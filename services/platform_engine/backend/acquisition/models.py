from __future__ import annotations
from uuid import UUID
from pydantic import BaseModel, Field

class AcquisitionStartRequest(BaseModel):
    adapter: str = Field(default='simulator', pattern='^(simulator|ble|wifi|usb|bound)$')
    device_id: str | None = Field(default=None, max_length=256)
    poll_interval_ms: int = Field(default=100, ge=20, le=10_000)
    pids: list[int] = Field(default_factory=lambda: [0x0C,0x05,0x0D,0x11], max_length=32)

class AcquisitionStatus(BaseModel):
    session_id: UUID
    state: str
    adapter: str
    stats: dict[str, int]
    buffered_records: int
    offline_queue_items: int = 0


class SimulatorParameters(BaseModel):
    """Canonical SI values; updates never affect physical adapters."""
    rpm: float = Field(default=750, ge=0, le=16383, allow_inf_nan=False)
    coolant_c: float = Field(default=90, ge=-40, le=215, allow_inf_nan=False)
    speed_kmh: float = Field(default=40, ge=0, le=255, allow_inf_nan=False)
    throttle_percent: float = Field(default=32, ge=0, le=100, allow_inf_nan=False)
