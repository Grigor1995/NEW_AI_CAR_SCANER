from __future__ import annotations
from fastapi import APIRouter, HTTPException
from api.state import sessions
from acquisition.models import AcquisitionStartRequest, AcquisitionStatus, SimulatorParameters
from acquisition.service import AcquisitionApiService
from telemetry.channels import channel_name

router=APIRouter(prefix='/api/v1/acquisition',tags=['vehicle-acquisition'])
service=AcquisitionApiService()

@router.post('/sessions/{session_id}/start',response_model=AcquisitionStatus)
async def start_acquisition(session_id: str, request: AcquisitionStartRequest):
    if session_id not in sessions: raise HTTPException(404,'Session not found')
    if request.adapter != 'simulator':
        from api.state import vci_manager
        device_id = request.device_id or sessions[session_id].connected_device_id
        if not device_id:
            raise HTTPException(409, 'Bind a connected server-local device or supply device_id')
        try:
            device = vci_manager.status(device_id)
            kind = device.connection_type.lower().replace('-', '')
            if request.adapter == 'bound':
                if kind not in {'wifi', 'usb', 'ble'}:
                    raise ValueError('Bound acquisition requires a physical server-local adapter')
                request = request.model_copy(update={'adapter': kind})
            if device.status.value != 'connected' or kind != request.adapter:
                raise ValueError('Connected device transport does not match requested adapter')
            return await service.start_device(sessions[session_id].session_id, request, vci_manager, device_id)
        except Exception as error:
            raise HTTPException(409, str(error)) from error
    try: return await service.start_simulator(sessions[session_id].session_id,request)
    except ValueError as exc: raise HTTPException(409, str(exc)) from exc
    except Exception as exc: raise HTTPException(502,f'Acquisition start failed: {exc}') from exc

@router.post('/sessions/{session_id}/stop',response_model=AcquisitionStatus)
async def stop_acquisition(session_id: str):
    if session_id not in sessions: raise HTTPException(404,'Session not found')
    try: return await service.stop(sessions[session_id].session_id)
    except KeyError: raise HTTPException(409,'Acquisition is not running')

@router.get('/sessions/{session_id}/status',response_model=AcquisitionStatus)
def acquisition_status(session_id: str):
    if session_id not in sessions: raise HTTPException(404,'Session not found')
    try: return service.status(sessions[session_id].session_id)
    except KeyError: raise HTTPException(404,'Acquisition not started')

@router.get('/sessions/{session_id}/records')
def acquisition_records(session_id: str, limit: int = 100):
    if session_id not in sessions: raise HTTPException(404,'Session not found')
    if limit < 1 or limit > 1000: raise HTTPException(400,'limit must be between 1 and 1000')
    try:
        return {'records':[r.__dict__ | {'display_name':channel_name(r.channel),'id':str(r.id),'session_id':str(r.session_id),'source_type':r.source_type.value,'raw':r.raw.hex() if r.raw else None} for r in service.snapshot(sessions[session_id].session_id,limit)]}
    except KeyError: raise HTTPException(404,'Acquisition not started')


@router.put('/sessions/{session_id}/simulator/parameters')
def simulator_parameters(session_id: str, parameters: SimulatorParameters):
    if session_id not in sessions:
        raise HTTPException(404, 'Session not found')
    try:
        return service.set_simulator_parameters(sessions[session_id].session_id, parameters)
    except (KeyError, ValueError) as exc:
        raise HTTPException(409, str(exc)) from exc
