from uuid import uuid4

from diagnostic.models import DiagnosticSession, DiagnosticTest, TestResult
from diagnostic.decision import DiagnosticDecisionEngine
from telemetry.channels import channel_name
from telemetry.models import TelemetrySample
from telemetry.service import TelemetryService


def test_rule_specific_tests_remain_executable_and_incomplete_remains_open():
    session=DiagnosticSession()
    test=DiagnosticTest(name='Inspect battery terminal voltage',purpose='Compare the measured voltage',
                        risk_level='MEDIUM',prerequisites=['Use rated measurement equipment'])
    session.recommendations=[test]
    engine=DiagnosticDecisionEngine()
    candidate=engine.build_plan(session).candidates[0]
    assert candidate.test_id == test.id
    assert candidate.risk_level == 'MEDIUM' and candidate.prerequisites == test.prerequisites
    engine.refresh_recommendations(session)
    assert session.recommendations[0].id == test.id
    session.test_results.append(TestResult(test_id=test.id,test_name=test.name,result='INCOMPLETE'))
    assert engine.build_plan(session).candidates[0].test_id == test.id
    session.test_results.append(TestResult(test_id=test.id,test_name=test.name,result='PASS'))
    assert engine.build_plan(session).candidates == []
    assert engine.build_plan(DiagnosticSession()).candidates == []


def test_hex_pid_telemetry_has_human_readable_names_without_changing_ids():
    sid=uuid4()
    service=TelemetryService()
    service.append([TelemetrySample(session_id=sid,timestamp_ms=1,pid='0x0C',value=750,source='SIMULATOR')])
    summary=service.summarize(sid)
    assert summary.stats[0].pid == '0x0C'
    assert summary.stats[0].display_name == 'Engine speed'
    assert channel_name('0x05') == 'Coolant temperature'
    assert channel_name('0x0D') == 'Vehicle speed'
    assert channel_name('0x11') == 'Throttle position'
    assert channel_name('custom-sensor') == 'custom-sensor'
