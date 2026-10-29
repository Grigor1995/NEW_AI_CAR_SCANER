from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class SampleQuality(str, Enum):
    GOOD = "GOOD"
    SUSPECT = "SUSPECT"
    INVALID = "INVALID"


class TelemetrySample(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    timestamp_ms: int = Field(ge=0)
    pid: str = Field(min_length=1, max_length=128)
    value: float
    unit: str | None = None
    source: str = "OBD"
    sequence: int | None = Field(default=None, ge=0)
    quality: SampleQuality = SampleQuality.GOOD
    metadata: dict = Field(default_factory=dict)


class SignalStats(BaseModel):
    display_name: str | None = None
    session_id: UUID
    pid: str
    count: int
    start_ms: int | None = None
    end_ms: int | None = None
    duration_ms: int = 0
    min_value: float | None = None
    max_value: float | None = None
    mean: float | None = None
    stddev: float | None = None
    slope_per_second: float | None = None
    mean_abs_delta: float | None = None
    max_abs_delta: float | None = None
    sample_rate_hz: float | None = None
    anomaly_count: int = 0
    event_count: int = 0


class SignalEventType(str, Enum):
    STEP_CHANGE = "STEP_CHANGE"
    RATE_SPIKE = "RATE_SPIKE"
    OUT_OF_RANGE = "OUT_OF_RANGE"
    STALL = "STALL"
    OSCILLATION = "OSCILLATION"


class SignalEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    pid: str
    event_type: SignalEventType
    start_ms: int
    end_ms: int
    severity: str = "INFO"
    message: str
    evidence_fact: str
    metrics: dict = Field(default_factory=dict)


class TelemetrySummary(BaseModel):
    session_id: UUID
    sample_count: int
    signal_count: int
    start_ms: int | None = None
    end_ms: int | None = None
    stats: list[SignalStats] = Field(default_factory=list)
    events: list[SignalEvent] = Field(default_factory=list)
    evidence_added: int = 0
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
