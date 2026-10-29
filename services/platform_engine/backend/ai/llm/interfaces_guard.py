from __future__ import annotations
from dataclasses import dataclass
from diagnostic.models import DiagnosticSession

@dataclass(frozen=True)
class SafePromptContext:
    vehicle: dict | None
    evidence: list[dict]
    hypotheses: list[dict]
    tests: list[dict]
    retrieved: list[dict]
    response_language: str = "en"

    @classmethod
    def from_session(cls, session: DiagnosticSession, retrieved: list[dict], response_language: str = "en") -> "SafePromptContext":
        return cls(
            vehicle=session.vehicle.model_dump(mode="json") if session.vehicle else None,
            evidence=[e.model_dump(mode="json") for e in session.evidence],
            hypotheses=[h.model_dump(mode="json") for h in session.hypotheses],
            tests=[t.model_dump(mode="json") for t in session.recommendations],
            retrieved=retrieved,
            response_language=response_language,
        )

    def to_prompt(self) -> str:
        return (
            "Explain the current diagnostic state. Use ONLY these facts and retrieved sources. "
            "Do not create measurements. Do not confirm a component failure unless evidence status is confirmed. "
            "State what is reported vs measured vs inferred, and propose the next diagnostic test.\n"
            f"Vehicle: {self.vehicle}\nEvidence: {self.evidence}\nHypotheses: {self.hypotheses}\n"
            f"Recommended tests: {self.tests}\nRetrieved sources: {self.retrieved}"
        )
