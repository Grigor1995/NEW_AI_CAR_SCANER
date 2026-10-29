from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from ai.interfaces import LLMProvider, LLMResponse


@dataclass(frozen=True)
class OpenAICompatibleConfig:
    base_url: str
    model: str
    api_key: str | None = None
    timeout_s: float = 60.0
    temperature: float = 0.1


class HttpOpenAICompatibleProvider(LLMProvider):
    """Serve LM Studio, Jan, local GGUF, or compatible hosted APIs.

    These runtimes use GET /v1/models rather than the llama.cpp-only /health.
    """
    def __init__(self, config: OpenAICompatibleConfig):
        self.config = config

    @property
    def _root(self) -> str:
        value = self.config.base_url.rstrip("/")
        return value[:-3] if value.endswith("/v1") else value

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def availability(self) -> dict:
        """Model availability is independent of the FastAPI /health endpoint."""
        result = {
            "provider": self.__class__.__name__,
            "model": self.config.model,
            "base_url": self._root,
            "available": False,
            "healthy": False,
        }
        req = Request(self._root + "/v1/models", headers=self._headers(), method="GET")
        try:
            with urlopen(req, timeout=4.0) as response:
                payload = json.loads(response.read().decode("utf-8"))
            entries = payload.get("data", []) if isinstance(payload, dict) else []
            models = [
                str(row["id"]) for row in entries
                if isinstance(row, dict) and row.get("id")
            ]
            result["healthy"] = True
            result["server_models"] = models
            result["available"] = self.config.model in models
            if not models:
                result["reason"] = "No models are available. Load a model in the local AI server."
            elif not result["available"]:
                result["reason"] = (
                    f"Model '{self.config.model}' not found. "
                    "Set LLM_MODEL to one of the server_models."
                )
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            result["reason"] = f"AI runtime unavailable: {exc}"
        return result

    def _generate_sync(self, prompt: str, context: dict) -> LLMResponse:
        language = {"en": "English", "ru": "Russian", "hy": "Armenian"}.get(
            context.get("response_language"), "English"
        )
        messages = [
            {"role": "system", "content": (
                "You are an evidence-driven automotive diagnostic assistant. "
                "Use only supplied diagnostic evidence and retrieved sources. "
                "Never invent measurements or claim confirmed faults without evidence. "
                f"Explain uncertainty, and write in {language}."
            )},
            {"role": "user", "content": json.dumps(
                {"task": prompt, "context": context}, ensure_ascii=False
            )},
        ]
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
        }
        req = Request(
            self._root + "/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        try:
            with urlopen(req, timeout=self.config.timeout_s) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            raise RuntimeError(f"OpenAI-compatible inference failed: {exc}") from exc
        choices = body.get("choices") or []
        response_text = str((choices[0].get("message") or {}).get("content", "")) if choices else ""
        return LLMResponse(response_text, self.config.model, "openai-compatible", raw=body)

    async def generate(self, prompt: str, context: dict) -> LLMResponse:
        # urllib is synchronous; do not block FastAPI's event loop during inference.
        return await asyncio.to_thread(self._generate_sync, prompt, context)
