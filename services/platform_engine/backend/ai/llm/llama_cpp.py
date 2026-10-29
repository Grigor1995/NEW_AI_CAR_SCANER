"""Legacy in-process llama.cpp provider retained for migration/testing.

Phase 31 does not select this provider by default because the Windows native
binding can crash the host process on some CPU/build combinations. Use
LlamaServerLLMProvider instead.
"""
from __future__ import annotations

from ai.llm.llama_server import LlamaServerLLMProvider as LlamaCppLLMProvider
from ai.llm.llama_server import LlamaServerConfig as LlamaCppConfig

__all__ = ["LlamaCppConfig", "LlamaCppLLMProvider"]
