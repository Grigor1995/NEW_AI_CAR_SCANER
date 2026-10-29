"""Real DB/API authorization tests: no providers, hardware or privilege mocks."""
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, inspect, insert, select, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from api.main import app
from ecosystem import api
from ecosystem.models import Account, AccountRole, AuditEvent, AuthSession, Base, Consent, Invitation, ServiceCenter, Staff, profiles, utcnow
from ecosystem.security import password_hash, password_matches, token_digest
from security.rate_limit import SlidingWindowRateLimiter

P = '/api/v2/ecosystem'
PASSWORD = 'a-good-passphrase-123'


@pytest.fixture
def environment(monkeypatch):
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    with engine.connect() as connection:
        connection.exec_driver_sql('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    monkeypatch.setenv('AI_CAR_ECOSYSTEM_ENABLED', '1')
    monkeypatch.setattr(api.persistence, 'engine', engine)
    monkeypatch.setattr(api.persistence, 'enabled', True)
    monkeypatch.setattr(api, 'registration_limiter', SlidingWindowRateLimiter(1000))
    monkeypatch.setattr(api, 'login_limiter', SlidingWindowRateLimiter(1000))
    with TestClient(app) as client:
        yield client, engine
    engine.dispose()


def register(client, label='owner', **extra):
    payload = dict(email=label+'@example.invalid', full_name=label, password=PASSWORD)
    payload.update(extra)
    response = client.post(P+'/accounts', json=payload)
    assert response.status_code == 201, response.text
    response = response.json()
    login = client.post(P+'/auth/login', json={'email': payload['email'], 'password': payload['password']})
    assert login.status_code == 200, login.text
    return response['id'], {'Authorization': 'Bearer '+login.json()['access_token']}


def vehicle(client, headers):
    result = client.post(P+'/vehicles', headers=headers, json={'name': 'private nickname', 'vehicle': {
        'make': 'Mercedes-Benz', 'model': 'E-Class', 'chassis': 'W211', 'year': 2006,
        'engine': 'M272', 'fuel': ['petrol', 'LPG'], 'metadata': {'private': 'not shared'}}})
    assert result.status_code == 201, result.text
    return result.json()['id']


def workshop(client, headers):
    response = client.post(P+'/service-centers', headers=headers, json={'name':'Test workshop','address':'Manually entered address'})
    assert response.status_code == 201, response.text
    assert response.json()['verified'] is False
    return response.json()['id']


def sharing(environment):
    client, engine = environment
    owner, owner_headers = register(client)
    technician, technician_headers = register(client, 'mechanic')
    profile = vehicle(client, owner_headers)
    center = workshop(client, technician_headers)
    invitation = client.post(P+f'/service-centers/{center}/invitations', headers=technician_headers, json={'account_id':owner}).json()['id']
    return client, engine, owner, owner_headers, technician, technician_headers, profile, center, invitation


def test_accounts_ownership_privileges_and_sensitive_fields(environment):
    client, engine = environment
    account, headers = register(client, language='hy', timezone='Asia/Yerevan', mobile='+37499123456')
    me = client.get(P+'/me', headers=headers)
    assert me.json()['roles'] == ['USER'] and me.json()['modes'] == ['USER'] and me.json()['portals'] == []
    assert me.json()['email_verified'] is False and me.json()['mobile_verified'] is False
    assert 'password' not in me.text and me.headers['cache-control'] == 'no-store'
    assert client.post(P+'/workspace', headers=headers, json={'mode':'USER'}).status_code == 200
    assert client.post(P+'/workspace', headers=headers, json={'mode':'ADMIN'}).status_code == 403
    assert client.post(P+'/workspace', headers=headers, json={'mode':'MARKET'}).status_code == 422
    bad = client.post(P+'/accounts', json={'email':'e@example.invalid','password':PASSWORD,'full_name':'x','roles':['ADMIN']})
    assert bad.status_code == 422 and PASSWORD not in bad.text
    assert client.post(P+'/accounts', json={'email':'OWNER@EXAMPLE.INVALID','password':PASSWORD,'full_name':'duplicate'}).status_code == 409
    profile = vehicle(client, headers)
    _, foreign = register(client, 'foreign')
    assert client.get(P+'/vehicles', headers=foreign).json() == []
    assert client.get(P+'/vehicles', headers=headers).json()[0]['id'] == profile
    with Session(engine) as db:
        stored = db.get(Account, account)
        assert stored.password_hash != PASSWORD and password_matches(PASSWORD, stored.password_hash)
        token = headers['Authorization'].removeprefix('Bearer ')
        assert db.get(AuthSession, token_digest(token)) is not None
        assert db.scalar(select(AuthSession.token_hash)) != token
        events = db.scalars(select(AuditEvent)).all()
        assert 'ACCOUNT_REGISTERED' in [event.action for event in events]
        assert all(PASSWORD not in event.action and token not in event.action for event in events)


@pytest.mark.parametrize('payload', [
    {'email':'not-an-email'}, {'mobile':'099123456'}, {'timezone':'Invented/Zone'}, {'language':'de'},
    {'password':'short'}, {'full_name':'   '},
])
def test_invalid_profile_fields_and_password_redaction(environment, payload):
    client, _ = environment
    body = dict(email='a@example.invalid', full_name='Name', password=PASSWORD)
    body.update(payload)
    response = client.post(P+'/accounts', json=body, headers={'Accept-Language':'hy-AM'})
    assert response.status_code == 422
    assert response.json()['code'] == 'invalid_input'
    assert 'Հարցման' in response.json()['detail']
    assert PASSWORD not in response.text and 'input' not in response.json()


def test_profile_patch_and_workspace_roles_from_database(environment):
    client, engine = environment
    account, headers = register(client)
    update = client.patch(P+'/me', headers=headers, json={'language':'ru','timezone':'Europe/Moscow','mobile':'+79991234567'})
    assert update.json()['language'] == 'ru' and update.json()['mobile_verified'] is False
    assert client.patch(P+'/me', headers=headers, json={'email_verified':True}).status_code == 422
    assert client.patch(P+'/me', headers=headers, json={'language':None}).status_code == 422
    assert client.patch(P+'/me', headers=headers, json={'timezone':'bad'}).status_code == 422
    assert client.patch(P+'/me', headers=headers, json={'mobile':'bad'}).status_code == 422
    assert client.patch(P+'/me', headers=headers, json={'mobile':None}).status_code == 200
    with Session(engine) as db:
        db.add_all([AccountRole(account_id=account,role='ADMIN'), AccountRole(account_id=account,role='MARKET')])
        db.commit()
    me = client.get(P+'/me',headers=headers).json()
    assert me['modes'] == ['USER','ADMIN'] and me['portals'] == ['MARKET']
    assert client.post(P+'/workspace',headers=headers,json={'mode':'ADMIN'}).status_code == 200
    # A new role assignment is not a private-data bypass.
    other, other_headers = register(client,'other')
    profile = vehicle(client, other_headers)
    center = workshop(client, other_headers)
    assert client.get(P+f'/service-centers/{center}/vehicles/{profile}',headers=headers).status_code == 404


def test_login_logout_expiry_inactive_and_generic_errors(environment):
    client, engine = environment
    account, headers = register(client)
    absent = client.post(P+'/auth/login',json={'email':'absent@example.invalid','password':'wrong'})
    wrong = client.post(P+'/auth/login',json={'email':'owner@example.invalid','password':'wrong'})
    assert absent.status_code == wrong.status_code == 401 and absent.json() == wrong.json()
    assert client.get(P+'/me').status_code == 401
    assert client.get(P+'/me',headers={'Authorization':'Bearer invalid'}).status_code == 401
    assert client.get(P+'/me',headers={'Authorization':'Bearer '+'x'*43}).status_code == 401
    assert client.post(P+'/auth/logout',headers=headers).status_code == 204
    assert client.get(P+'/me',headers=headers).status_code == 401
    _, headers = register(client,'expiring')
    with Session(engine) as db:
        session = db.get(AuthSession,token_digest(headers['Authorization'][7:]))
        session.expires_at=utcnow()-timedelta(seconds=1);db.commit()
    assert client.get(P+'/me',headers=headers).status_code == 401
    with Session(engine) as db:
        db.get(Account,account).active=False;db.commit()
    assert client.post(P+'/auth/login',json={'email':'owner@example.invalid','password':PASSWORD}).status_code == 401


def test_unapproved_invitation_never_grants_access_and_revoke_is_immediate(environment):
    client, engine, owner, owner_h, tech, tech_h, profile, center, invitation = sharing(environment)
    path=P+f'/service-centers/{center}/vehicles/{profile}'
    assert client.get(path,headers=tech_h).status_code == 404
    assert client.get(P+'/invitations',headers=tech_h).json() == []
    inbox = client.get(P+'/invitations',headers=owner_h).json()[0]
    assert inbox['id'] == invitation and inbox['center_name'] == 'Test workshop' and inbox['center_verified'] is False
    assert client.get(P+'/service-centers',headers=tech_h).json()[0]['id'] == center
    assert client.get(P+'/service-centers',headers=owner_h).json() == []
    assert client.post(P+f'/invitations/{invitation}/accept',headers=tech_h,json={'profile_id':profile}).status_code == 404
    grant = client.post(P+f'/invitations/{invitation}/accept',headers=owner_h,json={'profile_id':profile}).json()
    assert grant['scopes'] == ['report:read','vehicle:read']
    shared = client.get(path,headers=tech_h)
    assert shared.status_code == 200 and shared.json()['vehicle']['chassis'] == 'W211'
    assert 'private' not in shared.text and 'metadata' not in shared.text and 'email' not in shared.text
    assert client.get(P+'/consents',headers=tech_h).json() == []
    assert client.delete(P+f'/consents/{grant["id"]}',headers=tech_h).status_code == 404
    assert client.delete(P+f'/consents/{grant["id"]}',headers=owner_h).status_code == 204
    assert client.delete(P+f'/consents/{grant["id"]}',headers=owner_h).status_code == 204
    assert client.get(path,headers=tech_h).status_code == 404
    # Fresh explicit approval may restore a previously revoked relationship, without duplicate grants.
    invitation2=client.post(P+f'/service-centers/{center}/invitations',headers=tech_h,json={'account_id':owner}).json()['id']
    assert client.post(P+f'/invitations/{invitation2}/accept',headers=owner_h,json={'profile_id':profile}).status_code == 200
    assert len(client.get(P+'/consents',headers=owner_h).json()) == 1


@pytest.mark.parametrize('condition', ['expired-invite','expired-grant','inactive-staff','inactive-owner','missing-scope','foreign-profile','already-accepted','inactive-center','revoked-customer-role'])
def test_consent_negative_conditions(environment,condition):
    client,engine,owner,owner_h,tech,tech_h,profile,center,invitation=sharing(environment)
    if condition == 'expired-invite':
        with Session(engine) as db:
            db.get(Invitation,invitation).expires_at=utcnow()-timedelta(days=1);db.commit()
        assert client.post(P+f'/invitations/{invitation}/accept',headers=owner_h,json={'profile_id':profile}).status_code==403
        return
    if condition == 'foreign-profile':
        foreign=vehicle(client,tech_h)
        assert client.post(P+f'/invitations/{invitation}/accept',headers=owner_h,json={'profile_id':foreign}).status_code==404
        return
    result=client.post(P+f'/invitations/{invitation}/accept',headers=owner_h,json={'profile_id':profile})
    assert result.status_code==200,result.text
    with Session(engine) as db:
        grant=db.get(Consent,result.json()['id'])
        if condition=='expired-grant':grant.expires_at=utcnow()-timedelta(seconds=1)
        if condition=='inactive-staff':db.get(Staff,(center,tech)).active=False
        if condition=='inactive-owner':db.get(Account,owner).active=False
        if condition=='missing-scope':grant.scopes=['report:read']
        if condition=='inactive-center':db.get(ServiceCenter,center).active=False
        if condition=='revoked-customer-role':db.delete(db.get(AccountRole,(tech,'CUSTOMER')))
        db.commit()
    if condition=='already-accepted':
        assert client.post(P+f'/invitations/{invitation}/accept',headers=owner_h,json={'profile_id':profile}).status_code==409
    else:
        expected = 403 if condition == 'revoked-customer-role' else 404
        assert client.get(P+f'/service-centers/{center}/vehicles/{profile}',headers=tech_h).status_code==expected


def test_cross_center_and_viewer_permissions(environment):
    client,engine,owner,owner_h,tech,tech_h,profile,center,invitation=sharing(environment)
    stranger,stranger_h=register(client,'stranger')
    assert client.post(P+f'/service-centers/{center}/invitations',headers=stranger_h,json={'account_id':owner}).status_code==404
    with Session(engine) as db:
        db.add(Staff(center_id=center,account_id=stranger,role='viewer'));db.add(AccountRole(account_id=stranger,role='CUSTOMER'));db.commit()
    assert client.post(P+f'/service-centers/{center}/invitations',headers=stranger_h,json={'account_id':owner}).status_code==403
    assert client.post(P+f'/service-centers/{center}/invitations',headers=tech_h,json={'account_id':str(uuid4())}).status_code==404
    assert client.post(P+f'/invitations/{invitation}/accept',headers=owner_h,json={'profile_id':profile,'scopes':['vehicle:write']}).status_code==422
    assert client.post(P+f'/invitations/{invitation}/accept',headers=owner_h,json={'profile_id':profile,'expires_in_days':91}).status_code==422
    assert client.get(P+'/me',headers=tech_h).json()['modes']==['USER','CUSTOMER']
    assert client.post(P+f'/invitations/{invitation}/accept',headers=owner_h,json={'profile_id':profile}).status_code==200
    assert client.get(P+f'/service-centers/{center}/vehicles/{profile}',headers=stranger_h).status_code==200


def test_rate_limit_translations_and_legacy_boundary(environment,monkeypatch):
    client,engine=environment
    monkeypatch.setattr(api,'login_limiter',SlidingWindowRateLimiter(1))
    assert client.post(P+'/auth/login',json={'email':'none@example.invalid','password':'wrong'}).status_code==401
    response=client.post(P+'/auth/login',json={'email':'none@example.invalid','password':'wrong'},headers={'Accept-Language':'ru'})
    assert response.status_code==429 and 'Слишком' in response.json()['detail'] and response.headers['retry-after']=='60'
    assert client.get('/api/v1/vehicle-profiles').status_code==403
    assert client.post('/api/v1/sessions',json={}).status_code==403
    assert client.get('/health').status_code==200
    monkeypatch.setenv('AI_CAR_ECOSYSTEM_ENABLED','0')
    assert client.get(P+'/me').status_code==404
    monkeypatch.setattr(api.persistence,'enabled',False)
    assert client.get('/api/v1/platform/roles').status_code==200


def test_missing_database_or_migration_fails_closed(monkeypatch):
    monkeypatch.setenv('AI_CAR_ECOSYSTEM_ENABLED','1')
    monkeypatch.setattr(api.persistence,'enabled',False)
    with TestClient(app) as client:
        assert client.get(P+'/me').status_code==503
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    monkeypatch.setattr(api.persistence,'enabled',True)
    monkeypatch.setattr(api.persistence,'engine',engine)
    with TestClient(app) as client:
        assert client.get(P+'/me').status_code==503
    engine.dispose()


def migration_config(url):
    config=Config(str(Path(__file__).resolve().parents[2]/'backend/alembic.ini'))
    config.set_main_option('sqlalchemy.url',url)
    return config


def test_real_alembic_upgrade_downgrade_preserves_legacy_row(tmp_path,monkeypatch):
    monkeypatch.delenv('DATABASE_URL',raising=False)
    url='sqlite:///'+str(tmp_path/'migration.sqlite')
    engine=create_engine(url)
    profiles.create(engine)
    with engine.begin() as connection:
        connection.execute(insert(profiles).values(id='legacy',payload={'vehicle':{'make':'Toyota','model':'Corolla'}}))
    config=migration_config(url)
    command.upgrade(config,'head');command.upgrade(config,'head')
    assert 'ecosystem_accounts' in inspect(engine).get_table_names()
    with engine.connect() as connection:
        assert connection.execute(select(profiles.c.id)).scalar()=='legacy'
        assert connection.execute(text('SELECT version_num FROM alembic_version')).scalar()=='0001_ecosystem'
    command.downgrade(config,'base')
    assert 'ecosystem_accounts' not in inspect(engine).get_table_names()
    with engine.connect() as connection:assert connection.execute(select(profiles.c.id)).scalar()=='legacy'
    engine.dispose()


def test_migration_creates_profile_contract_when_absent_and_needs_explicit_url(tmp_path,monkeypatch):
    monkeypatch.delenv('DATABASE_URL',raising=False)
    url='sqlite:///'+str(tmp_path/'new.sqlite')
    command.upgrade(migration_config(url),'head')
    engine=create_engine(url)
    assert 'vehicle_profiles' in inspect(engine).get_table_names()
    engine.dispose()
    with pytest.raises(RuntimeError,match='DATABASE_URL'):command.upgrade(migration_config(''),'head')


def test_password_hashes_have_salt_and_fail_closed():
    one=password_hash(PASSWORD);two=password_hash(PASSWORD)
    assert one!=two and password_matches(PASSWORD,one)
    assert not password_matches('wrong',one)
    assert not password_matches(PASSWORD,'not-a-hash')
    assert not password_matches(PASSWORD,'different$salt$hash')
    assert not password_matches(PASSWORD,'scrypt$invalid$invalid')


def test_active_bearer_is_invalidated_when_account_deactivated(environment):
    client,engine=environment
    account,headers=register(client)
    with Session(engine) as db:
        db.get(Account,account).active=False;db.commit()
    assert client.get(P+'/me',headers=headers).status_code==401


def test_database_constraint_failure_is_atomic_and_sanitized(environment):
    client,engine=environment
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TRIGGER reject_account BEFORE INSERT ON ecosystem_accounts BEGIN SELECT RAISE(ABORT,'private database constraint detail'); END")
    response=client.post(P+'/accounts',json={'email':'a@example.invalid','full_name':'Name','password':PASSWORD})
    assert response.status_code==409 and 'private database' not in response.text
    with Session(engine) as db:assert db.scalar(select(Account)) is None


def test_unavailable_database_is_localized_without_connection_details(environment,monkeypatch):
    client,_=environment
    from sqlalchemy.exc import OperationalError
    def unavailable(*args):raise OperationalError('private statement',{},Exception('private db details'))
    monkeypatch.setattr(api,'inspect',unavailable)
    response=client.get(P+'/me',headers={'Accept-Language':'ru-RU'})
    assert response.status_code==503 and 'private' not in response.text and 'базу' in response.json()['detail']


def test_center_phone_validation_and_legacy_validation_contract(environment,monkeypatch):
    client,_=environment
    _,headers=register(client)
    assert client.post(P+'/service-centers',headers=headers,json={'name':'Name','address':'Address','phone':'local-number'}).status_code==422
    assert client.post(P+'/service-centers',headers=headers,json={'name':'Name','address':'Address','phone':'+37499123456'}).status_code==201
    monkeypatch.setenv('AI_CAR_ECOSYSTEM_ENABLED','0')
    response=client.post('/api/v1/vehicle-profiles',json={'vehicle':{'make':None}})
    assert response.status_code==422 and isinstance(response.json()['detail'],list)


def test_registration_limit_and_loopback_are_explicit(environment,monkeypatch):
    client,_=environment
    monkeypatch.setattr(api,'registration_limiter',SlidingWindowRateLimiter(1,window_seconds=600))
    body={'email':'one@example.invalid','full_name':'One','password':PASSWORD}
    assert client.post(P+'/accounts',json=body).status_code==201
    body['email']='two@example.invalid'
    response=client.post(P+'/accounts',json=body)
    assert response.status_code==429 and response.headers['retry-after']=='600'


@pytest.mark.parametrize('encoded', ['scrypt$1073741824$8$3$c2FsdA==$aGFzaA==', 'scrypt$32768$8$3$c2FsdA==$aGFzaA=='])
def test_corrupt_or_unbounded_password_profiles_never_run_kdf(monkeypatch,encoded):
    from ecosystem import security
    def forbidden(*args,**kwargs):raise AssertionError('Invalid stored hash must fail before memory-expensive KDF')
    monkeypatch.setattr(security.hashlib,'scrypt',forbidden)
    assert not security.password_matches(PASSWORD,encoded)


def test_autogeneration_never_proposes_removing_legacy_tables(tmp_path,monkeypatch):
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from ecosystem.migration_policy import include_object
    monkeypatch.delenv('DATABASE_URL',raising=False)
    url='sqlite:///'+str(tmp_path/'generation.sqlite')
    command.upgrade(migration_config(url),'head')
    engine=create_engine(url)
    with engine.begin() as connection:
        connection.exec_driver_sql('CREATE TABLE legacy_customer_records (id INTEGER PRIMARY KEY, private TEXT)')
        connection.exec_driver_sql("INSERT INTO legacy_customer_records VALUES (1,'retained')")
        context=MigrationContext.configure(connection,opts={'include_object':include_object,'compare_type':True})
        assert compare_metadata(context,Base.metadata)==[]
        assert connection.exec_driver_sql('SELECT private FROM legacy_customer_records').scalar()=='retained'
    engine.dispose()


def test_actual_openapi_declares_safe_account_and_auth_contracts():
    document=app.openapi()
    output=document['components']['schemas']['AccountOutput']['properties']
    assert 'password_hash' not in output and 'password' not in output
    assert output['modes']['items']['enum']==['USER','CUSTOMER','ADMIN']
    assert document['paths'][P+'/me']['get']['security']==[{'HTTPBearer':[]}]
    assert document['paths'][P+'/accounts']['post'].get('security',[])==[]
    assert document['paths'][P+'/auth/login']['post']['responses']['200']['content']['application/json']['schema']['$ref'].endswith('/TokenOutput')
    assert document['paths'][P+'/me']['get']['responses']['422']['content']['application/json']['schema']['$ref'].endswith('/ErrorOutput')
