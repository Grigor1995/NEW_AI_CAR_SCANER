from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from diagnostic.models import DiagnosticSession
from telemetry.models import SignalEvent, SignalEventType, SignalStats, TelemetrySample, TelemetrySummary
from telemetry.service import TelemetryService
from api import telemetry_routes as routes


def _summary(sid):
    stat = SignalStats(
        session_id=sid, pid="RPM", count=2, start_ms=100, end_ms=200,
        min_value=700, max_value=900, mean=800, event_count=1,
    )
    event = SignalEvent(
        session_id=sid, pid="RPM", event_type=SignalEventType.STEP_CHANGE,
        start_ms=100, end_ms=200, severity="HIGH",
        message="RPM changed rapidly", evidence_fact="RPM step change",
    )
    return TelemetrySummary(
        session_id=sid, sample_count=2, signal_count=1,
        start_ms=100, end_ms=200, stats=[stat], events=[event],
    )


def _setup(monkeypatch):
    session = DiagnosticSession()
    service = TelemetryService()
    monkeypatch.setattr(routes, "sessions", {"s1": session})
    monkeypatch.setattr(routes, "service", service)
    return session, service


def test_append_samples_normalizes_session_id_and_logs_count(monkeypatch):
    session, service = _setup(monkeypatch)
    supplied_sid = uuid4()
    sample = TelemetrySample(
        session_id=supplied_sid, timestamp_ms=100, pid="RPM", value=750, unit="rpm", sequence=1,
    )
    with pytest.raises(HTTPException) as exc:
        routes.append_samples("missing", routes.TelemetryBatch(samples=[sample]))
    assert exc.value.status_code == 404

    response = routes.append_samples("s1", routes.TelemetryBatch(samples=[sample]))
    assert response == {"accepted": 1}
    stored = service.samples(session.session_id)
    assert len(stored) == 1
    assert stored[0].session_id == session.session_id
    assert session.audit_log[-1] == {"event": "LIVE_DATA_SAMPLES_RECEIVED", "sample_count": 1}


def test_summary_analysis_adds_measured_evidence_once(monkeypatch):
    session, service = _setup(monkeypatch)
    sid = session.session_id
    summary = _summary(sid)
    monkeypatch.setattr(service, "summarize", lambda _sid: summary)

    with pytest.raises(HTTPException) as exc:
        routes.telemetry_summary("missing")
    assert exc.value.status_code == 404
    assert routes.telemetry_summary("s1") is summary

    with pytest.raises(HTTPException) as exc:
        routes.analyze_telemetry("missing")
    assert exc.value.status_code == 404

    response = routes.analyze_telemetry("s1")
    assert response.evidence_added == 1
    assert session.evidence[0].fact == "RPM step change"
    second = routes.analyze_telemetry("s1")
    assert second.evidence_added == 0
    assert len(session.evidence) == 1
    assert session.audit_log[-1]["event"] == "TELEMETRY_ANALYSIS_COMPLETED"


@pytest.mark.asyncio
async def test_ai_live_analysis_logs_provider_outcome_and_checks_session(monkeypatch):
    session, service = _setup(monkeypatch)
    summary = _summary(session.session_id)
    monkeypatch.setattr(service, "summarize", lambda _sid: summary)
    monkeypatch.setattr(service, "samples", lambda _sid: [])
    fake_result = {
        "evidence_added": 2,
        "ai": {"available": False, "provider": "FallbackProvider"},
        "live_context": {},
    }
    analyze = AsyncMock(return_value=fake_result)
    monkeypatch.setattr(routes, "analyze_live_session", analyze)

    with pytest.raises(HTTPException) as exc:
        await routes.ai_analyze_live("missing")
    assert exc.value.status_code == 404

    response = await routes.ai_analyze_live("s1")
    assert response == fake_result
    analyze.assert_awaited_once_with(session, summary, [], language="en")
    event = session.audit_log[-1]
    assert event["event"] == "LIVE_DATA_AI_ANALYSIS_COMPLETED"
    assert event["ai_available"] is False
    assert event["provider"] == "FallbackProvider"
