from fastapi.testclient import TestClient
from api.main import app

def test_active_discovery_confirms_passive_candidate():
    c=TestClient(app)
    sid=c.post('/api/v1/sessions').json()['session_id']
    payload={
      'buses':[{'name':'CAN0','bitrate':500000}],
      'ecus':[{'ecu_id':'engine','name':'Engine ECU','request_id':0x7E0,'response_id':0x7E8,'bus':'CAN0','vin':'ACTIVEVIN1234567'}]
    }
    assert c.post(f'/api/v1/multi-bus/sessions/{sid}/connect',json=payload).status_code==200
    frames=[
      {'arbitration_id':0x7E0,'data_hex':'1003','timestamp_ns':0},
      {'arbitration_id':0x7E8,'data_hex':'5003','timestamp_ns':2_000_000},
      {'arbitration_id':0x7E0,'data_hex':'1003','timestamp_ns':100_000_000},
      {'arbitration_id':0x7E8,'data_hex':'5003','timestamp_ns':102_000_000},
    ]
    r=c.post(f'/api/v1/network-discovery/sessions/{sid}/frames',json={'bus':'CAN0','frames':frames}); assert r.status_code==200
    r=c.post(f'/api/v1/network-discovery/sessions/{sid}/active-probe',json={'inter_probe_ms':0,'timeout_ms':500})
    assert r.status_code==200, r.text
    data=r.json(); assert data['results'][0]['classification']=='CONFIRMED_UDS_ECU'
    assert data['results'][0]['identity']['vin']=='ACTIVEVIN1234567'
    assert data['correlation']['confirmed_count']==1
