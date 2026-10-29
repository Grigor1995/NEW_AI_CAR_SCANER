from diagnostic.models import DTC, DiagnosticSession, EvidenceSource, Vehicle
from diagnostic.rules import DiagnosticReasoningEngine


def analyze(text: str, *dtcs: str):
    s = DiagnosticSession(vehicle=Vehicle(make="Generic", model="Test", year=2020, engine="2.0", fuel=["petrol"]))
    s.evidence.append(__import__("diagnostic.models", fromlist=["Evidence"]).Evidence(
        fact=text, source=EvidenceSource.USER_REPORTED, status=__import__("diagnostic.models", fromlist=["EvidenceStatus"]).EvidenceStatus.REPORTED
    ))
    s.dtcs = [DTC(code=x, source=EvidenceSource.ECU_REPORTED) for x in dtcs]
    return DiagnosticReasoningEngine().analyze(s)


def test_lpg_misfire_has_lpg_specific_hypotheses_and_tests():
    s = analyze("Engine shakes during acceleration below 2000 RPM only on LPG; petrol normal.", "P0302")
    cats = {h.category for h in s.hypotheses}
    assert "LPG fuel delivery" in cats
    assert "ignition under LPG load" in cats
    assert any("LPG pressure" in t.name for t in s.recommendations)


def test_maf_fault_does_not_reuse_lpg_answer():
    s = analyze("Engine hesitates and airflow reading looks implausible on petrol.", "P0101")
    cats = {h.category for h in s.hypotheses}
    names = {t.name for t in s.recommendations}
    assert "air metering / MAF" in cats
    assert "LPG fuel delivery" not in cats
    assert any("MAF" in n for n in names)


def test_catalyst_fault_gets_catalyst_specific_plan():
    s = analyze("Check engine light after warm highway driving; no noticeable misfire.", "P0420")
    cats = {h.category for h in s.hypotheses}
    names = {t.name for t in s.recommendations}
    assert "catalyst efficiency" in cats
    assert any("upstream/downstream O2" in n for n in names)
    assert not any("LPG pressure" in n for n in names)


def test_transmission_fault_gets_transmission_specific_plan():
    s = analyze("Harsh 2-3 shift and flare during gear change.", "P0730")
    cats = {h.category for h in s.hypotheses}
    assert "transmission control / gear ratio" in cats
    assert any("commanded gear" in t.name for t in s.recommendations)
