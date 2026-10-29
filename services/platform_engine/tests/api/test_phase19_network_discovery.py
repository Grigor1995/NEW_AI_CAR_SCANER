from fastapi.testclient import TestClient
from backend.api.main import app


def test_network_discovery_api():
    client = TestClient(app)
    sid = client.post('/api/v1/sessions').json()['session_id']
    payload = {
        'bus': 'CAN1',
        'frames': [
            {'arbitration_id': 2016, 'data_hex': '1003', 'timestamp_ns': 0},
            {'arbitration_id': 2024, 'data_hex': '5003', 'timestamp_ns': 2_000_000},
            {'arbitration_id': 2016, 'data_hex': '1003', 'timestamp_ns': 100_000_000},
            {'arbitration_id': 2024, 'data_hex': '5003', 'timestamp_ns': 102_000_000},
        ],
    }
    response = client.post(f'/api/v1/network-discovery/sessions/{sid}/frames', json=payload)
    assert response.status_code == 200
    mapped = client.get(f'/api/v1/network-discovery/sessions/{sid}/map')
    assert mapped.status_code == 200
    data = mapped.json()
    assert data['summary']['inferred_uds_pairs'] == 1
    assert data['ecu_candidates'][0]['classification'] == 'UDS_REQUEST_RESPONSE_INFERRED'
