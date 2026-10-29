from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Any

from ai.llm.factory import build_llm_provider
from ai.reasoning.engine import DiagnosticIntelligenceEngine
from diagnostic.models import DiagnosticSession, Evidence, EvidenceSource, EvidenceStatus
from telemetry.models import TelemetrySample, TelemetrySummary
from telemetry.evidence import events_to_evidence
from diagnostic.localization import normalize_language, localize_session_analysis


def _recent_signal_context(samples: list[TelemetrySample], max_per_signal: int = 8) -> list[dict[str, Any]]:
    grouped: dict[str, list[TelemetrySample]] = defaultdict(list)
    for sample in sorted(samples, key=lambda x: (x.timestamp_ms, x.sequence or -1)):
        grouped[sample.pid].append(sample)
    payload: list[dict[str, Any]] = []
    for pid, items in sorted(grouped.items()):
        recent = items[-max_per_signal:]
        payload.append({
            "pid": pid,
            "unit": recent[-1].unit if recent else None,
            "count": len(recent),
            "values": [round(float(x.value), 4) for x in recent],
            "latest": round(float(recent[-1].value), 4) if recent else None,
            "mean": round(mean(float(x.value) for x in recent), 4) if recent else None,
        })
    return payload


def build_live_context(session: DiagnosticSession, summary: TelemetrySummary, samples: list[TelemetrySample]) -> dict[str, Any]:
    # Live-data analysis must stay bounded. Keep the newest/high-value evidence rather than
    # serializing the entire session history into every inference request.
    evidence = [x.model_dump(mode="json") for x in session.evidence[-30:]]
    hypotheses = [x.model_dump(mode="json") for x in session.hypotheses[-12:]]
    symptoms = [x.raw_text for x in session.symptoms[-12:]]
    return {
        "vehicle": session.vehicle.model_dump(mode="json") if session.vehicle else None,
        "dtcs": [x.model_dump(mode="json") for x in session.dtcs[-30:]],
        "symptoms": symptoms,
        "evidence": evidence,
        "hypotheses": hypotheses,
        "telemetry_summary": summary.model_dump(mode="json"),
        "recent_live_signals": _recent_signal_context(samples),
        "safety_instruction": (
            "Treat telemetry as measured evidence. Do not invent values. Do not claim a component failure is confirmed "
            "unless the session contains CONFIRMED evidence. Explain anomalies, correlations and useful next tests."
        ),
    }


def add_live_evidence(session: DiagnosticSession, summary: TelemetrySummary) -> int:
    added = 0
    existing_refs = {x.source_ref for x in session.evidence if x.source_ref}
    for item in events_to_evidence(summary):
        if item.source_ref not in existing_refs:
            session.evidence.append(item)
            existing_refs.add(item.source_ref)
            added += 1
    # A compact measured snapshot is useful even when there are no threshold events.
    for stat in summary.stats:
        if stat.count <= 0:
            continue
        source_ref = f"telemetry-summary:{summary.session_id}:{stat.pid}:{summary.end_ms}"
        if source_ref in existing_refs:
            continue
        fact = (
            f"Live {stat.pid}: n={stat.count}, mean={stat.mean}, min={stat.min_value}, max={stat.max_value}, "
            f"sample_rate_hz={stat.sample_rate_hz}, anomalies={stat.anomaly_count}, events={stat.event_count}."
        )
        session.evidence.append(Evidence(
            fact=fact,
            source=EvidenceSource.VEHICLE_MEASURED,
            status=EvidenceStatus.MEASURED,
            confidence=0.96,
            source_ref=source_ref,
            metadata={"pid": stat.pid, "window_end_ms": summary.end_ms},
        ))
        existing_refs.add(source_ref)
        added += 1
    return added


async def analyze_live_session(
    session: DiagnosticSession,
    summary: TelemetrySummary,
    samples: list[TelemetrySample],
    language: str = "en",
) -> dict[str, Any]:
    language = normalize_language(language)
    added = add_live_evidence(session, summary)
    deterministic = DiagnosticIntelligenceEngine().analyze(session)
    provider = build_llm_provider()
    context = build_live_context(deterministic, summary, samples)
    context["response_language"] = language
    response_language = {"en": "English", "ru": "Russian", "hy": "Armenian"}[language]
    prompt = (
        "Analyze the current live vehicle telemetry together with the diagnostic evidence. "
        "Identify meaningful signal relationships or anomalies, state what is measured versus inferred, "
        "and recommend the next diagnostic test. Never invent values or confirm a component failure without CONFIRMED evidence. "
        f"Write the entire explanation in {response_language} (language code {language}). Preserve DTC codes and units."
    )

    ai_payload: dict[str, Any]
    try:
        response = await provider.generate(prompt, context)
        ai_payload = {
            "available": True,
            "provider": response.provider,
            "model": response.model,
            "text": response.text,
        }
    except Exception as exc:
        ai_payload = {
            "available": False,
            "provider": provider.__class__.__name__,
            "model": getattr(getattr(provider, "config", None), "model", "unknown"),
            "text": {
                "en": "Live-data AI inference is unavailable. Deterministic telemetry analysis remains active.",
                "ru": "ИИ-анализ текущих данных недоступен. Детерминированный анализ телеметрии продолжает работать.",
                "hy": "Ընթացիկ տվյալների AI վերլուծությունն անհասանելի է։ Հեռաչափության կանոնային վերլուծությունը շարունակում է աշխատել։",
            }[language],
            "error": str(exc),
        }

    return {
        "session": localize_session_analysis(deterministic, language).model_dump(mode="json"),
        "telemetry": summary.model_dump(mode="json"),
        "live_context": context,
        "evidence_added": added,
        "ai": ai_payload,
    }
