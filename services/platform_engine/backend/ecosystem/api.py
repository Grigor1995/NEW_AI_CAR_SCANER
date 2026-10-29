"""Feature-gated durable identity and consent HTTP boundary; no new diagnostics."""
from dataclasses import dataclass
from datetime import timedelta
import os
from threading import RLock
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from diagnostic.session_persistence import persistence
from security.rate_limit import SlidingWindowRateLimiter
from . import schemas, service
from .errors import DomainError, error_body
from .models import Account, AccountRole, AuditEvent, AuthSession, Consent, Invitation, ServiceCenter, Staff, utcnow
from .security import new_token, password_hash, password_matches, token_digest

PREFIX = '/api/v2/ecosystem'
bearer = HTTPBearer(auto_error=False, description='Opaque revocable session token from the ecosystem login API')
registration_limiter = SlidingWindowRateLimiter(limit=10, window_seconds=600)
login_limiter = SlidingWindowRateLimiter(limit=10, window_seconds=60)
_limiter_lock = RLock()
DUMMY_HASH = 'scrypt$32768$8$3$L0xjcqAeO9vpant6xeTf3A==$61CFYQ/Qe8CgZI1XnXhv82ljN1gzYmvL89g8Ai0RhJE='


def enabled():
    return os.environ.get('AI_CAR_ECOSYSTEM_ENABLED', '0').lower() in {'1', 'true', 'yes'}


def require_enabled():
    if not enabled():
        raise DomainError('disabled', 404)


router = APIRouter(prefix=PREFIX, tags=['ecosystem-foundation'], dependencies=[Depends(require_enabled)],
                   responses={status: {'model': schemas.ErrorOutput} for status in (401, 403, 404, 409, 422, 429, 503)})


def get_db():
    engine = persistence.engine if persistence.enabled else None
    if engine is None:
        raise DomainError('database_unavailable', 503)
    try:
        if not inspect(engine).has_table('ecosystem_auth_sessions'):
            raise DomainError('database_unavailable', 503)
        with Session(engine, expire_on_commit=False) as db:
            if engine.dialect.name == 'sqlite':
                db.connection().exec_driver_sql('PRAGMA foreign_keys=ON')
            try:
                yield db
            except Exception:
                db.rollback()
                raise
    except IntegrityError as error:
        raise DomainError('conflict', 409) from error
    except SQLAlchemyError as error:
        raise DomainError('database_unavailable', 503) from error


def throttle(limiter, request):
    # Single-process throttle. A distributed production limiter remains a release gate.
    key = request.client.host if request.client else 'unknown'
    with _limiter_lock:
        if not limiter.allow(key):
            error = DomainError('rate_limited', 429)
            error.retry_after = int(limiter.window)
            raise error


@dataclass
class Authenticated:
    account: Account
    session: AuthSession


def current(db=Depends(get_db), credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if credentials is None or len(credentials.credentials) != 43:
        raise DomainError('unauthorized', 401)
    session = db.get(AuthSession, token_digest(credentials.credentials))
    if session is None or session.revoked or service.as_utc(session.expires_at) <= utcnow():
        raise DomainError('unauthorized', 401)
    account = db.get(Account, session.account_id)
    if account is None or not account.active:
        raise DomainError('unauthorized', 401)
    return Authenticated(account, session)


@router.post('/accounts', status_code=201, response_model=schemas.AccountOutput)
def register(data: schemas.Register, request: Request, db=Depends(get_db)):
    throttle(registration_limiter, request)
    if db.scalar(select(Account.id).where(Account.email == data.email)):
        raise DomainError('conflict', 409)
    fields = data.model_dump(exclude={'password'})
    account = Account(**fields, password_hash=password_hash(data.password.get_secret_value()))
    db.add(account)
    db.flush()
    db.add(AccountRole(account_id=account.id, role='USER'))
    service.record(db, account, 'ACCOUNT_REGISTERED', account.id)
    db.commit()
    return service.account_view(db, account)


@router.post('/auth/login', response_model=schemas.TokenOutput)
def login(data: schemas.Login, request: Request, response: Response, db=Depends(get_db)):
    throttle(login_limiter, request)
    account = db.scalar(select(Account).where(Account.email == data.email.casefold()))
    matched = password_matches(data.password.get_secret_value(), account.password_hash if account else DUMMY_HASH)
    if not matched or account is None or not account.active:
        db.add(AuditEvent(action='LOGIN_DENIED', target_id='authentication'))
        db.commit()
        raise DomainError('invalid_credentials', 401)
    token, digest = new_token()
    ttl = max(60, min(86400, int(os.environ.get('AI_CAR_SESSION_TTL_SECONDS', '3600'))))
    db.add(AuthSession(token_hash=digest, account_id=account.id, expires_at=utcnow() + timedelta(seconds=ttl)))
    service.record(db, account, 'LOGIN_SUCCEEDED', account.id)
    db.commit()
    response.headers['Pragma'] = 'no-cache'
    return {'access_token': token, 'token_type': 'bearer', 'expires_in': ttl}


@router.post('/auth/logout', status_code=204)
def logout(auth=Depends(current), db=Depends(get_db)):
    auth.session.revoked = True
    service.record(db, auth.account, 'LOGOUT', auth.account.id)
    db.commit()
    return Response(status_code=204)


@router.get('/me', response_model=schemas.AccountOutput)
def me(auth=Depends(current), db=Depends(get_db)):
    return service.account_view(db, auth.account)


@router.patch('/me', response_model=schemas.AccountOutput)
def update_me(data: schemas.ProfilePatch, auth=Depends(current), db=Depends(get_db)):
    for field, value in data.model_dump(exclude_unset=True).items():
        if field == 'mobile' and value != auth.account.mobile:
            auth.account.mobile_verified = False
        setattr(auth.account, field, value)
    service.record(db, auth.account, 'PROFILE_UPDATED', auth.account.id)
    db.commit()
    return service.account_view(db, auth.account)


@router.post('/workspace', response_model=schemas.Workspace)
def workspace(data: schemas.Workspace, auth=Depends(current), db=Depends(get_db)):
    if data.mode not in service.current_roles(db, auth.account):
        raise DomainError('forbidden')
    return {'mode': data.mode}


@router.get('/vehicles', response_model=list[schemas.OwnedVehicleOutput])
def vehicles(auth=Depends(current), db=Depends(get_db)):
    return service.owned_vehicles(db, auth.account)


@router.post('/vehicles', status_code=201, response_model=schemas.OwnedVehicleOutput)
def add_vehicle(data: schemas.VehicleInput, auth=Depends(current), db=Depends(get_db)):
    return service.add_vehicle(db, auth.account, data)


@router.get('/service-centers', response_model=list[schemas.CenterOutput])
def centers(auth=Depends(current), db=Depends(get_db)):
    if 'CUSTOMER' not in service.current_roles(db, auth.account):
        return []
    rows = db.scalars(select(ServiceCenter).join(Staff, Staff.center_id == ServiceCenter.id)
                      .where(Staff.account_id == auth.account.id, Staff.active.is_(True), ServiceCenter.active.is_(True)))
    return [{'id': row.id, 'name': row.name, 'verified': row.verified} for row in rows]


@router.post('/service-centers', status_code=201, response_model=schemas.CenterOutput)
def create_center(data: schemas.CenterInput, auth=Depends(current), db=Depends(get_db)):
    return service.create_center(db, auth.account, data)


@router.post('/service-centers/{center_id}/invitations', status_code=201, response_model=schemas.InviteOutput)
def invite(center_id: UUID, data: schemas.InviteInput, auth=Depends(current), db=Depends(get_db)):
    return service.invite(db, auth.account, str(center_id), str(data.account_id))


@router.get('/invitations', response_model=list[schemas.InboxInvitation])
def invitations(auth=Depends(current), db=Depends(get_db)):
    rows = db.execute(select(Invitation, ServiceCenter).join(ServiceCenter, Invitation.center_id == ServiceCenter.id)
                      .where(Invitation.account_id == auth.account.id))
    return [{'id': row.id, 'center_id': row.center_id, 'center_name': center.name, 'center_verified': center.verified,
             'expires_at': row.expires_at, 'accepted': row.accepted_at is not None} for row, center in rows]


@router.post('/invitations/{invitation_id}/accept', response_model=schemas.ConsentOutput)
def accept(invitation_id: UUID, data: schemas.AcceptInput, auth=Depends(current), db=Depends(get_db)):
    return service.accept(db, auth.account, str(invitation_id), data)


@router.get('/consents', response_model=list[schemas.ConsentOutput])
def consents(auth=Depends(current), db=Depends(get_db)):
    rows = db.execute(select(Consent, ServiceCenter).join(ServiceCenter, Consent.center_id == ServiceCenter.id)
                      .where(Consent.owner_id == auth.account.id))
    return [service.consent_view(row, center) for row, center in rows]


@router.delete('/consents/{consent_id}', status_code=204)
def revoke(consent_id: UUID, auth=Depends(current), db=Depends(get_db)):
    grant = db.get(Consent, str(consent_id))
    if grant is None or grant.owner_id != auth.account.id:
        raise DomainError('not_found', 404)
    if not grant.revoked:
        grant.revoked = True
        service.record(db, auth.account, 'CONSENT_REVOKED', grant.id)
        db.commit()
    return Response(status_code=204)


@router.get('/service-centers/{center_id}/vehicles/{profile_id}', response_model=schemas.VehicleOutput,
            response_model_exclude={'vehicle': {'metadata'}})
def shared_vehicle(center_id: UUID, profile_id: UUID, auth=Depends(current), db=Depends(get_db)):
    return service.read_shared_vehicle(db, auth.account, str(center_id), str(profile_id))


def install(app):
    async def domain_error(request, error):
        headers = {'Cache-Control': 'no-store'}
        if error.status == 401: headers['WWW-Authenticate'] = 'Bearer'
        if error.status == 429: headers['Retry-After'] = str(getattr(error, 'retry_after', 60))
        return JSONResponse(error_body(error.code, request.headers.get('Accept-Language', 'en')),
                            status_code=error.status, headers=headers)

    async def invalid_request(request, error):
        if not request.url.path.startswith(PREFIX + '/'):
            return await request_validation_exception_handler(request, error)
        # Do not serialize Pydantic's raw `input` field, which can contain a password.
        body = error_body('invalid_input', request.headers.get('Accept-Language', 'en'))
        body['fields'] = [list(item['loc']) for item in error.errors()]
        return JSONResponse(body, status_code=422, headers={'Cache-Control': 'no-store'})

    @app.middleware('http')
    async def boundary(request, call_next):
        path = request.url.path
        if enabled() and path.startswith('/api/') and not (path == PREFIX or path.startswith(PREFIX + '/')):
            return await domain_error(request, DomainError('legacy_blocked', 403))
        response = await call_next(request)
        if path.startswith(PREFIX): response.headers['Cache-Control'] = 'no-store'
        return response

    app.add_exception_handler(DomainError, domain_error)
    app.add_exception_handler(RequestValidationError, invalid_request)
    app.include_router(router)
