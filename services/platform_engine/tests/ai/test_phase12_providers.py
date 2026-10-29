import pytest

from ai.embeddings.providers import HashEmbeddingProvider, create_embedding_provider
from ai.rag.reranker import LexicalReranker, create_reranker
from ai.rag.store import RetrievalHit


@pytest.mark.asyncio
async def test_hash_embeddings_are_stable_across_calls():
    provider = HashEmbeddingProvider(32)
    first = await provider.embed(['P0302 LPG misfire'])
    second = await provider.embed(['P0302 LPG misfire'])
    assert first == second
    assert len(first[0]) == 32


def test_factory_defaults_to_offline_stack(monkeypatch):
    monkeypatch.delenv('RAG_EMBEDDING_PROVIDER', raising=False)
    monkeypatch.delenv('RAG_RERANKER_PROVIDER', raising=False)
    assert isinstance(create_embedding_provider(dimensions=32), HashEmbeddingProvider)
    assert isinstance(create_reranker(), LexicalReranker)


def test_cross_encoder_is_lazy_optional():
    from ai.rag.reranker import CrossEncoderReranker
    reranker = CrossEncoderReranker(model_name='missing-model')
    with pytest.raises(RuntimeError, match='sentence-transformers is not installed'):
        reranker.rerank('P0302', [RetrievalHit('c', 'd', 'misfire', {}, 0.9)], top_k=1)
