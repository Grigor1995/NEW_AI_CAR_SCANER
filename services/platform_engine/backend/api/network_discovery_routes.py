from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.state import sessions
from vehicle.can.models import CanFrame
from network_discovery.state import passive_service

router = APIRouter(prefix="/api/v1/network-discovery", tags=["network-discovery"])
service = passive_service


class DiscoveredFrameRequest(BaseModel):
    arbitration_id: int = Field(ge=0, le=0x1FFFFFFF)
    data_hex: str = Field(default="", max_length=128)
    timestamp_ns: int | None = Field(default=None, ge=0)
    is_extended: bool = False
    is_fd: bool = False


class DiscoveryBatchRequest(BaseModel):
    bus: str = Field(default="CAN0", min_length=1, max_length=32)
    frames: list[DiscoveredFrameRequest] = Field(min_length=1, max_length=10_000)


def _frame(item: DiscoveredFrameRequest) -> CanFrame:
    try:
        data = bytes.fromhex(item.data_hex)
    except ValueError as exc:
        raise HTTPException(422, "data_hex must contain valid hexadecimal bytes") from exc
    return CanFrame(
        arbitration_id=item.arbitration_id,
        data=data,
        timestamp_ns=item.timestamp_ns,
        is_extended=item.is_extended,
        is_fd=item.is_fd,
    )


@router.post("/sessions/{session_id}/frames")
def ingest_frames(session_id: str, request: DiscoveryBatchRequest):
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    count = service.ingest_frames(
        sessions[session_id].session_id,
        bus=request.bus,
        frames=[_frame(item) for item in request.frames],
    )
    return {"accepted": count, "observation_count": service.observation_count(sessions[session_id].session_id)}


@router.get("/sessions/{session_id}/map")
def discover_map(session_id: str):
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    return service.analyze(sessions[session_id].session_id).to_dict()


@router.delete("/sessions/{session_id}/frames")
def reset_discovery(session_id: str):
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    service.reset(sessions[session_id].session_id)
    return {"status": "reset"}
