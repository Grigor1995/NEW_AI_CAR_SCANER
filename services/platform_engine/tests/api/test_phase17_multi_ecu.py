from fastapi.testclient import TestClient
from api.main import app

c = TestClient(app)

def test_multi_ecu_api_workflow():
    session = c.post('/api/v1/sessions', json={'make':'Mercedes-Benz','model':'W211','year':2006,'engine':'M272 3.5','fuel':['petrol','LPG']}).json()
    sid = session['session_id']
    payload = {
        'gateways': [{'gateway_id':'gw1','name':'Central Gateway','bus':'CAN0'}],
        'ecus': [
            {'ecu_id':'engine','name':'Engine ECU','request_id':2016,'response_id':2024,'vin':'VINTEST1234567890','dtc_records':[[197120,40]]},
            {'ecu_id':'transmission','name':'Transmission ECU','request_id':2017,'response_id':2025,'vin':'VINTEST1234567890','dtc_records':[[197120,40]]}
        ]
    }
    r = c.post(f'/api/v1/multi-ecu/sessions/{sid}/connect', json=payload)
    assert r.status_code == 200 and r.json()['ecu_count'] == 2
    top = c.get(f'/api/v1/multi-ecu/sessions/{sid}/topology')
    assert top.status_code == 200 and len(top.json()['ecus']) == 2
    ident = c.post(f'/api/v1/multi-ecu/sessions/{sid}/identify-all')
    assert ident.status_code == 200 and ident.json()['ecus']['engine']['vin'] == 'VINTEST1234567890'
    dtcs = c.post(f'/api/v1/multi-ecu/sessions/{sid}/dtcs/read-all')
    assert dtcs.status_code == 200
    assert len(dtcs.json()['correlations']) == 1
    assert dtcs.json()['correlations'][0]['type'] == 'SHARED_DTC'
    trace = c.get(f'/api/v1/multi-ecu/sessions/{sid}/trace')
    assert trace.status_code == 200 and trace.json()['events']
