from __future__ import annotations

from backend.ai.llm.llama_server import LlamaServerConfig


def test_phase32_ports_are_split(monkeypatch):
    monkeypatch.delenv("AI_CAR_BACKEND_PORT", raising=False)
    monkeypatch.delenv("LOCAL_LLM_SERVER_URL", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    cfg = LlamaServerConfig.from_env()
    assert cfg.base_url == "http://127.0.0.1:8000"


def test_phase32_inference_timeout_is_long_enough(monkeypatch):
    monkeypatch.delenv("LOCAL_LLM_SERVER_TIMEOUT_S", raising=False)
    cfg = LlamaServerConfig.from_env()
    assert cfg.timeout_s >= 180.0
