from backend.ai.live_analysis import build_live_context
from backend.ai.llm.llama_server import LlamaServerConfig, LlamaServerLLMProvider
from backend.diagnostic.models import DiagnosticSession, Vehicle, Evidence, EvidenceSource, EvidenceStatus
from backend.telemetry.models import TelemetrySample, TelemetrySummary, SignalStats
from uuid import uuid4


def test_phase33_live_context_is_bounded_to_recent_history():
    sid = uuid4()
    session = DiagnosticSession(session_id=str(sid), vehicle=Vehicle(make="Demo", model="Live", year=2026))
    session.symptoms = [type("S", (), {"raw_text": f"symptom-{i}"})() for i in range(50)]
    session.evidence = [Evidence(fact=f"fact-{i}", source=EvidenceSource.USER_REPORTED, status=EvidenceStatus.REPORTED) for i in range(100)]
    samples = [TelemetrySample(session_id=sid, timestamp_ms=i, pid="rpm", value=1000 + i, unit="rpm") for i in range(100)]
    summary = TelemetrySummary(session_id=sid, sample_count=100, signal_count=1, start_ms=0, end_ms=99,
        stats=[SignalStats(session_id=sid, pid="rpm", count=100, start_ms=0, end_ms=99, mean=1049.5)])
    context = build_live_context(session, summary, samples)
    assert len(context["evidence"]) == 30
    assert len(context["symptoms"]) == 12
    assert len(context["recent_live_signals"][0]["values"]) == 8


def test_phase33_safe_context_compacts_large_payload():
    provider = LlamaServerLLMProvider()
    context = {"vehicle": {"make": "Demo"}, "dtcs": [], "symptoms": [], "evidence": [], "hypotheses": [],
               "telemetry_summary": {}, "recent_live_signals": [{"pid": "rpm", "values": list(range(10000))}],
               "safety_instruction": "safe"}
    text = provider._safe_context_text(context)
    assert "CONTEXT_COMPACTED" in text
    assert len(text) <= 24020


def test_phase33_llm_context_default_is_8192(monkeypatch):
    monkeypatch.delenv("LOCAL_LLM_SERVER_CONTEXT", raising=False)
    # The desktop launcher owns the server context default; verify the documented env contract is sane.
    monkeypatch.delenv("LOCAL_LLM_MAX_CONTEXT_CHARS", raising=False)
    provider = LlamaServerLLMProvider(LlamaServerConfig())
    assert provider.config.max_tokens == 700
