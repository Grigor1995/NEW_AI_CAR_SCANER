from __future__ import annotations
from pydantic import BaseModel, Field
from uuid import UUID


class DiagnosticConnectRequest(BaseModel):
    adapter: str = Field(default='simulator', pattern='^(simulator|ble|wifi|usb|j2534)$')
    request_id: int = Field(default=0x7E0, ge=0, le=0x1FFFFFFF)
    response_id: int = Field(default=0x7E8, ge=0, le=0x1FFFFFFF)


class DiagnosticRuntimeStatus(BaseModel):
    session_id: UUID
    connected: bool
    adapter: str | None = None
    can: bool = False
    isotp: bool = False
    uds: bool = False
    dtc_read: bool = False
    dtc_clear: bool = False
    trace_events: int = 0


class EcuIdentityResponse(BaseModel):
    session_id: UUID
    vin: str | None = None
    software_version: str | None = None
    hardware_version: str | None = None


class UdsDtcResponse(BaseModel):
    session_id: UUID
    records: list[dict]


class SessionDeviceBindRequest(BaseModel):
    device_id: str


class SessionDeviceBindingResponse(BaseModel):
    session_id: UUID
    device_id: str | None = None
    connection_type: str | None = None
    connected: bool


class SessionObdSyncResponse(BaseModel):
    session_id: UUID
    device_id: str
    vin: str | None = None
    dtcs: list[str] = Field(default_factory=list)
    live_data: dict = Field(default_factory=dict)
    evidence_added: int = 0
    telemetry_measurements_added: int = 0
