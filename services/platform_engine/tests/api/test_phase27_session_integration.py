from fastapi.testclient import TestClient
from api.main import app
from api.device_routes import manager
from api.state import sessions


def setup_function():
    manager.devices.clear()
    manager.connections.clear()
    sessions.clear()


def teardown_function():
    manager.devices.clear()
    manager.connections.clear()
    sessions.clear()


def test_vci_binds_to_session_and_syncs_obd_data_into_session():
    client = TestClient(app)

    device = client.post('/api/v1/devices/simulator').json()
    device_id = device['device_id']
    assert client.post(f'/api/v1/devices/{device_id}/connect', json={'config': {}}).status_code == 200

    session = client.post('/api/v1/sessions', json={
        'make': 'Mercedes-Benz',
        'model': 'W211',
        'year': 2006,
        'engine': 'M272 3.5',
        'fuel': ['Petrol', 'LPG'],
        'ecu': 'ME 9.7',
    }).json()
    session_id = session['session_id']

    bound = client.post(
        f'/api/v1/vehicle-diagnostic/sessions/{session_id}/device/bind',
        json={'device_id': device_id},
    )
    assert bound.status_code == 200, bound.text
    assert bound.json()['connected'] is True

    sync = client.post(f'/api/v1/vehicle-diagnostic/sessions/{session_id}/obd/sync')
    assert sync.status_code == 200, sync.text
    body = sync.json()
    assert body['vin'] == 'WDD2110801A123456'
    assert body['dtcs'] == ['P0102']
    assert body['live_data']['rpm'] == 1696.0
    assert body['evidence_added'] >= 4
    assert body['telemetry_measurements_added'] >= 4

    stored = client.get(f'/api/v1/sessions/{session_id}').json()
    assert stored['connected_device_id'] == device_id
    assert stored['vehicle']['metadata']['vin'] == 'WDD2110801A123456'
    assert any(e['source_ref'] == 'SIM:OBD:MODE:09:02' for e in stored['evidence'])
    assert any(e['source_ref'] == 'SIM:OBD:MODE:03' and e['metadata']['dtc'] == 'P0102' for e in stored['evidence'])
    assert all(e['source'] == 'SIMULATOR' and e['status'] == 'simulated'
               and e['metadata']['simulated'] for e in stored['evidence'])
    assert all(m['source'] == 'SIMULATOR' and m['simulated'] for m in stored['measurements'])
    assert len(stored['measurements']) >= 4
    assert len(stored['live_data']) == 1


def test_sync_requires_a_bound_connected_device():
    client = TestClient(app)
    session = client.post('/api/v1/sessions').json()
    response = client.post(f"/api/v1/vehicle-diagnostic/sessions/{session['session_id']}/obd/sync")
    assert response.status_code == 409


def test_repeated_sync_does_not_duplicate_vin_or_dtc_evidence():
    client = TestClient(app)
    device = client.post('/api/v1/devices/simulator').json()
    did = device['device_id']
    assert client.post(f'/api/v1/devices/{did}/connect').status_code == 200
    session = client.post('/api/v1/sessions').json()
    sid = session['session_id']
    assert client.post(f'/api/v1/vehicle-diagnostic/sessions/{sid}/device/bind', json={'device_id': did}).status_code == 200
    first = client.post(f'/api/v1/vehicle-diagnostic/sessions/{sid}/obd/sync').json()
    second = client.post(f'/api/v1/vehicle-diagnostic/sessions/{sid}/obd/sync').json()
    assert first['vin'] == second['vin']
    stored = client.get(f'/api/v1/sessions/{sid}').json()
    vin_evidence = [e for e in stored['evidence'] if e['source_ref'] == 'SIM:OBD:MODE:09:02']
    dtc_evidence = [e for e in stored['evidence'] if e['source_ref'] == 'SIM:OBD:MODE:03' and e['metadata'].get('dtc') == 'P0102']
    assert len(vin_evidence) == 1
    assert len(dtc_evidence) == 1
