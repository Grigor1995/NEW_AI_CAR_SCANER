from __future__ import annotations

import os

from ai.interfaces import LocalLLMProvider
from ai.llm.llama_server import LlamaServerConfig, LlamaServerLLMProvider
from ai.llm.openai_compatible import OpenAICompatibleConfig, HttpOpenAICompatibleProvider


def build_llm_provider():
    provider = os.getenv("DIAGNOSTIC_LLM_PROVIDER", "llama-server").lower()
    if provider in {"llama-server", "llama_server", "llamaserver", "local"}:
        return LlamaServerLLMProvider(LlamaServerConfig.from_env())
    if provider in {"openai-compatible", "openai_compatible"}:
        return HttpOpenAICompatibleProvider(OpenAICompatibleConfig(
            base_url=os.getenv("LLM_BASE_URL", "http://127.0.0.1:1234"),
            model=os.getenv("LLM_MODEL", "local-model"),
            api_key=os.getenv("LLM_API_KEY"),
        ))
    if provider == "placeholder":
        return LocalLLMProvider()
    raise ValueError(f"Unsupported LLM provider: {provider}")
