from fastapi.testclient import TestClient
from api.main import app
from backend.telemetry.analysis import compute_stats, detect_events
from backend.telemetry.models import TelemetrySample, SignalEventType
from diagnostic.models import DiagnosticSession


def test_signal_stats_calculate_rate_and_deltas():
    sid = DiagnosticSession().session_id
    samples = [
        TelemetrySample(session_id=sid, timestamp_ms=0, pid="rpm", value=1000),
        TelemetrySample(session_id=sid, timestamp_ms=1000, pid="rpm", value=1500),
        TelemetrySample(session_id=sid, timestamp_ms=2000, pid="rpm", value=1800),
    ]
    stats = compute_stats(sid, "rpm", samples)
    assert stats.count == 3
    assert stats.max_value == 1800
    assert stats.sample_rate_hz == 1.0
    assert stats.mean_abs_delta == 400
    assert stats.slope_per_second == 400


def test_signal_event_detection_finds_large_step():
    sid = DiagnosticSession().session_id
    samples = [
        TelemetrySample(session_id=sid, timestamp_ms=0, pid="rpm", value=1200),
        TelemetrySample(session_id=sid, timestamp_ms=100, pid="rpm", value=2600),
    ]
    events = detect_events(sid, "rpm", samples)
    kinds = {e.event_type for e in events}
    assert SignalEventType.STEP_CHANGE in kinds
    assert SignalEventType.RATE_SPIKE in kinds


def test_invalid_samples_do_not_drive_stats():
    sid = DiagnosticSession().session_id
    samples = [
        TelemetrySample(session_id=sid, timestamp_ms=0, pid="battery_voltage", value=12.5),
        TelemetrySample(session_id=sid, timestamp_ms=100, pid="battery_voltage", value=30.0, quality="INVALID"),
    ]
    stats = compute_stats(sid, "battery_voltage", samples)
    assert stats.count == 1
    assert stats.max_value == 12.5


def test_telemetry_api_generates_measured_evidence():
    c = TestClient(app)
    r = c.post('/api/v1/sessions', json={'make':'Mercedes-Benz','model':'W211','year':2006,'engine':'M272 3.5','fuel':['petrol','LPG']})
    sid = r.json()['session_id']
    payload = {
        'samples': [
            {'session_id': sid, 'timestamp_ms': 0, 'pid': 'battery_voltage', 'value': 12.5, 'unit': 'V'},
            {'session_id': sid, 'timestamp_ms': 1000, 'pid': 'battery_voltage', 'value': 9.0, 'unit': 'V'},
        ]
    }
    assert c.post(f'/api/v1/telemetry/sessions/{sid}/samples', json=payload).json()['accepted'] == 2
    out = c.post(f'/api/v1/telemetry/sessions/{sid}/analyze')
    assert out.status_code == 200
    assert len(out.json()['events']) >= 1
    session = c.get(f'/api/v1/sessions/{sid}').json()
    assert any(x['source'] == 'VEHICLE_MEASURED' for x in session['evidence'])


def test_telemetry_analysis_is_idempotent_for_same_event():
    c = TestClient(app)
    sid = c.post('/api/v1/sessions', json={'make':'Test','model':'Car'}).json()['session_id']
    c.post(f'/api/v1/telemetry/sessions/{sid}/samples', json={'samples': [
        {'session_id': sid, 'timestamp_ms': 0, 'pid': 'rpm', 'value': 1000},
        {'session_id': sid, 'timestamp_ms': 100, 'pid': 'rpm', 'value': 2500},
    ]})
    first = c.post(f'/api/v1/telemetry/sessions/{sid}/analyze').json()['evidence_added']
    second = c.post(f'/api/v1/telemetry/sessions/{sid}/analyze').json()['evidence_added']
    assert first > 0
    assert second == 0
