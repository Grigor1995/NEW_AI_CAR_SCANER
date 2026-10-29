import asyncio
import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.state import sessions

@pytest.mark.asyncio
async def test_acquisition_api():
    client=TestClient(app)
    r=client.post('/api/v1/sessions'); assert r.status_code==200
    sid=r.json()['session_id']
    r=client.post(f'/api/v1/acquisition/sessions/{sid}/start',json={'adapter':'simulator','poll_interval_ms':20,'pids':[12]})
    assert r.status_code==200
    await asyncio.sleep(0.06)
    r=client.get(f'/api/v1/acquisition/sessions/{sid}/status'); assert r.status_code==200
    assert r.json()['stats']['records'] >= 1
    r=client.get(f'/api/v1/acquisition/sessions/{sid}/records'); assert r.status_code==200
    assert r.json()['records']
    r=client.post(f'/api/v1/acquisition/sessions/{sid}/stop'); assert r.status_code==200
    sessions.pop(sid,None)


def test_simulator_parameter_endpoint_validation_and_adapter_boundary():
    from api.acquisition_routes import service
    from acquisition.service import _AcquisitionState
    from uuid import UUID
    with TestClient(app) as client:
        sid = client.post('/api/v1/sessions').json()['session_id']
        path = f'/api/v1/acquisition/sessions/{sid}/simulator/parameters'
        try:
            assert client.put(path, json={}).status_code == 409
            service._states[UUID(sid)] = _AcquisitionState()
            response = client.put(path, json={'speed_kmh': 123, 'coolant_c': 101})
            assert response.status_code == 200
            assert response.json()['speed_kmh'] == 123
            assert client.put(path, json={'speed_kmh': 999}).status_code == 422
            service._states[UUID(sid)].adapter = 'usb'
            assert client.put(path, json={}).status_code == 409
            assert client.put(path.replace(sid, 'missing'), json={}).status_code == 404
        finally:
            sessions.pop(sid, None)
            service._states.pop(UUID(sid), None)
