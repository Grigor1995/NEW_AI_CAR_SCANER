from __future__ import annotations
import re
from diagnostic.models import EvidenceSource, EvidenceStatus, Evidence, Symptom, DTC

class StructuredEvidenceExtractor:
    """Conservative rule-based extraction: converts language into explicit evidence, never a diagnosis."""

    PATTERNS = {
        "fuel_mode_lpg": [r"\blpg\b", r"gas mode", r"on lpg"],
        "fuel_mode_petrol": [r"\bpetrol\b", r"\bgasoline\b", r"\bbenzine\b"],
        "misfire": [r"misfire", r"shak(?:e|ing|es)", r"rough idle", r"jerk(?:ing|s)"],
        "acceleration": [r"acceleration", r"accelerat(?:e|ing|ion)", r"under load"],
        "below_2000_rpm": [r"below\s*2000\s*rpm", r"under\s*2000\s*rpm", r"<\s*2000\s*rpm"],
        "petrol_normal": [r"petrol.*normal", r"normal.*petrol", r"runs fine on petrol"],
    }

    def extract(self, text: str, source: EvidenceSource = EvidenceSource.USER_REPORTED) -> list[Evidence]:
        raw = " ".join(text.strip().split())
        if not raw:
            return []
        out: list[Evidence] = [Evidence(fact=raw, source=source, status=EvidenceStatus.REPORTED)]
        lowered = raw.lower()
        for key, patterns in self.PATTERNS.items():
            if any(re.search(p, lowered) for p in patterns):
                out.append(Evidence(fact=key, source=source, status=EvidenceStatus.REPORTED, confidence=0.8, metadata={"derived_from": raw}))
        return out

    def from_symptom(self, symptom: Symptom) -> list[Evidence]:
        out = self.extract(symptom.raw_text)
        if symptom.normalized:
            for key, value in symptom.normalized.items():
                out.append(Evidence(fact=f"{key}={value}", source=EvidenceSource.USER_REPORTED, status=EvidenceStatus.REPORTED, confidence=0.9))
        return out

    def from_dtc(self, dtc: DTC) -> Evidence:
        status = EvidenceStatus.MEASURED if dtc.source == EvidenceSource.ECU_REPORTED else EvidenceStatus.REPORTED
        return Evidence(fact=dtc.code.upper(), source=dtc.source, status=status, confidence=0.95 if status == EvidenceStatus.MEASURED else 0.8)
