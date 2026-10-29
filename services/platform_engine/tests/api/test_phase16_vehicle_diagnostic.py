from fastapi.testclient import TestClient
from api.main import app

c = TestClient(app)

def test_vehicle_diagnostic_api():
    session = c.post('/api/v1/sessions', json={'make':'Mercedes-Benz','model':'W211','year':2006,'engine':'M272 3.5','fuel':['petrol','LPG']}).json()
    sid = session['session_id']
    r = c.post(f'/api/v1/vehicle-diagnostic/sessions/{sid}/connect', json={'adapter':'simulator'})
    assert r.status_code == 200
    ecu = c.get(f'/api/v1/vehicle-diagnostic/sessions/{sid}/ecu')
    assert ecu.status_code == 200
    assert ecu.json()['vin'] == 'VINTEST1234567890'
    dtcs = c.post(f'/api/v1/vehicle-diagnostic/sessions/{sid}/dtcs/read')
    assert dtcs.status_code == 200 and dtcs.json()['records']
    trace = c.get(f'/api/v1/vehicle-diagnostic/sessions/{sid}/trace')
    assert trace.status_code == 200 and len(trace.json()['events']) >= 1
    session_after = c.get(f'/api/v1/sessions/{sid}').json()
    assert any('Simulated DTC' in e['fact'] and e['source'] == 'SIMULATOR'
               and e['status'] == 'simulated' for e in session_after['evidence'])
    status = c.get(f'/api/v1/vehicle-diagnostic/sessions/{sid}/status').json()
    assert status['can'] and status['isotp'] and status['uds'] and not status['dtc_clear']
