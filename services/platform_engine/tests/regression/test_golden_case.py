from pathlib import Path

import yaml

from diagnostic.models import (
    DTC,
    DiagnosticSession,
    Evidence,
    EvidenceSource,
    EvidenceStatus,
    Vehicle,
)
from diagnostic.rules import DiagnosticReasoningEngine


def test_golden_case():
    case = yaml.safe_load(
        (Path(__file__).resolve().parents[2] / "datasets/golden-cases/LPG_MISFIRE_001.yaml").read_text(encoding="utf-8")
    )
    session = DiagnosticSession(vehicle=Vehicle(**case["vehicle"]))
    for symptom in case["symptoms"]:
        session.evidence.append(
            Evidence(
                fact=symptom,
                source=EvidenceSource.USER_REPORTED,
                status=EvidenceStatus.REPORTED,
            )
        )
    session.dtcs = [DTC(code=code) for code in case["dtc"]]

    result = DiagnosticReasoningEngine().analyze(session)
    categories = {hypothesis.category for hypothesis in result.hypotheses}
    assert set(case["expected_categories"]) <= categories

    statements = " ".join(hypothesis.statement.lower() for hypothesis in result.hypotheses)
    for forbidden in case["forbidden_claims"]:
        assert forbidden.lower() not in statements

    recommendations = " ".join(
        f"{item.name} {item.purpose}".lower() for item in result.recommendations
    )
    assert any(
        evidence in recommendations
        for evidence in ("lpg pressure", "lpg injector", "stft/ltft")
    )
