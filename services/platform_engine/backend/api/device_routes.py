from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from device.manager import DeviceConnectionError, DeviceDescriptor
from api.state import vci_manager

router = APIRouter(prefix="/api/v1/devices", tags=["vci-devices"])
manager = vci_manager


class WifiProbeRequest(BaseModel):
    host: str
    port: int = Field(default=35000, ge=1, le=65535)
    timeout: float = Field(default=2.0, gt=0, le=10)


class DeviceConnectRequest(BaseModel):
    config: dict = Field(default_factory=dict)


class ScanRequest(BaseModel):
    timeout: float = Field(default=3.0, gt=0, le=30)


def _json(device: DeviceDescriptor) -> dict:
    return {
        "device_id": device.device_id,
        "manufacturer": device.manufacturer,
        "model": device.model,
        "firmware_version": device.firmware_version,
        "protocol": device.protocol,
        "connection_type": device.connection_type,
        "capabilities": device.capabilities.__dict__,
        "status": device.status.value,
        "metadata": device.metadata,
    }


@router.get("")
def list_devices():
    return {"devices": [_json(d) for d in manager.devices.values()]}


@router.post("/scan/{transport}")
async def scan_devices(transport: str, request: ScanRequest = ScanRequest()):
    try:
        devices = await manager.scan(transport, request.timeout)
        return {"transport": transport.lower(), "devices": [_json(d) for d in devices]}
    except DeviceConnectionError as exc:
        raise HTTPException(501, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, f"Device scan failed: {exc}") from exc


@router.post("/wifi/probe")
async def wifi_probe(request: WifiProbeRequest):
    try:
        device = await manager.probe_wifi(request.host, request.port, request.timeout)
        return _json(device)
    except DeviceConnectionError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.post("/simulator")
def add_simulator():
    return _json(manager.add_simulator())


@router.post("/{device_id:path}/connect")
async def connect_device(device_id: str, request: DeviceConnectRequest = DeviceConnectRequest()):
    try:
        return _json(await manager.connect(device_id, request.config))
    except DeviceConnectionError as exc:
        raise HTTPException(409, str(exc)) from exc



@router.post("/{device_id:path}/reconnect")
async def reconnect_device(device_id: str):
    try:
        return _json(await manager.reconnect(device_id))
    except DeviceConnectionError as exc:
        raise HTTPException(409, str(exc)) from exc

@router.post("/{device_id:path}/disconnect")
async def disconnect_device(device_id: str):
    try:
        return _json(await manager.disconnect(device_id))
    except DeviceConnectionError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/{device_id:path}/status")
def device_status(device_id: str):
    try:
        return _json(manager.status(device_id))
    except DeviceConnectionError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/{device_id:path}/obd/vin")
async def read_vin(device_id: str):
    try:
        return {"device_id": device_id, "vin": await manager.read_vin(device_id)}
    except DeviceConnectionError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("/{device_id:path}/obd/dtcs")
async def read_dtcs(device_id: str):
    try:
        return {"device_id": device_id, "dtcs": await manager.read_dtcs(device_id)}
    except DeviceConnectionError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("/{device_id:path}/obd/live-data")
async def read_live_data(device_id: str):
    try:
        return {"device_id": device_id, "values": await manager.read_live_data(device_id)}
    except DeviceConnectionError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("/{device_id:path}/obd/protocol")
async def read_device_obd_protocol(device_id: str):
    """Observe a connected adapter through either supported backend manager.

    A simulator never establishes physical ECU communication. Model/engine
    metadata is never used to infer a measured protocol.
    """
    from vehicle.protocol.elm327_probe import discover_elm_obd_protocol

    if device_id == "simulator-vci":
        return {"device_id": device_id, "simulated": True, "observed": False,
                "protocol_id": None, "confirmed_ecu_communication": False}
    try:
        physical = manager if hasattr(manager, "connected_obd") else manager._physical()
        client = physical.connected_obd(device_id)
        result = await discover_elm_obd_protocol(client.command)
    except Exception as error:
        raise HTTPException(409, str(error)) from error
    return {"device_id": device_id, "simulated": False, **result}


@router.post("/{device_id:path}/diagnostic-discovery")
async def diagnostic_discovery(device_id: str, request: DeviceConnectRequest = DeviceConnectRequest()):
    """Connect, read VIN first, then show measured generic OBD responders."""
    from vehicle.diagnostic_discovery import collect, identify
    try:
        descriptor = manager.status(device_id)
        if descriptor.status.value != "connected":
            descriptor = await manager.connect(device_id, request.config)
        simulated = descriptor.connection_type.lower() == "simulator"
        if simulated:
            return {"vin": None, "vehicle": None, "modules": [], "simulated": True,
                    "identification_status": "simulated", "scope": "generic_obd_responders_only"}
        physical = manager if hasattr(manager, "connected_obd") else manager._physical()
        client = physical.connected_obd(device_id)
        async with client._lock:
            responses = await collect(client._command_unlocked)
        return await identify(responses)
    except Exception as exc:
        raise HTTPException(409, "OBD identification failed; check adapter connection and ignition") from exc
