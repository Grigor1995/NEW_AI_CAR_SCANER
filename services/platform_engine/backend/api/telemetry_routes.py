from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from api.state import sessions
from telemetry.evidence import events_to_evidence
from telemetry.models import TelemetrySample, TelemetrySummary
from telemetry.service import TelemetryService
from ai.live_analysis import analyze_live_session

router = APIRouter(prefix="/api/v1/telemetry", tags=["vehicle-telemetry"])
service = TelemetryService()


class TelemetryBatch(BaseModel):
    samples: list[TelemetrySample] = Field(default_factory=list, max_length=5000)


@router.post("/sessions/{session_id}/samples")
def append_samples(session_id: str, batch: TelemetryBatch):
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    sid = sessions[session_id].session_id
    normalized = [sample.model_copy(update={"session_id": sid}) for sample in batch.samples]
    count = service.append(normalized)
    sessions[session_id].audit_log.append({"event": "LIVE_DATA_SAMPLES_RECEIVED", "sample_count": count})
    return {"accepted": count}


@router.get("/sessions/{session_id}/summary", response_model=TelemetrySummary)
def telemetry_summary(session_id: str):
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    return service.summarize(sessions[session_id].session_id)


@router.post("/sessions/{session_id}/analyze", response_model=TelemetrySummary)
def analyze_telemetry(session_id: str):
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    session = sessions[session_id]
    summary = service.summarize(session.session_id)
    new_evidence = events_to_evidence(summary)
    existing = {e.source_ref for e in session.evidence if e.source_ref}
    added = 0
    for item in new_evidence:
        if item.source_ref not in existing:
            session.evidence.append(item)
            existing.add(item.source_ref)
            added += 1
    summary.evidence_added = added
    session.audit_log.append({"event": "TELEMETRY_ANALYSIS_COMPLETED", "sample_count": summary.sample_count, "event_count": len(summary.events), "evidence_added": added})
    return summary


@router.post("/sessions/{session_id}/ai-analyze-live")
async def ai_analyze_live(session_id: str, language: str = "en"):
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    session = sessions[session_id]
    summary = service.summarize(session.session_id)
    samples = service.samples(session.session_id)
    result = await analyze_live_session(session, summary, samples, language=language)
    from diagnostic.decision import DiagnosticDecisionEngine
    from diagnostic.localization import localize_decision_plan
    result["decision"] = localize_decision_plan(DiagnosticDecisionEngine().build_plan(session), language).model_dump(mode="json")
    session.audit_log.append({
        "event": "LIVE_DATA_AI_ANALYSIS_COMPLETED",
        "sample_count": summary.sample_count,
        "signal_count": summary.signal_count,
        "event_count": len(summary.events),
        "evidence_added": result["evidence_added"],
        "ai_available": result["ai"]["available"],
        "provider": result["ai"]["provider"],
    })
    return result
