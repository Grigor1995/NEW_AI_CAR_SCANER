import io
import json
from urllib.error import HTTPError, URLError

import pytest

import ai.llm.openai_compatible as openai_compatible


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
    def __enter__(self):
        return self
    def __exit__(self, *_args):
        return False
    def read(self):
        return self.payload


def success_body(text="Diagnostic explanation"):
    return json.dumps({
        "choices": [{"message": {"content": text}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 3},
    }).encode("utf-8")


@pytest.mark.asyncio
async def test_openai_compatible_generate_builds_request_and_parses_response(monkeypatch):
    seen = {}
    def fake_urlopen(request, timeout):
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        seen["headers"] = {key.lower(): value for key, value in request.header_items()}
        seen["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse(success_body("Only evidence-backed conclusions."))

    monkeypatch.setattr(openai_compatible, "urlopen", fake_urlopen)
    provider = openai_compatible.HttpOpenAICompatibleProvider(
        openai_compatible.OpenAICompatibleConfig(
            base_url="http://localhost:9000/",
            model="test-model",
            api_key="secret",
            timeout_s=12,
            temperature=0.25,
        )
    )

    result = await provider.generate("Explain P0302", {"dtcs": ["P0302"], "note": "Գազ"})

    assert result.text == "Only evidence-backed conclusions."
    assert result.model == "test-model"
    assert result.provider == "openai-compatible"
    assert result.raw["usage"]["prompt_tokens"] == 5
    assert seen["url"] == "http://localhost:9000/v1/chat/completions"
    assert seen["timeout"] == 12
    assert seen["headers"]["authorization"] == "Bearer secret"
    assert seen["body"]["model"] == "test-model"
    assert seen["body"]["temperature"] == 0.25
    user_payload = json.loads(seen["body"]["messages"][1]["content"])
    assert user_payload == {"task": "Explain P0302", "context": {"dtcs": ["P0302"], "note": "Գազ"}}


@pytest.mark.asyncio
async def test_openai_compatible_generate_omits_authorization_without_key(monkeypatch):
    def fake_urlopen(request, timeout):
        assert request.full_url == "http://localhost:9000/v1/chat/completions"
        assert not any(key.lower() == "authorization" for key, _ in request.header_items())
        return FakeResponse(success_body())

    monkeypatch.setattr(openai_compatible, "urlopen", fake_urlopen)
    provider = openai_compatible.HttpOpenAICompatibleProvider(
        openai_compatible.OpenAICompatibleConfig("http://localhost:9000", "offline-model")
    )

    result = await provider.generate("Test", {})
    assert result.text == "Diagnostic explanation"


@pytest.mark.parametrize(
    "error",
    [
        HTTPError("http://localhost", 503, "unavailable", {}, io.BytesIO(b"down")),
        URLError("connection refused"),
        TimeoutError("request timeout"),
    ],
)
@pytest.mark.asyncio
async def test_openai_compatible_wraps_transport_failures(monkeypatch, error):
    def fail(*_args, **_kwargs):
        raise error
    monkeypatch.setattr(openai_compatible, "urlopen", fail)
    provider = openai_compatible.HttpOpenAICompatibleProvider(
        openai_compatible.OpenAICompatibleConfig("http://localhost", "offline-model")
    )

    with pytest.raises(RuntimeError, match="OpenAI-compatible inference failed"):
        await provider.generate("Test", {})


@pytest.mark.asyncio
async def test_openai_compatible_wraps_invalid_json_response(monkeypatch):
    monkeypatch.setattr(openai_compatible, "urlopen", lambda *_args, **_kwargs: FakeResponse(b"not-json"))
    provider = openai_compatible.HttpOpenAICompatibleProvider(
        openai_compatible.OpenAICompatibleConfig("http://localhost", "offline-model")
    )
    with pytest.raises(RuntimeError, match="OpenAI-compatible inference failed"):
        await provider.generate("Test", {})


@pytest.mark.asyncio
async def test_openai_compatible_preserves_empty_choice_content_contract(monkeypatch):
    monkeypatch.setattr(
        openai_compatible,
        "urlopen",
        lambda *_args, **_kwargs: FakeResponse(json.dumps({"choices": [{"message": {"content": ""}}]}).encode()),
    )
    provider = openai_compatible.HttpOpenAICompatibleProvider(
        openai_compatible.OpenAICompatibleConfig("http://localhost", "offline-model")
    )

    result = await provider.generate("Test", {})
    assert result.text == ""
