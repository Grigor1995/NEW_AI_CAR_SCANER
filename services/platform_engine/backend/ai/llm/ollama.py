from __future__ import annotations
import json
from dataclasses import dataclass
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from ai.interfaces import LLMProvider, LLMResponse

@dataclass(frozen=True)
class OllamaConfig:
    base_url: str = "http://localhost:11434"
    model: str = "qwen3:8b"
    timeout_s: float = 60.0
    temperature: float = 0.1

class OllamaLLMProvider(LLMProvider):
    """Local Ollama provider. No paid API is required."""
    def __init__(self, config: OllamaConfig | None = None):
        self.config = config or OllamaConfig()

    async def generate(self, prompt: str, context: dict) -> LLMResponse:
        payload = {
            "model": self.config.model,
            "stream": False,
            "options": {"temperature": self.config.temperature},
            "system": (
                "You are a diagnostic reasoning assistant. Use only supplied evidence and retrieved sources. "
                "Never claim a component is confirmed unless evidence status is CONFIRMED. "
                "Clearly distinguish reported, measured, calculated, inferred, confirmed, and rejected facts."
            ),
            "prompt": json.dumps({"task": prompt, "context": context}, ensure_ascii=False),
        }
        req = Request(
            f"{self.config.base_url.rstrip('/')}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(req, timeout=self.config.timeout_s) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Ollama inference failed: {exc}") from exc
        return LLMResponse(body.get("response", ""), self.config.model, "ollama", raw=body)
