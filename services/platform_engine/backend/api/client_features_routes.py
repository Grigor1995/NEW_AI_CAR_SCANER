"""Shared native-client profiles and privacy-preserving reports."""
from threading import RLock
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import JSON, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from api.state import sessions
from diagnostic.models import Vehicle
from diagnostic.session_persistence import SessionStateBase, persistence

router = APIRouter(prefix='/api/v1', tags=['native-client-features'])


class VehicleProfileRow(SessionStateBase):
    __tablename__ = 'vehicle_profiles'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)


class ProfileRequest(BaseModel):
    name: str = Field(default='', max_length=200)
    vehicle: Vehicle


_profile_cache: dict[str, dict] = {}
_lock = RLock()


def _engine():
    engine = persistence.engine if persistence.enabled else None
    if engine is not None:
        VehicleProfileRow.__table__.create(engine, checkfirst=True)
    return engine


@router.get('/vehicle-profiles')
def list_profiles():
    with _lock:
        engine = _engine()
        if engine is None:
            return list(_profile_cache.values())
        with Session(engine) as db:
            return [dict(row.payload, id=row.id) for row in db.scalars(select(VehicleProfileRow))]


def _save_profile(profile_id: str, request: ProfileRequest, create: bool):
    payload = {'id': profile_id, 'name': request.name.strip(), 'vehicle': request.vehicle.model_dump(mode='json')}
    with _lock:
        engine = _engine()
        if engine is None:
            if not create and profile_id not in _profile_cache:
                raise HTTPException(404, 'Vehicle profile not found')
            _profile_cache[profile_id] = payload
        else:
            with Session(engine) as db:
                row = db.get(VehicleProfileRow, profile_id)
                if row is None:
                    if not create:
                        raise HTTPException(404, 'Vehicle profile not found')
                    row = VehicleProfileRow(id=profile_id, payload=payload)
                    db.add(row)
                else:
                    row.payload = payload
                db.commit()
    return payload


@router.post('/vehicle-profiles', status_code=201)
def create_profile(request: ProfileRequest):
    return _save_profile(str(uuid4()), request, True)


@router.put('/vehicle-profiles/{profile_id}')
def update_profile(profile_id: str, request: ProfileRequest):
    return _save_profile(profile_id, request, False)


@router.delete('/vehicle-profiles/{profile_id}')
def delete_profile(profile_id: str):
    with _lock:
        engine = _engine()
        if engine is None:
            if _profile_cache.pop(profile_id, None) is None:
                raise HTTPException(404, 'Vehicle profile not found')
        else:
            with Session(engine) as db:
                row = db.get(VehicleProfileRow, profile_id)
                if row is None:
                    raise HTTPException(404, 'Vehicle profile not found')
                db.delete(row)
                db.commit()
    return {'deleted': True}


def private_report(value):
    if isinstance(value, dict):
        return {key: private_report(item) for key, item in value.items() if key not in {'session_id', 'connected_device_id'}}
    if isinstance(value, list):
        return [private_report(item) for item in value]
    return value


@router.get('/sessions/{session_id}/report')
def report(session_id: str, format: str = Query('json', pattern='^(json|pdf)$'), language: str = 'en'):
    if session_id not in sessions:
        raise HTTPException(404, 'Session not found')
    from diagnostic.localization import localize_session_analysis
    session = localize_session_analysis(sessions[session_id], language=language)
    if hasattr(session, 'model_dump'):
        session = session.model_dump(mode='json')
    # Strip internal identifier values too, including user-independent audit text.
    data = private_report(session)
    def redact(value):
        if isinstance(value, str): return value.replace(session_id, '[internal]')
        if isinstance(value, list): return [redact(v) for v in value]
        if isinstance(value, dict): return {k: redact(v) for k, v in value.items()}
        return value
    data = redact(data)
    if format == 'json':
        return data
    from shared.reporting import render_diagnostic_pdf
    return Response(render_diagnostic_pdf(data, language), media_type='application/pdf', headers={'Content-Disposition': 'attachment; filename="diagnostic-report.pdf"'})
