from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from time import time_ns
from uuid import UUID, uuid4
from typing import Any

class AcquisitionState(str, Enum):
    STOPPED = 'STOPPED'
    STARTING = 'STARTING'
    RUNNING = 'RUNNING'
    RECONNECTING = 'RECONNECTING'
    DEGRADED = 'DEGRADED'
    ERROR = 'ERROR'

class AcquisitionSourceType(str, Enum):
    OBD_PID = 'OBD_PID'
    CAN_FRAME = 'CAN_FRAME'
    UDS_DID = 'UDS_DID'

@dataclass(frozen=True)
class ReconnectPolicy:
    max_attempts: int = 5
    initial_backoff_s: float = 0.25
    max_backoff_s: float = 5.0
    multiplier: float = 2.0

    def delay(self, attempt: int) -> float:
        if attempt < 1:
            return self.initial_backoff_s
        return min(self.max_backoff_s, self.initial_backoff_s * (self.multiplier ** (attempt - 1)))

@dataclass(frozen=True)
class AcquisitionRecord:
    id: UUID = field(default_factory=uuid4)
    session_id: UUID = field(default_factory=uuid4)
    timestamp_ns: int = field(default_factory=time_ns)
    source_type: AcquisitionSourceType = AcquisitionSourceType.OBD_PID
    channel: str = ''
    numeric_value: float | None = None
    unit: str | None = None
    raw: bytes | None = None
    sequence: int = 0
    quality: str = 'GOOD'
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def timestamp_ms(self) -> int:
        return self.timestamp_ns // 1_000_000
