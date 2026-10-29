from fastapi.testclient import TestClient
from api.main import app

def test_phase18_multibus_gateway_api():
    client = TestClient(app)
    session_id = client.post('/api/v1/sessions').json()['session_id']
    payload = {
        'buses': [{'name':'CAN0','bitrate':500000},{'name':'CAN1','bitrate':500000}],
        'ecus': [{'ecu_id':'engine','name':'Engine ECU','request_id':2016,'response_id':2024,'bus':'CAN1','gateway_id':'gw','vin':'APIVIN1234567890'}],
        'gateways': [{'gateway_id':'gw','name':'Central Gateway','bus':'CAN0'}],
        'routes': [{'gateway_id':'gw','source_bus':'CAN0','target_bus':'CAN1','target_ecu_id':'engine'}]
    }
    r=client.post(f'/api/v1/multi-bus/sessions/{session_id}/connect', json=payload)
    assert r.status_code == 200
    r=client.post(f'/api/v1/multi-bus/sessions/{session_id}/identify-all')
    assert r.status_code == 200
    assert r.json()['ecus']['engine']['vin'] == 'APIVIN1234567890'
