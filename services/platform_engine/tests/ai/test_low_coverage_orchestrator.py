from types import SimpleNamespace

import pytest

from ai.interfaces import LLMResponse
from ai.llm.orchestrator import DiagnosticLLMOrchestrator
from diagnostic.models import (
    DiagnosticSession, DiagnosticTest, Evidence, EvidenceSource, EvidenceStatus,
    Hypothesis, Vehicle,
)


def test_build_context_serializes_session_and_applies_defaults():
    session = DiagnosticSession(
        vehicle=Vehicle(make="Mercedes-Benz", model="E350", year=2006),
        evidence=[Evidence(
            fact="P0302 reported", source=EvidenceSource.USER_REPORTED,
            status=EvidenceStatus.REPORTED,
        )],
        hypotheses=[Hypothesis(category="ignition", statement="Possible ignition issue")],
        recommendations=[DiagnosticTest(name="Inspect plugs", purpose="Check ignition")],
    )

    context = DiagnosticLLMOrchestrator(SimpleNamespace()).build_context(session)

    assert context["session_id"] == str(session.session_id)
    assert context["vehicle"]["make"] == "Mercedes-Benz"
    assert context["evidence"][0]["fact"] == "P0302 reported"
    assert context["hypotheses"][0]["statement"] == "Possible ignition issue"
    assert context["recommended_tests"][0]["name"] == "Inspect plugs"
    assert context["retrieved_knowledge"] == []
    assert context["response_language"] == "en"
    assert "Do not invent measurements" in context["instruction"]


def test_build_context_handles_missing_vehicle_and_supplied_retrieval():
    session = DiagnosticSession()
    retrieved = [{"title": "OEM note", "score": 0.8}]
    context = DiagnosticLLMOrchestrator(SimpleNamespace()).build_context(
        session, retrieved=retrieved, language="hy"
    )

    assert context["vehicle"] is None
    assert context["retrieved_knowledge"] == retrieved
    assert context["response_language"] == "hy"


@pytest.mark.asyncio
async def test_explain_sends_language_instruction_and_context_to_provider():
    session = DiagnosticSession()
    captured = {}

    class FakeProvider:
        async def generate(self, prompt, context):
            captured.update(prompt=prompt, context=context)
            return LLMResponse(text="Խափանման հավանական պատճառը...", model="fake", provider="test")

    response = await DiagnosticLLMOrchestrator(FakeProvider()).explain(
        session, retrieved=[{"document_id": "case-1"}], language="hy"
    )

    assert response.text.startswith("Խափանման")
    assert captured["context"]["response_language"] == "hy"
    assert captured["context"]["retrieved_knowledge"] == [{"document_id": "case-1"}]
    assert "language code 'hy'" in captured["prompt"]
    assert "clearly label uncertainty" in captured["prompt"]
