from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from api.state import sessions
from multi_ecu.multibus_runtime import MultiBusDiagnosticRuntime
from multi_ecu.models import EcuNodeRequest, GatewayNodeRequest
from vehicle.network.models import EcuNode, GatewayNode, GatewayRoute, VehicleNetworkTopology
from vehicle.network.multibus import CanBusConfig

router = APIRouter(prefix='/api/v1/multi-bus', tags=['multi-bus'])
_runtime: dict[str, MultiBusDiagnosticRuntime] = {}

class CanBusRequest(BaseModel):
    name: str = Field(min_length=1, max_length=32)
    bitrate: int = Field(default=500_000, ge=10_000, le=10_000_000)
    can_fd: bool = False
    data_bitrate: int | None = Field(default=None, ge=10_000, le=20_000_000)

class GatewayRouteRequest(BaseModel):
    gateway_id: str
    source_bus: str
    target_bus: str
    target_ecu_id: str
    addressing: str = 'NORMAL'

class MultiBusConnectRequest(BaseModel):
    buses: list[CanBusRequest] = Field(min_length=1, max_length=16)
    ecus: list[EcuNodeRequest] = Field(min_length=1, max_length=64)
    gateways: list[GatewayNodeRequest] = Field(default_factory=list, max_length=16)
    routes: list[GatewayRouteRequest] = Field(default_factory=list, max_length=128)

@router.post('/sessions/{session_id}/connect')
async def connect(session_id: str, request: MultiBusConnectRequest):
    if session_id not in sessions:
        raise HTTPException(404, 'Session not found')
    try:
        buses = tuple(CanBusConfig(**b.model_dump()) for b in request.buses)
        ecus = tuple(
            EcuNode(
                ecu_id=e.ecu_id, name=e.name, request_id=e.request_id, response_id=e.response_id,
                bus=e.bus, gateway_id=e.gateway_id, address_type=e.address_type,
                capabilities=frozenset(e.capabilities),
                metadata={
                    'vin': e.vin or f'VIN-{e.ecu_id}',
                    'software_version': e.software_version or f'{e.ecu_id}-SW-1.0',
                    'hardware_version': e.hardware_version or f'{e.ecu_id}-HW-1.0',
                    'dtc_records': e.dtc_records,
                },
            )
            for e in request.ecus
        )
        gateways = tuple(GatewayNode(gateway_id=g.gateway_id, name=g.name, bus=g.bus) for g in request.gateways)
        routes = tuple(GatewayRoute(**r.model_dump()) for r in request.routes)
        topology = VehicleNetworkTopology(ecus=ecus, gateways=gateways, routes=routes)
        runtime = MultiBusDiagnosticRuntime(session_id=sessions[session_id].session_id, topology=topology, buses=buses)
        await runtime.connect(); _runtime[session_id] = runtime
        return runtime.topology_view()
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

@router.get('/sessions/{session_id}/topology')
def topology(session_id: str):
    runtime = _runtime.get(session_id)
    if not runtime: raise HTTPException(404, 'Multi-bus runtime not found')
    return runtime.topology_view()

@router.post('/sessions/{session_id}/identify-all')
async def identify_all(session_id: str):
    runtime = _runtime.get(session_id)
    if not runtime: raise HTTPException(404, 'Multi-bus runtime not found')
    try:
        values = await runtime.identify_all()
        return {'ecus': {k: v.to_dict() for k, v in values.items()}}
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc

@router.post('/sessions/{session_id}/dtcs/read-all')
async def read_dtcs(session_id: str):
    runtime = _runtime.get(session_id)
    if not runtime: raise HTTPException(404, 'Multi-bus runtime not found')
    values = await runtime.read_all_dtcs()
    return {'dtcs_by_ecu': {k: [r.to_dict() for r in v] for k, v in values.items()}}
