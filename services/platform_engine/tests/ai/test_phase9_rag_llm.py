from pathlib import Path
import asyncio

import pytest

from ai.embeddings.providers import HashEmbeddingProvider
from ai.rag.reranker import LexicalReranker
from ai.rag.store import HybridKnowledgeStore, KnowledgeDocument
from ai.evaluation.grounding import GroundingEvaluator
from ai.evaluation.golden import GoldenCase, GoldenCaseEvaluator


def test_hash_embeddings_are_normalized_and_deterministic():
    provider = HashEmbeddingProvider(64)
    a = asyncio.run(provider.embed(["P0302 cylinder misfire"]))[0]
    b = asyncio.run(provider.embed(["P0302 cylinder misfire"]))[0]
    assert a == b
    assert abs(sum(x * x for x in a) - 1.0) < 1e-8


def test_reranker_prioritizes_exact_phrase():
    store = HybridKnowledgeStore([
        KnowledgeDocument("a", "P0302", "Cylinder 2 misfire diagnostic information"),
        KnowledgeDocument("b", "Generic", "Misfire information"),
    ])
    hits = store.search("P0302 cylinder 2 misfire")
    reranked = LexicalReranker().rerank("P0302 cylinder 2 misfire", hits)
    assert reranked[0].hit.document_id == "a"


def test_grounding_gate_flags_missing_terms():
    result = GroundingEvaluator().evaluate(
        "The issue may be related to LPG calibration.",
        ["LPG calibration"],
        {"uncertainty", "LPG"},
    )
    assert not result.grounded
    assert result.unsupported_claims == 0


@pytest.mark.parametrize(
    "generated_text",
    [
        pytest.param("confirmed_coil_failure", id="underscore-token"),
        pytest.param("confirmed coil failure", id="space-separated"),
        pytest.param("Confirmed coil failure.", id="capitalized-punctuated"),
        pytest.param("confirmed-coil-failure", id="hyphen-separated"),
    ],
)
def test_golden_case_evaluator_blocks_forbidden_claim(generated_text):
    case = GoldenCase.load((Path(__file__).resolve().parents[2] / "datasets/golden-cases/LPG_MISFIRE_001.yaml"))
    categories = {
        "LPG fuel delivery / mixture",
        "ignition / combustion",
        "air-fuel / intake",
    }

    result = GoldenCaseEvaluator().evaluate(categories, generated_text, case)

    assert any(
        claim.casefold() == "confirmed coil failure"
        for claim in result.forbidden_claims_present
    )
    assert result.category_coverage == pytest.approx(0.75)
    assert not result.passed
