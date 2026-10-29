from diagnostic.models import DiagnosticSession, Evidence, EvidenceSource, EvidenceStatus
from ai.reasoning.pipeline import DiagnosticIntelligencePipeline
from ai.rag.store import HybridKnowledgeStore, KnowledgeDocument


def _session():
    session = DiagnosticSession()
    session.evidence.append(
        Evidence(
            fact="P0302 misfire under LPG load",
            source=EvidenceSource.USER_REPORTED,
            status=EvidenceStatus.REPORTED,
        )
    )
    return session


def test_pipeline_derives_query_from_session_and_builds_safe_prompt():
    store = HybridKnowledgeStore([
        KnowledgeDocument(
            document_id="manual-1",
            title="P0302 LPG misfire",
            text="Check LPG injector balance and ignition under load.",
            metadata={"source": "curated"},
        )
    ])
    result = DiagnosticIntelligencePipeline(store).run(_session(), language="hy")

    assert result.session.evidence
    assert result.retrieved
    assert result.retrieved[0]["document_id"] == "manual-1"
    assert result.retrieved[0]["metadata"] == {"source": "curated"}
    assert result.retrieved[0]["score"] > 0
    assert "Use ONLY these facts" in result.llm_prompt
    assert "P0302" in result.llm_prompt


def test_pipeline_uses_explicit_query_and_handles_no_retrieval_hits():
    store = HybridKnowledgeStore([
        KnowledgeDocument("unrelated", "Brake service", "Brake pad replacement", {})
    ])
    result = DiagnosticIntelligencePipeline(store).run(
        DiagnosticSession(), query="unmatched cooling-system phrase", language="ru"
    )

    assert result.retrieved == []
    assert "Retrieved sources: []" in result.llm_prompt
