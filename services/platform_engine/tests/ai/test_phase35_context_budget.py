from __future__ import annotations

from backend.ai.llm.llama_server import LlamaServerConfig, LlamaServerLLMProvider


def _context() -> dict:
    return {
        "vehicle": {"make": "Mercedes-Benz", "model": "W211", "year": 2006, "engine": "M272 3.5"},
        "dtcs": [{"code": f"P{i:04d}"} for i in range(30)],
        "symptoms": [f"symptom-{i}" for i in range(20)],
        "evidence": [{"fact": "x" * 800, "status": "MEASURED"} for _ in range(60)],
        "hypotheses": [{"name": f"hypothesis-{i}"} for i in range(20)],
        "telemetry_summary": {"stats": [{"pid": "rpm", "mean": 1650, "max": 2200}]},
        "recent_live_signals": [{"pid": "rpm", "values": list(range(200))}, {"pid": "map", "values": list(range(200))}],
        "safety_instruction": "Do not confirm unsupported component failures.",
    }


def test_phase35_context_budget_reads_server_context(monkeypatch):
    provider = LlamaServerLLMProvider(LlamaServerConfig(configured_context=2048, max_tokens=700))
    monkeypatch.setattr(provider, "_server_context_size", lambda: 2048)
    text = provider._safe_context_text(_context())
    # 2048-context server: leave room for output/system framing.
    assert len(text) <= 5760


def test_phase35_payload_caps_output_on_small_context(monkeypatch):
    provider = LlamaServerLLMProvider(LlamaServerConfig(configured_context=2048, max_tokens=700))
    monkeypatch.setattr(provider, "_server_context_size", lambda: 2048)
    monkeypatch.setattr(provider, "_resolve_model_id", lambda: "demo")
    payload = provider._build_payload("Analyze the live vehicle.", _context())
    assert payload["max_tokens"] <= 682
    content = payload["messages"][1]["content"]
    assert len(content) <= 6000


def test_phase35_config_default_context_is_8192(monkeypatch):
    monkeypatch.delenv("LOCAL_LLM_SERVER_CONTEXT", raising=False)
    cfg = LlamaServerConfig.from_env()
    assert cfg.configured_context == 8192
