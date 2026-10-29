from __future__ import annotations
from fastapi import APIRouter, HTTPException
from api.state import sessions
from multi_ecu.models import MultiEcuConnectRequest, MultiEcuStatusResponse
from multi_ecu.service import MultiEcuDiagnosticService
from diagnostic.models import DTC, Evidence, EvidenceSource, EvidenceStatus

router = APIRouter(prefix='/api/v1/multi-ecu', tags=['multi-ecu'])
service = MultiEcuDiagnosticService()

@router.post('/sessions/{session_id}/connect', response_model=MultiEcuStatusResponse)
async def connect(session_id: str, request: MultiEcuConnectRequest):
    if session_id not in sessions:
        raise HTTPException(404, 'Session not found')
    try:
        runtime = await service.connect(sessions[session_id].session_id, request)
        return _status(runtime)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

@router.post('/sessions/{session_id}/disconnect', response_model=MultiEcuStatusResponse)
async def disconnect(session_id: str):
    if session_id not in sessions:
        raise HTTPException(404, 'Session not found')
    try:
        runtime = await service.disconnect(sessions[session_id].session_id)
        return _status(runtime)
    except KeyError as exc:
        raise HTTPException(404, 'Multi-ECU runtime not found') from exc

@router.get('/sessions/{session_id}/topology')
def topology(session_id: str):
    if session_id not in sessions:
        raise HTTPException(404, 'Session not found')
    try:
        return service.require(sessions[session_id].session_id).discover().to_dict()
    except KeyError as exc:
        raise HTTPException(404, 'Multi-ECU runtime not found') from exc

@router.post('/sessions/{session_id}/identify-all')
async def identify_all(session_id: str):
    if session_id not in sessions:
        raise HTTPException(404, 'Session not found')
    try:
        runtime = service.require(sessions[session_id].session_id)
        identities = await runtime.identify_all()
        return {'session_id': session_id, 'ecus': {k: v.to_dict() for k, v in identities.items()}}
    except (KeyError, RuntimeError) as exc:
        raise HTTPException(409, str(exc)) from exc

@router.post('/sessions/{session_id}/dtcs/read-all')
async def read_all_dtcs(session_id: str):
    if session_id not in sessions:
        raise HTTPException(404, 'Session not found')
    try:
        runtime = service.require(sessions[session_id].session_id)
        dtcs = await runtime.read_all_dtcs()
        s = sessions[session_id]
        for ecu_id, records in dtcs.items():
            for r in records:
                s.dtcs.append(DTC(code=r.code, source=EvidenceSource.ECU_REPORTED))
                s.evidence.append(Evidence(
                    fact=f'ECU {ecu_id} UDS DTC {r.code} status=0x{r.status_byte:02X}',
                    source=EvidenceSource.ECU_REPORTED, status=EvidenceStatus.MEASURED,
                    source_ref=f'UDS:{ecu_id}:SVC:19:02',
                    metadata={'ecu_id': ecu_id, 'raw_dtc': r.raw_dtc, 'status_byte': r.status_byte},
                ))
        correlations = runtime.correlate_dtcs(dtcs)
        return {
            'session_id': session_id,
            'dtcs_by_ecu': {k: [
                {'code': r.code, 'raw_dtc': r.raw_dtc, 'status_byte': r.status_byte, 'confirmed': r.confirmed}
                for r in v] for k, v in dtcs.items()},
            'correlations': correlations,
        }
    except (KeyError, RuntimeError) as exc:
        raise HTTPException(409, str(exc)) from exc

@router.get('/sessions/{session_id}/trace')
def trace(session_id: str, limit: int = 500):
    if session_id not in sessions:
        raise HTTPException(404, 'Session not found')
    if not 1 <= limit <= 5000:
        raise HTTPException(400, 'limit must be between 1 and 5000')
    try:
        return {'events': [e.to_dict() for e in service.require(sessions[session_id].session_id).trace_snapshot(limit)]}
    except KeyError as exc:
        raise HTTPException(404, 'Multi-ECU runtime not found') from exc

def _status(runtime) -> MultiEcuStatusResponse:
    return MultiEcuStatusResponse(
        session_id=str(runtime.session_id), connected=runtime.connected,
        ecu_count=len(runtime.topology.ecus), gateway_count=len(runtime.topology.gateways),
        trace_events=len(runtime.trace_snapshot()),
    )
