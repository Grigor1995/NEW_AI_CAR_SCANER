from __future__ import annotations
from fastapi import APIRouter, HTTPException
from api.state import sessions
from diagnostic.models import DTC, Evidence, EvidenceSource, EvidenceStatus
from api.state import vci_manager
from vehicle_diagnostic.models import SessionDeviceBindRequest, SessionDeviceBindingResponse, SessionObdSyncResponse
from vehicle_diagnostic.models import DiagnosticConnectRequest, DiagnosticRuntimeStatus, EcuIdentityResponse, UdsDtcResponse
from vehicle_diagnostic.service import VehicleDiagnosticService

router = APIRouter(prefix='/api/v1/vehicle-diagnostic', tags=['vehicle-diagnostic'])
service = VehicleDiagnosticService()


def _is_simulated_diagnostic_runtime(session_id) -> bool:
    """Never mark an active simulator as measured ECU evidence.

    Some unit tests inject a fake identify/read operation without a registered
    runtime; retain their existing mocked non-simulator contract.
    """
    try:
        return service.status(session_id).adapter == "simulator"
    except KeyError:
        return False


@router.post('/sessions/{session_id}/connect', response_model=DiagnosticRuntimeStatus)
async def connect(session_id: str, request: DiagnosticConnectRequest):
    if session_id not in sessions:
        raise HTTPException(404, 'Session not found')
    try:
        return await service.connect(sessions[session_id].session_id, adapter=request.adapter, request_id=request.request_id, response_id=request.response_id)
    except NotImplementedError as exc:
        raise HTTPException(501, str(exc)) from exc


@router.post('/sessions/{session_id}/disconnect', response_model=DiagnosticRuntimeStatus)
async def disconnect(session_id: str):
    if session_id not in sessions:
        raise HTTPException(404, 'Session not found')
    try:
        return await service.disconnect(sessions[session_id].session_id)
    except KeyError as exc:
        raise HTTPException(404, 'Diagnostic connection not found') from exc


@router.get('/sessions/{session_id}/status', response_model=DiagnosticRuntimeStatus)
def status(session_id: str):
    if session_id not in sessions:
        raise HTTPException(404, 'Session not found')
    try:
        return service.status(sessions[session_id].session_id)
    except KeyError as exc:
        raise HTTPException(404, 'Diagnostic connection not found') from exc


@router.get('/sessions/{session_id}/ecu', response_model=EcuIdentityResponse)
async def identify_ecu(session_id: str):
    if session_id not in sessions:
        raise HTTPException(404, 'Session not found')
    try:
        identity = await service.identify_ecu(sessions[session_id].session_id)
        s = sessions[session_id]
        if identity.vin:
            synthetic = _is_simulated_diagnostic_runtime(s.session_id)
            s.evidence.append(Evidence(
                fact=f'{"Simulated" if synthetic else "ECU"} VIN identified as {identity.vin}',
                source=EvidenceSource.SIMULATOR if synthetic else EvidenceSource.ECU_REPORTED,
                status=EvidenceStatus.SIMULATED if synthetic else EvidenceStatus.MEASURED,
                source_ref='SIM:UDS:DID:F190' if synthetic else 'UDS:DID:F190',
                metadata={'simulated': synthetic},
            ))
        return EcuIdentityResponse(session_id=s.session_id, vin=identity.vin, software_version=identity.software_version, hardware_version=identity.hardware_version)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(404, 'Diagnostic connection not found') from exc


@router.post('/sessions/{session_id}/dtcs/read', response_model=UdsDtcResponse)
async def read_dtcs(session_id: str):
    if session_id not in sessions:
        raise HTTPException(404, 'Session not found')
    s = sessions[session_id]
    try:
        records = await service.read_dtcs(s.session_id)
        synthetic = _is_simulated_diagnostic_runtime(s.session_id)
        origin = EvidenceSource.SIMULATOR if synthetic else EvidenceSource.ECU_REPORTED
        evidence_status = EvidenceStatus.SIMULATED if synthetic else EvidenceStatus.MEASURED
        for record in records:
            s.dtcs.append(DTC(code=record.code, source=origin))
            s.evidence.append(Evidence(
                fact=f'{"Simulated" if synthetic else "UDS"} DTC {record.code} status=0x{record.status_byte:02X}',
                source=origin, status=evidence_status,
                source_ref='SIM:UDS:SVC:19:02' if synthetic else 'UDS:SVC:19:02',
                metadata={'raw_dtc': record.raw_dtc, 'status_byte': record.status_byte, 'simulated': synthetic},
            ))
        return UdsDtcResponse(session_id=s.session_id, records=[{'code': r.code, 'raw_dtc': r.raw_dtc, 'status_byte': r.status_byte, 'confirmed': r.confirmed} for r in records])
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(404, 'Diagnostic connection not found') from exc


@router.get('/sessions/{session_id}/trace')
def trace(session_id: str, limit: int = 500):
    if session_id not in sessions:
        raise HTTPException(404, 'Session not found')
    if not 1 <= limit <= 5000:
        raise HTTPException(400, 'limit must be between 1 and 5000')
    try:
        return {'events': [event.to_dict() for event in service.trace(sessions[session_id].session_id, limit)]}
    except KeyError as exc:
        raise HTTPException(404, 'Diagnostic connection not found') from exc


@router.post('/sessions/{session_id}/device/bind', response_model=SessionDeviceBindingResponse)
async def bind_device(session_id: str, request: SessionDeviceBindRequest):
    if session_id not in sessions:
        raise HTTPException(404, 'Session not found')
    s = sessions[session_id]
    try:
        device = vci_manager.status(request.device_id)
    except Exception as exc:
        raise HTTPException(404, f'Device not found: {request.device_id}') from exc
    if device.status.value != 'connected':
        raise HTTPException(409, 'Device must be connected before binding it to a diagnostic session')
    s.connected_device_id = device.device_id
    s.connection_type = device.connection_type
    s.audit_log.append({'event': 'DEVICE_BOUND', 'device_id': device.device_id, 'connection_type': device.connection_type})
    return SessionDeviceBindingResponse(session_id=s.session_id, device_id=device.device_id, connection_type=device.connection_type, connected=True)


@router.get('/sessions/{session_id}/device', response_model=SessionDeviceBindingResponse)
def device_binding(session_id: str):
    if session_id not in sessions:
        raise HTTPException(404, 'Session not found')
    s = sessions[session_id]
    if not s.connected_device_id:
        return SessionDeviceBindingResponse(session_id=s.session_id, connected=False)
    try:
        device = vci_manager.status(s.connected_device_id)
    except Exception:
        return SessionDeviceBindingResponse(session_id=s.session_id, device_id=s.connected_device_id, connection_type=s.connection_type, connected=False)
    return SessionDeviceBindingResponse(session_id=s.session_id, device_id=device.device_id, connection_type=device.connection_type, connected=device.status.value == 'connected')


@router.post('/sessions/{session_id}/obd/sync', response_model=SessionObdSyncResponse)
async def sync_obd_to_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(404, 'Session not found')
    s = sessions[session_id]
    if not s.connected_device_id:
        raise HTTPException(409, 'No VCI device is bound to this diagnostic session')
    try:
        device = vci_manager.status(s.connected_device_id)
        if device.status.value != 'connected':
            raise HTTPException(409, 'Bound VCI device is not connected')
        vin = await vci_manager.read_vin(device.device_id)
        dtcs = await vci_manager.read_dtcs(device.device_id)
        live_data = await vci_manager.read_live_data(device.device_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, f'OBD synchronization failed: {exc}') from exc

    synthetic = device.connection_type.lower() == 'simulator'
    origin = EvidenceSource.SIMULATOR if synthetic else EvidenceSource.ECU_REPORTED
    measurement_origin = EvidenceSource.SIMULATOR if synthetic else EvidenceSource.VEHICLE_MEASURED
    evidence_status = EvidenceStatus.SIMULATED if synthetic else EvidenceStatus.MEASURED

    evidence_added = 0
    if vin and not any(e.source_ref in {'OBD:MODE:09:02', 'SIM:OBD:MODE:09:02'} and vin in e.fact for e in s.evidence):
        s.evidence.append(Evidence(
            fact=f'OBD VIN identified as {vin}',
            source=origin,
            status=evidence_status,
            source_ref='SIM:OBD:MODE:09:02' if synthetic else 'OBD:MODE:09:02',
            metadata={'device_id': device.device_id, 'simulated': synthetic},
        ))
        evidence_added += 1
        if s.vehicle is not None:
            s.vehicle.metadata['vin'] = vin

    for code in dtcs:
        if not any(d.code.upper() == code.upper() and d.source == origin for d in s.dtcs):
            s.dtcs.append(DTC(code=code, source=origin))
            evidence_added += 1
        if not any(e.source_ref in {'OBD:MODE:03', 'SIM:OBD:MODE:03'} and e.metadata.get('dtc') == code for e in s.evidence):
            s.evidence.append(Evidence(
                fact=f'{"Simulated" if synthetic else "OBD"} DTC {code} read from {"simulator" if synthetic else "ECU"}',
                source=origin,
                status=evidence_status,
                source_ref='SIM:OBD:MODE:03' if synthetic else 'OBD:MODE:03',
                metadata={'device_id': device.device_id, 'dtc': code, 'simulated': synthetic},
            ))
            evidence_added += 1

    measurement_added = 0
    if live_data:
        snapshot = {'device_id': device.device_id, 'timestamp': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(), 'values': live_data}
        s.live_data.append(snapshot)
        for name, value in live_data.items():
            if value is None:
                continue
            s.measurements.append({'channel': name, 'value': value, 'source': measurement_origin.value, 'simulated': synthetic, 'device_id': device.device_id})
            measurement_added += 1
        s.evidence.append(Evidence(
            fact='OBD live data snapshot collected: ' + ', '.join(f'{k}={v}' for k, v in live_data.items() if v is not None),
            source=measurement_origin,
            status=evidence_status,
            source_ref='SIM:OBD:MODE:01' if synthetic else 'OBD:MODE:01',
            metadata={'device_id': device.device_id, 'values': live_data, 'simulated': synthetic},
        ))
        evidence_added += 1

    if vin and s.vehicle is None:
        s.audit_log.append({'event': 'VIN_RECEIVED', 'vin': vin, 'device_id': device.device_id})
    s.audit_log.append({'event': 'OBD_SESSION_SYNC', 'device_id': device.device_id, 'dtc_count': len(dtcs), 'live_channels': len(live_data)})
    return SessionObdSyncResponse(session_id=s.session_id, device_id=device.device_id, vin=vin, dtcs=dtcs, live_data=live_data, evidence_added=evidence_added, telemetry_measurements_added=measurement_added)
