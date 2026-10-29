from io import BytesIO
import pytest
from fastapi.testclient import TestClient
from api.main import app
from api import client_features_routes as features
from api.state import sessions
from diagnostic.models import DiagnosticSession, Vehicle, DTC


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(features.persistence, 'enabled', False)
    monkeypatch.setattr(features, '_profile_cache', {})
    return TestClient(app)


def test_profile_crud_is_shared_and_preserves_sessions(client):
    vehicle = {'make': 'Ford', 'model': 'Mondeo', 'year': 2011, 'engine': '2.0 TDCi', 'fuel': ['diesel']}
    created = client.post('/api/v1/vehicle-profiles', json={'name': 'Car', 'vehicle': vehicle})
    assert created.status_code == 201
    profile = created.json()
    sid = client.post('/api/v1/sessions', json=vehicle).json()['session_id']
    assert client.get('/api/v1/vehicle-profiles').json() == [profile]
    vehicle['year'] = 2012
    assert client.put('/api/v1/vehicle-profiles/' + profile['id'], json={'vehicle': vehicle}).json()['vehicle']['year'] == 2012
    assert client.delete('/api/v1/vehicle-profiles/' + profile['id']).status_code == 200
    assert client.get('/api/v1/vehicle-profiles').json() == []
    assert client.get('/api/v1/sessions/' + sid).status_code == 200
    assert client.delete('/api/v1/vehicle-profiles/' + profile['id']).status_code == 404
    assert client.put('/api/v1/vehicle-profiles/missing', json={'vehicle': vehicle}).status_code == 404


def test_profiles_survive_cache_reset_with_database(monkeypatch, tmp_path):
    from sqlalchemy import create_engine
    engine = create_engine('sqlite:///' + str(tmp_path / 'profiles.sqlite'))
    monkeypatch.setattr(features.persistence, 'enabled', True)
    monkeypatch.setattr(features.persistence, 'engine', engine)
    profile = features.create_profile(features.ProfileRequest(vehicle=Vehicle(make='Toyota', model='Corolla')))
    features._profile_cache.clear()
    assert features.list_profiles()[0]['vehicle']['model'] == 'Corolla'
    features.update_profile(profile['id'], features.ProfileRequest(vehicle=Vehicle(make='BMW',model='3 Series')))
    assert features.list_profiles()[0]['vehicle']['make'] == 'BMW'
    features.delete_profile(profile['id'])
    assert features.list_profiles() == []
    engine.dispose()


@pytest.mark.parametrize('language', ['en', 'hy', 'ru'])
def test_unicode_pdf_and_json_hide_internal_ids(client, language):
    from pypdf import PdfReader
    session = DiagnosticSession(vehicle=Vehicle(make='Mercedes-Benz', model='E-Class'), dtcs=[DTC(code='P0302')])
    sid = str(session.session_id)
    session.audit_log.append({'event': 'Example', 'session_id': sid, 'nested': [{'session_id': sid}]})
    sessions[sid] = session
    report = client.get(f'/api/v1/sessions/{sid}/report', params={'format': 'json', 'language': language})
    assert report.status_code == 200
    assert sid not in report.text and 'session_id' not in report.text
    pdf = client.get(f'/api/v1/sessions/{sid}/report', params={'format': 'pdf', 'language': language})
    assert pdf.status_code == 200
    assert pdf.content.startswith(b'%PDF')
    text = ''.join(page.extract_text() for page in PdfReader(BytesIO(pdf.content)).pages)
    assert 'Mercedes-Benz' in text and 'P0302' in text
    assert sid not in text and 'session_id' not in text
    if language == 'hy': assert 'հաշվետվություն' in text
    if language == 'ru': assert 'отчёт' in text
    assert client.get(f'/api/v1/sessions/{sid}/report?format=exe').status_code == 422
    assert client.get('/api/v1/sessions/missing/report').status_code == 404


def test_common_simulator_workflow_exposes_records_and_report(client):
    import time
    with client:
        sid = client.post('/api/v1/sessions', json={'make': 'Toyota', 'model': 'Corolla'}).json()['session_id']
        root = f'/api/v1/acquisition/sessions/{sid}'
        assert client.post(root + '/start', json={'adapter': 'simulator', 'poll_interval_ms': 25}).status_code == 200
        assert client.put(root + '/simulator/parameters', json={'rpm': 1800, 'coolant_c': 98, 'speed_kmh': 40, 'throttle_percent': 32}).status_code == 200
        rows = []
        for _ in range(40):
            rows = client.get(root + '/records').json()['records']
            if any(r.get('numeric_value') == 1800 for r in rows): break
            time.sleep(.025)
        assert any(r.get('numeric_value') == 1800 for r in rows)
        assert all(r.get('metadata', {}).get('adapter') == 'simulator' for r in rows)
        assert client.get(f'/api/v1/telemetry/sessions/{sid}/summary').json()['sample_count'] > 0
        assert client.post(f'/api/v1/telemetry/sessions/{sid}/analyze').status_code == 200
        assert client.get(f'/api/v1/network-discovery/sessions/{sid}/map').status_code == 200
        assert client.get(f'/api/v1/sessions/{sid}/report?format=pdf&language=hy').content.startswith(b'%PDF')
        assert client.post(root + '/stop').status_code == 200
