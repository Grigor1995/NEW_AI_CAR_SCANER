"""Read-only advanced diagnostic interfaces shared by all presentation clients."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from obd.j1939 import decode_diagnostic_frame
from vehicle.doip.client import DoipClient, DoipError
from vehicle.uds.read_only import read_request

router = APIRouter(prefix='/api/v1/obd', tags=['OBD'])


class DoipRead(BaseModel):
    host: str = Field(min_length=1, max_length=253)
    port: int = Field(default=13400, ge=1, le=65535)
    source_address: int = Field(ge=1, le=65535)
    target_address: int = Field(ge=1, le=65535)
    did: int | None = Field(default=None, ge=0, le=65535)
    dtc_status_mask: int | None = Field(default=None, ge=0, le=255)
    timeout: float = Field(default=5, gt=0, le=30)


class J1939Frame(BaseModel):
    arbitration_id: int = Field(ge=0, le=0x1FFFFFFF)
    data: str = Field(min_length=4, max_length=24)


@router.post('/uds/doip/read')
async def read_doip(request: DoipRead):
    try:
        command = read_request(request.did, request.dtc_status_mask)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    client = DoipClient(request.host, source_address=request.source_address,
                        target_address=request.target_address, port=request.port, timeout=request.timeout)
    try:
        raw = await client.read(command)
    except DoipError as error:
        raise HTTPException(502, str(error)) from error
    return {'response_hex': raw.hex().upper(), 'service': raw[0],
            'data_hex': raw[3 if request.did is not None else 2:].hex().upper(),
            'source': 'server_local_doip', 'read_only': True,
            'ecu_address': request.target_address, 'scope': 'Requested ECU/service only',
            'hardware_verified': False}


@router.post('/j1939/decode')
def decode_j1939(request: J1939Frame):
    try:
        return decode_diagnostic_frame(request.arbitration_id, bytes.fromhex(request.data))
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


class J1939Capture(BaseModel):
    frames: list[J1939Frame] = Field(min_length=2, max_length=256)


class J1708Packet(BaseModel):
    data: str = Field(min_length=8, max_length=64)


@router.post('/j1939/decode-bam')
def decode_j1939_bam(request: J1939Capture):
    from obd.j1939 import decode_bam_capture
    try:
        return decode_bam_capture([(frame.arbitration_id, bytes.fromhex(frame.data)) for frame in request.frames])
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


@router.post('/j1708/decode')
def decode_j1708(request: J1708Packet):
    from obd.j1587 import decode_packet
    try:
        return decode_packet(bytes.fromhex(request.data))
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


class ElmUdsRead(BaseModel):
    device_id: str = Field(min_length=1, max_length=256)
    request_id: int = Field(ge=0, le=0x1FFFFFFF)
    response_id: int = Field(ge=0, le=0x1FFFFFFF)
    did: int | None = Field(default=None, ge=0, le=65535)
    dtc_status_mask: int | None = Field(default=None, ge=0, le=255)


@router.post('/uds/elm/read')
async def read_elm_uds(request: ElmUdsRead):
    from api.state import vci_manager
    try:
        command = read_request(request.did, request.dtc_status_mask)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    try:
        if vci_manager.status(request.device_id).connection_type.lower() == 'simulator':
            raise ValueError('This endpoint requires a physical CAN adapter')
        physical = vci_manager if hasattr(vci_manager, 'connected_obd') else vci_manager._physical()
        client = physical.connected_obd(request.device_id)
        raw = await client.read_uds(request.request_id, request.response_id, command)
    except Exception as error:
        raise HTTPException(409, str(error)) from error
    return {'response_hex': raw.hex().upper(), 'source': 'server_local_elm_can',
            'read_only': True, 'hardware_verified': False,
            'scope': 'Explicitly addressed ECU/read service only'}
