from __future__ import annotations

from pathlib import Path

from backend.ai.llm.llama_cpp import LlamaCppConfig, LlamaCppLLMProvider


def test_legacy_llama_cpp_provider_alias_points_to_phase31_server():
    cfg = LlamaCppConfig(base_url="http://127.0.0.1:8081", model="test-model")
    provider = LlamaCppLLMProvider(cfg)
    assert provider.config.base_url == "http://127.0.0.1:8081"
    assert provider.__class__.__name__ == "LlamaServerLLMProvider"


def test_phase31_server_config_can_be_constructed():
    assert Path("models/qwen3-8b-q4_k_m.gguf").name == "qwen3-8b-q4_k_m.gguf"
