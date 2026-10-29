from diagnostic.models import *
from diagnostic.rules import DiagnosticReasoningEngine
def test_lpg_case_does_not_confirm_component_failure():
    s=DiagnosticSession(vehicle=Vehicle(make='Mercedes-Benz',model='W211',year=2006,engine='M272 3.5',fuel=['petrol','LPG']))
    for fact in ['Engine misfire/shaking only on LPG','Petrol normal','Acceleration below 2000 RPM']:
        s.evidence.append(Evidence(fact=fact,source=EvidenceSource.USER_REPORTED,status=EvidenceStatus.REPORTED))
    s.dtcs.append(DTC(code='P0302')); out=DiagnosticReasoningEngine().analyze(s)
    assert out.hypotheses and any(h.category=='LPG injection' for h in out.hypotheses)
    assert all('confirmed' not in h.statement.lower() for h in out.hypotheses)
