from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import Any

from ai.interfaces import LLMProvider, LLMResponse


@dataclass(frozen=True)
class LlamaServerConfig:
    base_url: str = "http://127.0.0.1:8000"
    model: str = "Qwen3-8B-Q4_K_M.gguf"
    timeout_s: float = 300.0
    temperature: float = 0.1
    max_tokens: int = 700
    api_key: str | None = None
    configured_context: int = 8192
    context_safety_margin: int = 128

    @classmethod
    def from_env(cls) -> "LlamaServerConfig":
        return cls(
            base_url=os.getenv(
                "LOCAL_LLM_SERVER_URL",
                os.getenv("LLM_BASE_URL", "http://127.0.0.1:8000"),
            ).rstrip("/").removesuffix("/v1"),
            model=os.getenv(
                "LOCAL_LLM_SERVER_MODEL",
                os.getenv("LLM_MODEL", "Qwen3-8B-Q4_K_M.gguf"),
            ),
            timeout_s=max(10.0, float(os.getenv("LOCAL_LLM_SERVER_TIMEOUT_S", "300"))),
            temperature=max(
                0.0,
                min(2.0, float(os.getenv("LOCAL_LLM_TEMPERATURE", "0.1"))),
            ),
            max_tokens=max(64, int(os.getenv("LOCAL_LLM_MAX_TOKENS", "700"))),
            api_key=os.getenv("LOCAL_LLM_SERVER_API_KEY") or os.getenv("LLM_API_KEY"),
            configured_context=max(1024, int(os.getenv("LOCAL_LLM_SERVER_CONTEXT", "8192"))),
            context_safety_margin=max(64, int(os.getenv("LOCAL_LLM_CONTEXT_SAFETY_MARGIN", "128"))),
        )


class LlamaServerLLMProvider(LLMProvider):
    """OpenAI-compatible adapter for a standalone llama-server.exe process."""

    def __init__(self, config: LlamaServerConfig | None = None) -> None:
        self.config = config or LlamaServerConfig.from_env()

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def _get_json(self, path: str, timeout_s: float = 5.0) -> dict[str, Any]:
        req = Request(
            f"{self.config.base_url}{path}",
            headers=self._headers(),
            method="GET",
        )
        try:
            with urlopen(req, timeout=timeout_s) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"llama-server {path} HTTP {exc.code}: {detail}"
            ) from exc
        except (URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            raise RuntimeError(
                f"llama-server unavailable at {self.config.base_url}: {exc}"
            ) from exc

        if isinstance(payload, dict):
            return payload
        return {"data": payload}

    def _server_models(self) -> list[str]:
        payload = self._get_json("/v1/models")
        data = payload.get("data") if isinstance(payload, dict) else None
        return [
            str(item["id"])
            for item in data or []
            if isinstance(item, dict) and item.get("id")
        ]

    def _resolve_model_id(self) -> str:
        try:
            models = self._server_models()
        except Exception:
            return self.config.model
        if self.config.model in models:
            return self.config.model
        if len(models) == 1:
            return models[0]
        return self.config.model

    def _server_context_size(self) -> int:
        """Return the actual context size reported by llama-server, with a configured fallback."""
        try:
            props = self._get_json("/props", timeout_s=3.0)
            n_ctx = (
                props.get("default_generation_settings", {})
                .get("n_ctx")
            )
            if n_ctx is None:
                n_ctx = props.get("n_ctx")
            if n_ctx is not None:
                return max(1024, int(n_ctx))
        except Exception:
            pass
        return self.config.configured_context

    def availability(self) -> dict[str, Any]:
        base = {
            "provider": self.__class__.__name__,
            "model": self.config.model,
            "base_url": self.config.base_url,
            "runtime": "llama.cpp server",
        }
        try:
            health = self._get_json("/health", timeout_s=3.0)
            models = self._server_models()
            context_size = self._server_context_size()
            status = str(health.get("status", "")).lower()
            ready = status in {"ok", "no slot available"}
            return {
                **base,
                "available": ready and bool(models),
                "healthy": ready,
                "health_status": health.get("status"),
                "server_models": models,
                "resolved_model": self._resolve_model_id(),
                "server_context": context_size,
            }
        except Exception as exc:
            return {
                **base,
                "available": False,
                "healthy": False,
                "reason": str(exc),
            }

    @staticmethod
    def _json_compact(value: Any) -> str:
        return json.dumps(
            value,
            ensure_ascii=False,
            default=str,
            separators=(",", ":"),
        )

    def _safe_context_text(self, context: dict[str, Any]) -> str:
        """Serialize only the highest-value context within a token-aware character budget.

        llama-server rejects a request when prompt tokens + output tokens exceed its configured
        context. We therefore derive the input budget from the server's actual /props value.
        Four characters per token is only an approximation, so a safety margin is reserved.
        """
        server_ctx = self._server_context_size()
        reserved_output = min(self.config.max_tokens, max(64, server_ctx // 3))
        input_token_budget = max(
            512,
            server_ctx - reserved_output - self.config.context_safety_margin,
        )
        max_chars = max(1600, input_token_budget * 3)

        compact = {
            "vehicle": context.get("vehicle"),
            "dtcs": context.get("dtcs", [])[-8:],
            "symptoms": context.get("symptoms", [])[-6:],
            "evidence": context.get("evidence", [])[-10:],
            "hypotheses": context.get("hypotheses", [])[-6:],
            "telemetry_summary": context.get("telemetry_summary"),
            "recent_live_signals": context.get("recent_live_signals", [])[-16:],
            "safety_instruction": context.get("safety_instruction"),
        }
        text = self._json_compact(compact)
        if len(text) <= max_chars:
            return text

        # Second pass: retain only the most diagnostic fields.
        minimal = {
            "vehicle": context.get("vehicle"),
            "dtcs": context.get("dtcs", [])[-4:],
            "symptoms": context.get("symptoms", [])[-4:],
            "evidence": context.get("evidence", [])[-6:],
            "hypotheses": context.get("hypotheses", [])[-4:],
            "telemetry_summary": context.get("telemetry_summary"),
            "recent_live_signals": context.get("recent_live_signals", [])[-8:],
            "safety_instruction": context.get("safety_instruction"),
        }
        text = self._json_compact(minimal)
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n[CONTEXT_COMPACTED]"

    def _build_payload(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        system = (
            "You are an evidence-driven automotive diagnostic assistant. "
            "Use only the supplied diagnostic evidence and retrieved knowledge. "
            "Never invent measurements. Never claim a component failure is confirmed "
            "unless the evidence explicitly has status CONFIRMED. Distinguish "
            "REPORTED, MEASURED, CALCULATED, INFERRED, CONFIRMED and REJECTED. "
            "Treat live telemetry as measured data. Explain relationships and uncertainty. "
            "Prefer the safest high-information next diagnostic test."
        )
        response_language = {"en": "English", "ru": "Russian", "hy": "Armenian"}.get(context.get("response_language"), "English")
        system += f" Write every explanatory sentence in {response_language}; preserve diagnostic codes, units and identifiers."
        server_ctx = self._server_context_size()
        # Keep enough room for the response and system/task framing. The context text is already
        # bounded, but this also prevents an oversized max_tokens on small external servers.
        max_output = min(
            self.config.max_tokens,
            max(64, server_ctx // 3),
        )
        return {
            "model": self._resolve_model_id(),
            "messages": [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": (
                        f"TASK:\n{prompt}\n\n"
                        f"DIAGNOSTIC CONTEXT:\n{self._safe_context_text(context)}"
                    ),
                },
            ],
            "temperature": self.config.temperature,
            "max_tokens": max_output,
            "stream": False,
        }

    def _generate_sync(self, prompt: str, context: dict[str, Any]) -> LLMResponse:
        body = self._build_payload(prompt, context)
        req = Request(
            f"{self.config.base_url}/v1/chat/completions",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        try:
            with urlopen(req, timeout=self.config.timeout_s) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            # llama-server reports context overflow as HTTP 400. Surface the measured server
            # limit and ask the UI layer to refresh/restart with a larger context if needed.
            if exc.code == 400 and "exceeds the available context size" in detail:
                raise RuntimeError(
                    "llama-server context overflow: "
                    f"{detail}. The client now compacts live diagnostic context automatically. "
                    "If this persists, restart llama-server with a larger --ctx-size (for example 8192)."
                ) from exc
            raise RuntimeError(
                f"llama-server inference HTTP {exc.code}: {detail}"
            ) from exc
        except (URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            raise RuntimeError(
                f"llama-server inference failed: {exc}"
            ) from exc

        choices = result.get("choices") or []
        if not choices:
            raise RuntimeError("llama-server returned no choices")
        message = choices[0].get("message") or {}
        text = str(message.get("content") or "").strip()
        if not text:
            raise RuntimeError("llama-server returned an empty response")

        return LLMResponse(
            text=text,
            model=str(body["model"]),
            provider="llama-server",
            raw=result,
        )

    async def generate(self, prompt: str, context: dict[str, Any]) -> LLMResponse:
        return await asyncio.wait_for(
            asyncio.to_thread(self._generate_sync, prompt, context),
            timeout=self.config.timeout_s + 10.0,
        )
