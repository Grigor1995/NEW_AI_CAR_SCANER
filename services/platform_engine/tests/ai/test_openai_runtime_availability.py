"""OpenAI-compatible local runtimes (LM Studio/Jan) must report AI readiness."""
from __future__ import annotations

import json
from urllib.error import URLError

import pytest

from ai.llm.openai_compatible import OpenAICompatibleConfig, HttpOpenAICompatibleProvider
import ai.llm.openai_compatible as module


class Response:
    def __init__(self, content):
        self.content = json.dumps(content).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return self.content


def test_compatible_server_reports_ready_when_requested_model_is_loaded(monkeypatch):
    captured = []
    def api(request, timeout):
        captured.append((request.full_url, timeout))
        return Response({"data": [{"id": "my-model.gguf"}]})
    monkeypatch.setattr(module, "urlopen", api)
    provider = HttpOpenAICompatibleProvider(OpenAICompatibleConfig(
        base_url="http://127.0.0.1:1234/v1", model="my-model.gguf"
    ))
    result = provider.availability()
    assert result["available"] is True
    assert result["healthy"] is True
    assert result["server_models"] == ["my-model.gguf"]
    assert captured == [("http://127.0.0.1:1234/v1/models", 4.0)]


def test_healthy_server_with_wrong_model_does_not_claim_ai_ready(monkeypatch):
    monkeypatch.setattr(
        module, "urlopen",
        lambda *_a, **_k: Response({"data": [{"id": "loaded-model"}]})
    )
    provider = HttpOpenAICompatibleProvider(
        OpenAICompatibleConfig("http://127.0.0.1:1234", "not-loaded")
    )
    info = provider.availability()
    assert info["healthy"] is True
    assert info["available"] is False
    assert "Set LLM_MODEL" in info["reason"]


def test_unreachable_runtime_is_separate_from_fastapi_health(monkeypatch):
    def fail(*_a, **_k):
        raise URLError("connection refused")
    monkeypatch.setattr(module, "urlopen", fail)
    info = HttpOpenAICompatibleProvider(
        OpenAICompatibleConfig("http://127.0.0.1:1234", "model")
    ).availability()
    assert info["healthy"] is False
    assert info["available"] is False
    assert "unavailable" in info["reason"].lower()


@pytest.mark.asyncio
async def test_openai_compatible_generate_supports_v1_root_and_localization(monkeypatch):
    captured = []
    def api(request, timeout):
        captured.append((
            request.full_url,
            json.loads(request.data.decode("utf-8")),
        ))
        return Response({"choices": [{"message": {"content": "Հնարավոր է գազի խառնուրդի խնդիր"}}]})
    monkeypatch.setattr(module, "urlopen", api)
    provider = HttpOpenAICompatibleProvider(
        OpenAICompatibleConfig("http://127.0.0.1:1234/v1", "model")
    )
    answer = await provider.generate(
        "Interpret P0302",
        {"response_language": "hy", "dtcs": ["P0302"]},
    )
    assert "Հնարավոր" in answer.text
    assert captured[0][0] == "http://127.0.0.1:1234/v1/chat/completions"
    assert "Armenian" in captured[0][1]["messages"][0]["content"]
