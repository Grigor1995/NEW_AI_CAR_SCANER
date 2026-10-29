from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from api.state import sessions
from network_discovery.state import passive_service, active_service
from api.multi_bus_routes import _runtime as multi_bus_runtime
from vehicle.network.active_discovery import ActiveProbePolicy

router = APIRouter(prefix='/api/v1/network-discovery', tags=['network-discovery-active'])

class ActiveProbeRequest(BaseModel):
    candidate_ids: list[str] | None = Field(default=None, max_length=64)
    timeout_ms: int = Field(default=800, ge=100, le=5000)
    max_targets: int = Field(default=16, ge=1, le=64)
    inter_probe_ms: int = Field(default=50, ge=0, le=5000)
    allowed_dids: list[int] = Field(default_factory=lambda: [0xF190, 0xF187, 0xF191], max_length=8)

@router.post('/sessions/{session_id}/active-probe')
async def active_probe(session_id: str, request: ActiveProbeRequest):
    if session_id not in sessions: raise HTTPException(404, 'Session not found')
    runtime = multi_bus_runtime.get(session_id)
    if not runtime: raise HTTPException(409, 'Multi-bus diagnostic runtime is required for active discovery')
    try:
        policy = ActiveProbePolicy(tuple(request.allowed_dids), request.timeout_ms, request.max_targets, request.inter_probe_ms)
        passive = passive_service.analyze(sessions[session_id].session_id)
        results = await active_service.probe_candidates(sessions[session_id].session_id, passive, runtime.raw_buses, runtime.topology, request.candidate_ids, policy)
        return {'session_id': session_id, 'results': [r.to_dict() for r in results], 'correlation': active_service.correlate(sessions[session_id].session_id, passive, runtime.topology)}
    except ValueError as exc: raise HTTPException(400, str(exc)) from exc

@router.get('/sessions/{session_id}/active-map')
def active_map(session_id: str):
    if session_id not in sessions: raise HTTPException(404, 'Session not found')
    runtime = multi_bus_runtime.get(session_id)
    if not runtime: raise HTTPException(409, 'Multi-bus diagnostic runtime is required for active discovery')
    passive = passive_service.analyze(sessions[session_id].session_id)
    return active_service.correlate(sessions[session_id].session_id, passive, runtime.topology)
