from __future__ import annotations
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from time import time_ns
from typing import Any
from uuid import UUID, uuid4

from vehicle.can.models import CanFrame


@dataclass(frozen=True)
class ProtocolTraceEvent:
    event_id: UUID = field(default_factory=uuid4)
    session_id: UUID | None = None
    timestamp_ns: int = field(default_factory=time_ns)
    direction: str = 'RX'
    protocol: str = 'CAN'
    arbitration_id: int | None = None
    data: bytes = b''
    is_extended: bool = False
    is_fd: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value['event_id'] = str(self.event_id)
        value['session_id'] = str(self.session_id) if self.session_id else None
        value['data_hex'] = self.data.hex()
        del value['data']
        return value


class ProtocolTraceRecorder:
    """In-memory protocol trace with deterministic JSON export.

    The recorder captures transport-level frames; it deliberately does not
    expose ECU programming/write operations as part of Phase 16.
    """

    def __init__(self, *, session_id: UUID | None = None, max_events: int = 50_000):
        if max_events < 1:
            raise ValueError('max_events must be >= 1')
        self.session_id = session_id
        self.max_events = max_events
        self._events: list[ProtocolTraceEvent] = []

    def record_can(self, direction: str, frame: CanFrame, *, metadata: dict[str, Any] | None = None) -> ProtocolTraceEvent:
        direction = direction.upper()
        if direction not in {'TX', 'RX'}:
            raise ValueError('direction must be TX or RX')
        event = ProtocolTraceEvent(
            session_id=self.session_id,
            timestamp_ns=frame.timestamp_ns or time_ns(),
            direction=direction,
            protocol='CAN_FD' if frame.is_fd else 'CAN',
            arbitration_id=frame.arbitration_id,
            data=bytes(frame.data),
            is_extended=frame.is_extended,
            is_fd=frame.is_fd,
            metadata=metadata or {},
        )
        self._events.append(event)
        if len(self._events) > self.max_events:
            del self._events[: len(self._events) - self.max_events]
        return event

    def snapshot(self, limit: int | None = None) -> list[ProtocolTraceEvent]:
        if limit is None:
            return list(self._events)
        if limit < 0:
            raise ValueError('limit must be >= 0')
        return list(self._events[-limit:]) if limit else []

    def clear(self) -> None:
        self._events.clear()

    def export_jsonl(self, path: str | Path) -> int:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        body = ''.join(json.dumps(e.to_dict(), sort_keys=True) + '\n' for e in self._events)
        path.write_text(body, encoding='utf-8')
        return len(self._events)


class TracedCanBus:
    """Duck-typed CAN bus wrapper that records every frame crossing the bus."""

    def __init__(self, bus, recorder: ProtocolTraceRecorder):
        self.bus = bus
        self.recorder = recorder

    async def send(self, frame: CanFrame) -> None:
        self.recorder.record_can('TX', frame)
        await self.bus.send(frame)

    async def receive(self, timeout_ms: int = 1000) -> CanFrame | None:
        frame = await self.bus.receive(timeout_ms)
        if frame is not None:
            self.recorder.record_can('RX', frame)
        return frame
