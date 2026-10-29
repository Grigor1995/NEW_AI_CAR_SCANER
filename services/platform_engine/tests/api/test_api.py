from fastapi.testclient import TestClient
from api.main import app
c=TestClient(app)
def test_health(): assert c.get('/health').json()['status']=='ok'
def test_session_flow():
    r=c.post('/api/v1/sessions',json={'make':'Mercedes-Benz','model':'W211','year':2006,'engine':'M272 3.5','fuel':['petrol','LPG']}); assert r.status_code==200; sid=r.json()['session_id']
    assert c.post(f'/api/v1/sessions/{sid}/symptoms',json={'raw_text':'Engine shakes below 2000 RPM during acceleration on LPG. Petrol works normally.'}).status_code==200
    assert c.post(f'/api/v1/sessions/{sid}/dtcs',json={'code':'P0302'}).status_code==200
    r=c.post(f'/api/v1/sessions/{sid}/analyze'); assert r.status_code==200 and r.json()['hypotheses']
