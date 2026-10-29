from __future__ import annotations
from pydantic import BaseModel, Field

class EcuNodeRequest(BaseModel):
    ecu_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=100)
    request_id: int = Field(ge=0, le=0x7FF)
    response_id: int = Field(ge=0, le=0x7FF)
    bus: str = 'CAN0'
    gateway_id: str | None = None
    address_type: str = 'NORMAL'
    capabilities: list[str] = Field(default_factory=lambda: ['IDENTITY', 'DTC_READ'])
    vin: str | None = None
    software_version: str | None = None
    hardware_version: str | None = None
    dtc_records: list[tuple[int, int]] = Field(default_factory=list)

class GatewayNodeRequest(BaseModel):
    gateway_id: str
    name: str
    bus: str = 'CAN0'

class MultiEcuConnectRequest(BaseModel):
    ecus: list[EcuNodeRequest] = Field(min_length=1, max_length=64)
    gateways: list[GatewayNodeRequest] = Field(default_factory=list, max_length=16)

class MultiEcuStatusResponse(BaseModel):
    session_id: str
    connected: bool
    ecu_count: int
    gateway_count: int
    trace_events: int
