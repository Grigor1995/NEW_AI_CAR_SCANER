from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from ai import live_analysis
from diagnostic.models import DiagnosticSession, Evidence, EvidenceSource, EvidenceStatus, Symptom, Hypothesis, Vehicle
from telemetry.models import SignalEvent, SignalEventType, SignalStats, TelemetrySample, TelemetrySummary


def _summary(sid):
    return TelemetrySummary(
        session_id=sid,
        sample_count=3,
        signal_count=1,
        start_ms=100,
        end_ms=300,
        stats=[SignalStats(
            session_id=sid, pid="RPM", count=3, start_ms=100, end_ms=300,
            min_value=700, max_value=1500, mean=1000, sample_rate_hz=10,
            anomaly_count=1, event_count=1,
        )],
        events=[SignalEvent(
            session_id=sid, pid="RPM", event_type=SignalEventType.STEP_CHANGE,
            start_ms=200, end_ms=300, severity="HIGH", message="step",
            evidence_fact="Measured RPM step", metrics={"delta": 800},
        )],
    )


def test_recent_signal_context_sorts_samples_groups_and_caps_history():
    sid = uuid4()
    samples = [
        TelemetrySample(session_id=sid, timestamp_ms=i, pid="RPM", value=i, unit="rpm", sequence=i)
        for i in range(10, 0, -1)
    ]
    samples += [
        TelemetrySample(session_id=sid, timestamp_ms=i, pid="MAP", value=i * 2, unit="kPa")
        for i in (1, 2)
    ]
    context = live_analysis._recent_signal_context(samples, max_per_signal=3)
    assert [x["pid"] for x in context] == ["MAP", "RPM"]
    rpm = context[1]
    assert rpm["count"] == 3
    assert rpm["values"] == [8.0, 9.0, 10.0]
    assert rpm["latest"] == 10.0
    assert rpm["mean"] == 9.0
    assert context[0]["unit"] == "kPa"


def test_build_live_context_bounds_session_lists_and_serializes_vehicle():
    sid = uuid4()
    session = DiagnosticSession(vehicle=Vehicle(make="Mercedes-Benz", model="W211"))
    session.evidence = [
        Evidence(fact=f"evidence-{i}", source=EvidenceSource.USER_REPORTED, status=EvidenceStatus.REPORTED)
        for i in range(35)
    ]
    session.hypotheses = [
        Hypothesis(category="ignition", statement=f"h-{i}") for i in range(14)
    ]
    session.symptoms = [Symptom(raw_text=f"symptom-{i}") for i in range(13)]
    summary = _summary(sid)
    sample = TelemetrySample(session_id=sid, timestamp_ms=100, pid="RPM", value=750, unit="rpm")

    context = live_analysis.build_live_context(session, summary, [sample])

    assert context["vehicle"]["make"] == "Mercedes-Benz"
    assert len(context["evidence"]) == 30 and context["evidence"][0]["fact"] == "evidence-5"
    assert len(context["hypotheses"]) == 12 and context["hypotheses"][0]["statement"] == "h-2"
    assert len(context["symptoms"]) == 12 and context["symptoms"][0] == "symptom-1"
    assert context["recent_live_signals"][0]["pid"] == "RPM"
    assert "Do not invent values" in context["safety_instruction"]


def test_add_live_evidence_deduplicates_events_and_adds_summary_snapshots():
    session = DiagnosticSession()
    summary = _summary(session.session_id)

    first = live_analysis.add_live_evidence(session, summary)
    assert first == 2  # one event plus one compact signal summary
    assert {item.source for item in session.evidence} == {EvidenceSource.VEHICLE_MEASURED}
    assert all(item.status is EvidenceStatus.MEASURED for item in session.evidence)
    second = live_analysis.add_live_evidence(session, summary)
    assert second == 0
    assert len(session.evidence) == 2


class FakeEngine:
    def analyze(self, session):
        session.audit_log.append({"event": "FAKE_ANALYZED"})
        return session


class FakeProvider:
    class Response:
        provider = "fake-provider"
        model = "fake-model"
        text = "Check pressure and compare fuel modes."
    async def generate(self, prompt, context):
        assert "telemetry" in prompt
        assert context["recent_live_signals"]
        return self.Response()


class BrokenProvider:
    config = SimpleNamespace(model="offline-model")
    async def generate(self, prompt, context):
        raise RuntimeError("LLM offline")


@pytest.mark.asyncio
async def test_analyze_live_session_returns_provider_result_and_deterministic_fallback(monkeypatch):
    session = DiagnosticSession()
    summary = _summary(session.session_id)
    sample = TelemetrySample(session_id=session.session_id, timestamp_ms=100, pid="RPM", value=750, unit="rpm")
    monkeypatch.setattr(live_analysis, "DiagnosticIntelligenceEngine", FakeEngine)
    monkeypatch.setattr(live_analysis, "build_llm_provider", lambda: FakeProvider())

    success = await live_analysis.analyze_live_session(session, summary, [sample])
    assert success["evidence_added"] == 2
    assert success["ai"] == {
        "available": True,
        "provider": "fake-provider",
        "model": "fake-model",
        "text": "Check pressure and compare fuel modes.",
    }
    assert success["session"]["audit_log"][-1]["event"] == "FAKE_ANALYZED"

    monkeypatch.setattr(live_analysis, "build_llm_provider", lambda: BrokenProvider())
    failure = await live_analysis.analyze_live_session(session, summary, [sample])
    assert failure["ai"]["available"] is False
    assert failure["ai"]["provider"] == "BrokenProvider"
    assert failure["ai"]["model"] == "offline-model"
    assert failure["ai"]["error"] == "LLM offline"
    assert failure["evidence_added"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("language,name", [("hy", "Armenian"), ("ru", "Russian"), ("en", "English")])
async def test_live_ai_receives_selected_response_language(monkeypatch, language, name):
    session = DiagnosticSession()
    summary = _summary(session.session_id)
    seen = {}
    class Provider:
        async def generate(self, prompt, context):
            seen.update(prompt=prompt, language=context["response_language"])
            return FakeProvider.Response()
    monkeypatch.setattr(live_analysis, "DiagnosticIntelligenceEngine", FakeEngine)
    monkeypatch.setattr(live_analysis, "build_llm_provider", lambda: Provider())
    result = await live_analysis.analyze_live_session(session, summary, [], language=language)
    assert seen["language"] == language
    assert name in seen["prompt"]
    assert result["ai"]["available"] is True
