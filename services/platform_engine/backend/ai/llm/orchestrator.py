from __future__ import annotations
from ai.interfaces import LLMProvider, LLMResponse
from diagnostic.models import DiagnosticSession

class DiagnosticLLMOrchestrator:
    """LLM is constrained to explanation/orchestration; deterministic reasoning remains authoritative."""
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    def build_context(self, session: DiagnosticSession, retrieved: list[dict] | None = None, language: str = "en") -> dict:
        return {
            "session_id": str(session.session_id),
            "vehicle": session.vehicle.model_dump() if session.vehicle else None,
            "evidence": [e.model_dump(mode="json") for e in session.evidence],
            "hypotheses": [h.model_dump(mode="json") for h in session.hypotheses],
            "recommended_tests": [t.model_dump(mode="json") for t in session.recommendations],
            "retrieved_knowledge": retrieved or [],
            "instruction": "Do not invent measurements, confirmations, or component failures. Separate evidence from inference.",
            "response_language": language,
        }

    async def explain(self, session: DiagnosticSession, retrieved: list[dict] | None = None, language: str = "en") -> LLMResponse:
        context = self.build_context(session, retrieved, language)
        prompt = (
            "Explain the current diagnostic reasoning using only the supplied evidence and clearly label uncertainty. "
            f"Respond in language code '{language}'."
        )
        return await self.provider.generate(prompt, context)
