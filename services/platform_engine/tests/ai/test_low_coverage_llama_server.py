import io
import json
from urllib.error import HTTPError, URLError

import pytest

import ai.llm.llama_server as llama


class FakeResponse:
    def __init__(self, body):
        self.body = body
    def __enter__(self):
        return self
    def __exit__(self, *_args):
        return False
    def read(self):
        return self.body


def make_provider(**overrides):
    config = llama.LlamaServerConfig(**overrides)
    return llama.LlamaServerLLMProvider(config)


def test_config_from_env_applies_bounds_and_url_normalization(monkeypatch):
    monkeypatch.setenv("LOCAL_LLM_SERVER_URL", "http://127.0.0.1:9000///")
    monkeypatch.setenv("LOCAL_LLM_SERVER_TIMEOUT_S", "2")
    monkeypatch.setenv("LOCAL_LLM_TEMPERATURE", "3.5")
    monkeypatch.setenv("LOCAL_LLM_MAX_TOKENS", "8")
    monkeypatch.setenv("LOCAL_LLM_SERVER_CONTEXT", "512")
    monkeypatch.setenv("LOCAL_LLM_CONTEXT_SAFETY_MARGIN", "8")
    monkeypatch.setenv("LOCAL_LLM_SERVER_API_KEY", "local-secret")
    config = llama.LlamaServerConfig.from_env()
    assert config.base_url == "http://127.0.0.1:9000"
    assert config.timeout_s == 10.0
    assert config.temperature == 2.0
    assert config.max_tokens == 64
    assert config.configured_context == 1024
    assert config.context_safety_margin == 64
    assert config.api_key == "local-secret"


def test_headers_only_include_bearer_when_key_exists():
    assert make_provider(api_key="test-secret")._headers() == {
        "Content-Type": "application/json",
        "Authorization": "Bearer test-secret",
    }
    assert make_provider(api_key=None)._headers() == {"Content-Type": "application/json"}


def test_get_json_wraps_non_dict_json_payload(monkeypatch):
    monkeypatch.setattr(llama, "urlopen", lambda *_args, **_kwargs: FakeResponse(b'["a", "b"]'))
    assert make_provider()._get_json("/v1/models") == {"data": ["a", "b"]}


def test_get_json_wraps_http_and_network_errors(monkeypatch):
    provider = make_provider()
    def http_error(*_args, **_kwargs):
        raise HTTPError("http://localhost/health", 503, "not ready", {}, io.BytesIO(b"maintenance"))
    monkeypatch.setattr(llama, "urlopen", http_error)
    with pytest.raises(RuntimeError, match="llama-server /health HTTP 503: maintenance"):
        provider._get_json("/health")

    def network_error(*_args, **_kwargs):
        raise URLError("connection refused")
    monkeypatch.setattr(llama, "urlopen", network_error)
    with pytest.raises(RuntimeError, match="llama-server unavailable"):
        provider._get_json("/health")


def test_server_models_filters_malformed_items(monkeypatch):
    provider = make_provider()
    monkeypatch.setattr(
        provider, "_get_json",
        lambda path, timeout_s=5.0: {"data": [
            {"id": "model-a"}, {"id": 22}, {}, "invalid", {"id": ""}
        ]},
    )
    assert provider._server_models() == ["model-a", "22"]


@pytest.mark.parametrize(
    ("models", "expected"),
    [
        (["configured"], "configured"),
        (["only-model"], "only-model"),
        (["first", "second"], "configured"),
        ([], "configured"),
    ],
)
def test_resolve_model_id_uses_configured_or_unambiguous_server_model(monkeypatch, models, expected):
    provider = make_provider(model="configured")
    monkeypatch.setattr(provider, "_server_models", lambda: models)
    assert provider._resolve_model_id() == expected


def test_resolve_model_id_falls_back_when_model_endpoint_fails(monkeypatch):
    provider = make_provider(model="configured")
    def fail():
        raise RuntimeError("offline")
    monkeypatch.setattr(provider, "_server_models", fail)
    assert provider._resolve_model_id() == "configured"


@pytest.mark.parametrize(
    ("props", "expected"),
    [
        ({"default_generation_settings": {"n_ctx": 4096}}, 4096),
        ({"n_ctx": 2048}, 2048),
        ({"n_ctx": 12}, 1024),
        ({}, 8192),
    ],
)
def test_server_context_size_reads_props_or_uses_fallback(monkeypatch, props, expected):
    provider = make_provider(configured_context=8192)
    monkeypatch.setattr(provider, "_get_json", lambda *_args, **_kwargs: props)
    assert provider._server_context_size() == expected


def test_server_context_size_falls_back_on_error(monkeypatch):
    provider = make_provider(configured_context=4096)
    monkeypatch.setattr(provider, "_get_json", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("offline")))
    assert provider._server_context_size() == 4096


def test_availability_reports_healthy_server(monkeypatch):
    provider = make_provider(model="model-a")
    payloads = {
        "/health": {"status": "ok"},
        "/v1/models": {"data": [{"id": "model-a"}]},
        "/props": {"default_generation_settings": {"n_ctx": 4096}},
    }
    monkeypatch.setattr(provider, "_get_json", lambda path, timeout_s=5.0: payloads[path])
    result = provider.availability()
    assert result["available"] is True
    assert result["healthy"] is True
    assert result["resolved_model"] == "model-a"
    assert result["server_context"] == 4096


def test_availability_reports_not_ready_and_endpoint_failure(monkeypatch):
    provider = make_provider()
    monkeypatch.setattr(provider, "_get_json", lambda path, timeout_s=5.0: {"status": "loading"} if path == "/health" else {"data": []})
    result = provider.availability()
    assert result["available"] is False
    assert result["healthy"] is False

    monkeypatch.setattr(provider, "_get_json", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("offline")))
    failed = provider.availability()
    assert failed["available"] is False
    assert failed["healthy"] is False
    assert "offline" in failed["reason"]


def test_safe_context_text_keeps_recent_items_and_compacts_oversized_data(monkeypatch):
    provider = make_provider(configured_context=1024, max_tokens=64, context_safety_margin=4096)
    monkeypatch.setattr(provider, "_server_context_size", lambda: 1024)
    normal = provider._safe_context_text({
        "dtcs": list(range(12)),
        "symptoms": list(range(8)),
        "evidence": list(range(12)),
        "recent_live_signals": list(range(20)),
        "safety_instruction": "Do not confirm unsupported failures.",
    })
    payload = json.loads(normal)
    assert payload["dtcs"] == list(range(4, 12))
    assert payload["symptoms"] == list(range(2, 8))
    assert payload["evidence"] == list(range(2, 12))
    assert payload["recent_live_signals"] == list(range(4, 20))

    oversized = provider._safe_context_text({"vehicle": {"raw": "x" * 9000}})
    assert len(oversized) < 1700
    assert oversized.endswith("[CONTEXT_COMPACTED]")


def test_build_payload_uses_resolved_model_and_limits_generation_tokens(monkeypatch):
    provider = make_provider(model="configured", max_tokens=700, temperature=0.4)
    monkeypatch.setattr(provider, "_server_context_size", lambda: 1024)
    monkeypatch.setattr(provider, "_resolve_model_id", lambda: "runtime-model")
    payload = provider._build_payload("Analyze P0302", {"dtcs": ["P0302"]})
    assert payload["model"] == "runtime-model"
    assert payload["max_tokens"] == 341
    assert payload["temperature"] == 0.4
    assert payload["stream"] is False
    assert "Never invent measurements" in payload["messages"][0]["content"]
    assert "Analyze P0302" in payload["messages"][1]["content"]


def test_generate_sync_maps_successful_response(monkeypatch):
    provider = make_provider(model="configured", api_key="top-secret")
    monkeypatch.setattr(provider, "_build_payload", lambda prompt, context: {"model": "resolved", "messages": []})
    captured = {}
    def urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["headers"] = dict(request.header_items())
        return FakeResponse(json.dumps({"choices": [{"message": {"content": "  Check pressure.  "}}]}).encode("utf-8"))
    monkeypatch.setattr(llama, "urlopen", urlopen)

    result = provider._generate_sync("prompt", {})
    assert result.text == "Check pressure."
    assert result.model == "resolved"
    assert result.provider == "llama-server"
    assert captured["url"] == "http://127.0.0.1:8000/v1/chat/completions"
    assert captured["timeout"] == provider.config.timeout_s
    assert captured["payload"]["model"] == "resolved"
    assert any(key.lower() == "authorization" for key in captured["headers"])


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (HTTPError("http://localhost", 400, "bad request", {}, io.BytesIO(b"exceeds the available context size")), "llama-server context overflow"),
        (HTTPError("http://localhost", 500, "server error", {}, io.BytesIO(b"oops")), "llama-server inference HTTP 500"),
        (URLError("offline"), "llama-server inference failed"),
        (TimeoutError("slow"), "llama-server inference failed"),
    ],
)
def test_generate_sync_wraps_http_and_transport_errors(monkeypatch, error, message):
    provider = make_provider()
    monkeypatch.setattr(provider, "_build_payload", lambda *_args: {"model": "m"})
    monkeypatch.setattr(llama, "urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(error))
    with pytest.raises(RuntimeError, match=message):
        provider._generate_sync("prompt", {})


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (b"not-json", "llama-server inference failed"),
        (b'{"choices":[]}', "llama-server returned no choices"),
        (b'{"choices":[{"message":{"content":"  "}}]}', "llama-server returned an empty response"),
    ],
)
def test_generate_sync_rejects_invalid_or_empty_responses(monkeypatch, body, message):
    provider = make_provider()
    monkeypatch.setattr(provider, "_build_payload", lambda *_args: {"model": "m"})
    monkeypatch.setattr(llama, "urlopen", lambda *_args, **_kwargs: FakeResponse(body))
    with pytest.raises(RuntimeError, match=message):
        provider._generate_sync("prompt", {})


@pytest.mark.asyncio
async def test_async_generate_delegates_to_thread_worker(monkeypatch):
    provider = make_provider(timeout_s=10)
    expected = llama.LLMResponse(text="ok", model="m", provider="llama-server", raw={})
    seen = []
    def worker(prompt, context):
        seen.append((prompt, context))
        return expected
    monkeypatch.setattr(provider, "_generate_sync", worker)
    result = await provider.generate("diagnose", {"dtcs": ["P0302"]})
    assert result is expected
    assert seen == [("diagnose", {"dtcs": ["P0302"]})]
