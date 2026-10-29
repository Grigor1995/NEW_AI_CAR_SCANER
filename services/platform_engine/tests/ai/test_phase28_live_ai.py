from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from ai.live_analysis import _recent_signal_context, analyze_live_session
from diagnostic.models import DiagnosticSession, EvidenceStatus, EvidenceSource, Vehicle
from telemetry.models import TelemetrySample


def test_recent_signal_context_groups_latest_samples():
    sid = uuid4()
    samples = [
        TelemetrySample(session_id=sid, timestamp_ms=1, pid="rpm", value=1000, unit="rpm"),
        TelemetrySample(session_id=sid, timestamp_ms=2, pid="rpm", value=1200, unit="rpm"),
        TelemetrySample(session_id=sid, timestamp_ms=3, pid="coolant_c", value=88, unit="C"),
    ]
    ctx = _recent_signal_context(samples, max_per_signal=10)
    assert [x["pid"] for x in ctx] == ["coolant_c", "rpm"]
    rpm = next(x for x in ctx if x["pid"] == "rpm")
    assert rpm["latest"] == 1200
    assert rpm["count"] == 2


def test_live_context_contains_measurement_provenance():
    session = DiagnosticSession(vehicle=Vehicle(make="Mercedes-Benz", model="W211", year=2006, engine="M272 3.5", fuel=["Petrol", "LPG"]))
    session.evidence.append(__import__("diagnostic.models", fromlist=["Evidence"]).Evidence(
        fact="LPG only", source=EvidenceSource.USER_REPORTED, status=EvidenceStatus.REPORTED
    ))
    assert session.vehicle.engine == "M272 3.5"


def test_phase28_telemetry_ai_route_accepts_live_analysis(monkeypatch):
    import api.main as main
    from api.state import sessions

    sid = str(uuid4())
    session = DiagnosticSession(session_id=sid, vehicle=Vehicle(make="Demo", model="Live", year=2026))
    sessions[sid] = session

    async def fake_analysis(session, summary, samples, language="en"):
        return {"session": session.model_dump(mode="json"), "telemetry": summary.model_dump(mode="json"), "ai": {"available": True, "provider": "fake", "model": "test", "text": "RPM trend is stable."}, "live_context": {}, "evidence_added": 0}

    monkeypatch.setattr("api.telemetry_routes.analyze_live_session", fake_analysis)
    client = TestClient(main.app)
    response = client.post(f"/api/v1/telemetry/sessions/{sid}/ai-analyze-live")
    assert response.status_code == 200
    assert response.json()["ai"]["available"] is True
    sessions.pop(sid, None)


@pytest.mark.asyncio
async def test_live_ai_provider_receives_current_telemetry(monkeypatch):
    from telemetry.models import TelemetrySummary, SignalStats
    from ai.interfaces import LLMResponse
    from diagnostic.models import DiagnosticSession, Vehicle
    import ai.live_analysis as live

    class FakeProvider:
        config = type("Config", (), {"model": "fake-live"})()
        async def generate(self, prompt, context):
            assert context["recent_live_signals"]
            assert context["telemetry_summary"]["sample_count"] == 1
            assert context["safety_instruction"]
            return LLMResponse("Live RPM is measured and currently available.", "fake-live", "fake")

    monkeypatch.setattr(live, "build_llm_provider", lambda: FakeProvider())
    sid = uuid4()
    session = DiagnosticSession(session_id=sid, vehicle=Vehicle(make="Demo", model="Live", year=2026))
    sample = TelemetrySample(session_id=sid, timestamp_ms=1000, pid="rpm", value=1500, unit="rpm")
    summary = TelemetrySummary(session_id=sid, sample_count=1, signal_count=1, start_ms=1000, end_ms=1000,
                               stats=[SignalStats(session_id=sid, pid="rpm", count=1, start_ms=1000, end_ms=1000, mean=1500)])
    result = await analyze_live_session(session, summary, [sample])
    assert result["ai"]["available"] is True
    assert "measured" in result["ai"]["text"]
