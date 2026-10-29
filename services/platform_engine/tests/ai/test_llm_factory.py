import pytest

import ai.llm.factory as factory


def test_factory_defaults_to_local_llama_server(monkeypatch):
    monkeypatch.delenv("DIAGNOSTIC_LLM_PROVIDER", raising=False)
    sentinel = object()
    captured = []
    monkeypatch.setattr(factory.LlamaServerConfig, "from_env", lambda: sentinel)
    monkeypatch.setattr(
        factory, "LlamaServerLLMProvider",
        lambda config: captured.append(config) or "llama-provider",
    )

    assert factory.build_llm_provider() == "llama-provider"
    assert captured == [sentinel]


@pytest.mark.parametrize(
    "provider",
    ["llama-server", "llama_server", "llamaserver", "local", "LOCAL"],
)
def test_factory_accepts_local_provider_aliases(monkeypatch, provider):
    monkeypatch.setenv("DIAGNOSTIC_LLM_PROVIDER", provider)
    monkeypatch.setattr(factory.LlamaServerConfig, "from_env", lambda: "config")
    monkeypatch.setattr(factory, "LlamaServerLLMProvider", lambda config: (provider, config))

    assert factory.build_llm_provider() == (provider, "config")


@pytest.mark.parametrize("provider", ["openai-compatible", "openai_compatible"])
def test_factory_builds_openai_compatible_provider_from_environment(monkeypatch, provider):
    monkeypatch.setenv("DIAGNOSTIC_LLM_PROVIDER", provider)
    monkeypatch.setenv("LLM_BASE_URL", "http://127.0.0.1:9000/")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setattr(factory, "HttpOpenAICompatibleProvider", lambda config: config)

    config = factory.build_llm_provider()
    assert config.base_url == "http://127.0.0.1:9000/"
    assert config.model == "test-model"
    assert config.api_key == "test-key"


def test_factory_uses_openai_compatible_defaults(monkeypatch):
    monkeypatch.setenv("DIAGNOSTIC_LLM_PROVIDER", "openai-compatible")
    for key in ("LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(factory, "HttpOpenAICompatibleProvider", lambda config: config)

    config = factory.build_llm_provider()
    assert config.base_url == "http://127.0.0.1:1234"
    assert config.model == "local-model"
    assert config.api_key is None


def test_factory_builds_placeholder_provider(monkeypatch):
    monkeypatch.setenv("DIAGNOSTIC_LLM_PROVIDER", "placeholder")
    marker = object()
    monkeypatch.setattr(factory, "LocalLLMProvider", lambda: marker)

    assert factory.build_llm_provider() is marker


def test_factory_rejects_unknown_provider(monkeypatch):
    monkeypatch.setenv("DIAGNOSTIC_LLM_PROVIDER", "remote-magic")

    with pytest.raises(ValueError, match="Unsupported LLM provider: remote-magic"):
        factory.build_llm_provider()
