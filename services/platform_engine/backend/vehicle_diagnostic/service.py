from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from .models import DiagnosticRuntimeStatus


@dataclass
class _TraceEvent:
    timestamp: str
    event: str
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"timestamp": self.timestamp, "event": self.event, **self.data}


@dataclass
class _SimDtc:
    code: str
    raw_dtc: int = 0
    status_byte: int = 0x28
    confirmed: bool = True


@dataclass
class _Runtime:
    adapter: str
    request_id: int
    response_id: int
    connected: bool = True
    trace: list[_TraceEvent] = field(default_factory=list)

    def record(self, event: str, **data) -> None:
        self.trace.append(
            _TraceEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                event=event,
                data=data,
            )
        )


class VehicleDiagnosticService:
    """Deterministic CAN/UDS simulator seam for the current backend.

    Physical adapters remain device-side. The HTTP backend currently exposes
    only a deterministic simulator so API/session flows can be exercised
    without legacy vehicle protocol packages.
    """

    def __init__(self):
        self._runtimes: dict[UUID, _Runtime] = {}

    async def connect(
        self,
        session_id: UUID,
        *,
        adapter: str,
        request_id: int,
        response_id: int,
    ) -> DiagnosticRuntimeStatus:
        if adapter != "simulator":
            raise NotImplementedError(
                "Physical CAN/UDS adapters are device-side in the current phase"
            )

        runtime = self._runtimes.get(session_id)
        if runtime and runtime.connected:
            return self.status(session_id)

        runtime = _Runtime(
            adapter=adapter,
            request_id=request_id,
            response_id=response_id,
        )
        runtime.record(
            "CONNECTED",
            adapter=adapter,
            request_id=request_id,
            response_id=response_id,
        )
        self._runtimes[session_id] = runtime
        return self.status(session_id)

    async def disconnect(self, session_id: UUID) -> DiagnosticRuntimeStatus:
        runtime = self._require(session_id)
        runtime.connected = False
        runtime.record("DISCONNECTED")
        return self.status(session_id)

    async def identify_ecu(self, session_id: UUID):
        runtime = self._require_connected(session_id)
        runtime.record("ECU_IDENTIFICATION")
        return type(
            "EcuIdentity",
            (),
            {
                "vin": "VINTEST1234567890",
                "software_version": "SIM-ECU-1.0",
                "hardware_version": "SIM-HW-1.0",
            },
        )()

    async def read_dtcs(self, session_id: UUID):
        runtime = self._require_connected(session_id)
        records = [_SimDtc(code="P0102", raw_dtc=0x0102)]
        runtime.record("DTC_READ", count=len(records))
        return records

    def trace(self, session_id: UUID, limit: int = 500):
        runtime = self._require(session_id)
        if limit <= 0:
            return []
        return runtime.trace[-limit:]

    def status(self, session_id: UUID) -> DiagnosticRuntimeStatus:
        runtime = self._require(session_id)
        return DiagnosticRuntimeStatus(
            session_id=session_id,
            connected=runtime.connected,
            adapter=runtime.adapter,
            can=runtime.connected,
            isotp=runtime.connected,
            uds=runtime.connected,
            dtc_read=runtime.connected,
            dtc_clear=False,
            trace_events=len(runtime.trace),
        )

    def _require(self, session_id: UUID) -> _Runtime:
        runtime = self._runtimes.get(session_id)
        if runtime is None:
            raise KeyError(session_id)
        return runtime

    def _require_connected(self, session_id: UUID) -> _Runtime:
        runtime = self._require(session_id)
        if not runtime.connected:
            raise RuntimeError("diagnostic connection is stopped")
        return runtime
