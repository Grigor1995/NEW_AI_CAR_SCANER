import sys
import types

import pytest

import ai.embeddings.providers as providers


@pytest.mark.asyncio
async def test_hash_provider_handles_empty_and_punctuation_only_text():
    provider = providers.HashEmbeddingProvider(dimensions=16)
    vectors = await provider.embed(["", "!!! ...", "P0302 misfire", "P0302 misfire"])

    assert len(vectors) == 4
    assert vectors[0] == [0.0] * 16
    assert vectors[1] == [0.0] * 16
    assert vectors[2] == vectors[3]
    assert sum(value * value for value in vectors[2]) == pytest.approx(1.0)


def test_hash_provider_rejects_too_small_dimensions():
    with pytest.raises(ValueError, match="dimensions must be >= 8"):
        providers.HashEmbeddingProvider(7)


def test_sentence_transformer_provider_loads_lazily_and_caches(monkeypatch):
    calls = []

    class FakeModel:
        def get_sentence_embedding_dimension(self):
            return 3
        def encode(self, texts, **kwargs):
            calls.append((texts, kwargs))
            return types.SimpleNamespace(tolist=lambda: [[0.1, 0.2, 0.3] for _ in texts])

    models = []
    module = types.SimpleNamespace(
        SentenceTransformer=lambda name, device: models.append((name, device)) or FakeModel()
    )
    monkeypatch.setitem(sys.modules, "sentence_transformers", module)
    provider = providers.SentenceTransformerEmbeddingProvider("fake-model", "cpu", normalize=False)

    assert models == []
    assert provider.dimensions == 3
    assert provider.dimensions == 3
    result = __import__("asyncio").run(provider.embed(["P0302"]))

    assert result == [[0.1, 0.2, 0.3]]
    assert models == [("fake-model", "cpu")]
    assert calls[0][1] == {
        "normalize_embeddings": False,
        "convert_to_numpy": True,
        "show_progress_bar": False,
    }


def test_sentence_transformer_provider_wraps_missing_dependency(monkeypatch):
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)
    provider = providers.SentenceTransformerEmbeddingProvider("not-downloaded")
    with pytest.raises(RuntimeError, match="sentence-transformers is not installed"):
        provider._load()


@pytest.mark.asyncio
async def test_fastembed_provider_accepts_numpy_like_and_plain_vectors(monkeypatch):
    class NumpyLike:
        def tolist(self):
            return [0.1, 0.2]
    class FakeTextEmbedding:
        def __init__(self, model_name):
            assert model_name == "fake-embed"
        def embed(self, texts):
            assert texts == ["one", "two"]
            return iter([NumpyLike(), [0.3, 0.4]])

    monkeypatch.setitem(
        sys.modules, "fastembed",
        types.SimpleNamespace(TextEmbedding=FakeTextEmbedding),
    )
    provider = providers.FastEmbedEmbeddingProvider("fake-embed")
    assert await provider.embed(["one", "two"]) == [[0.1, 0.2], [0.3, 0.4]]


def test_fastembed_provider_wraps_missing_dependency(monkeypatch):
    monkeypatch.setitem(sys.modules, "fastembed", None)
    provider = providers.FastEmbedEmbeddingProvider("missing-model")
    with pytest.raises(RuntimeError, match="fastembed is not installed"):
        provider._load()


@pytest.mark.parametrize(
    ("provider_name", "expected"),
    [
        ("sentence_transformers", providers.SentenceTransformerEmbeddingProvider),
        ("sentence-transformers", providers.SentenceTransformerEmbeddingProvider),
        ("st", providers.SentenceTransformerEmbeddingProvider),
        ("fastembed", providers.FastEmbedEmbeddingProvider),
    ],
)
def test_embedding_factory_provider_aliases(provider_name, expected):
    assert isinstance(providers.create_embedding_provider(provider_name), expected)


def test_embedding_factory_rejects_unknown_provider():
    with pytest.raises(ValueError, match="unsupported embedding provider: remote"):
        providers.create_embedding_provider("REMOTE")
