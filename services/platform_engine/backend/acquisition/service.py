from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4

from api.telemetry_routes import service as telemetry_service
from telemetry.models import TelemetrySample
from .models import AcquisitionStartRequest, AcquisitionStatus, SimulatorParameters


class AcquisitionSourceType(str, Enum):
    OBD_ACQUISITION = "OBD_ACQUISITION"


@dataclass
class AcquisitionRecord:
    """Small API-facing record kept by the simulator acquisition service."""

    id: UUID = field(default_factory=uuid4)
    session_id: UUID | None = None
    timestamp_ms: int = 0
    channel: str = ""
    numeric_value: float | None = None
    unit: str | None = None
    sequence: int | None = None
    quality: str = "GOOD"
    metadata: dict = field(default_factory=dict)
    source_type: AcquisitionSourceType = AcquisitionSourceType.OBD_ACQUISITION
    raw: bytes | None = None


@dataclass
class _AcquisitionState:
    state: str = "STOPPED"
    adapter: str = "simulator"
    records: list[AcquisitionRecord] = field(default_factory=list)
    task: asyncio.Task | None = None
    sequence: int = 0
    parameters: SimulatorParameters = field(default_factory=SimulatorParameters)
    stats: dict[str, int] = field(default_factory=lambda: {
        "polls": 0,
        "records": 0,
        "errors": 0,
        "reconnects": 0,
    })


class AcquisitionApiService:
    """Simulator acquisition facade backed by the existing telemetry service."""

    def __init__(self):
        self._states: dict[UUID, _AcquisitionState] = {}

    async def start_simulator(
        self, session_id: UUID, request: AcquisitionStartRequest
    ) -> AcquisitionStatus:
        state = self._states.setdefault(session_id, _AcquisitionState())
        if state.task and not state.task.done():
            return self.status(session_id)

        if any(s.source in {"NATIVE_OBD_BRIDGE", "SERVER_LOCAL_OBD"} for s in telemetry_service.samples(session_id)):
            raise ValueError("Create a new session before switching real measurements to simulator data")
        state.adapter = "simulator"
        state.state = "STARTING"
        state.stats = {"polls": 0, "records": 0, "errors": 0, "reconnects": 0}
        state.records.clear()
        state.sequence = 0
        state.task = asyncio.create_task(
            self._poll_simulator(session_id, state, request),
            name=f"acquisition-{session_id}",
        )
        state.state = "RUNNING"
        return self.status(session_id)

    def set_simulator_parameters(self, session_id, parameters: SimulatorParameters):
        state = self._require(session_id)
        if state.adapter != "simulator":
            raise ValueError("Parameters can only be changed for the simulator")
        state.parameters = parameters
        return parameters

    async def start_device(self, session_id, request, manager, device_id):
        state = self._states.setdefault(session_id, _AcquisitionState())
        if state.task and not state.task.done():
            raise ValueError("Stop the current acquisition before switching adapters")
        if any(s.source in {"SIMULATOR", "OBD_ACQUISITION"} for s in telemetry_service.samples(session_id)):
            raise ValueError("Create a new session before adding real measurements to simulator data")
        state.adapter = request.adapter
        state.stats = {"polls": 0, "records": 0, "errors": 0, "reconnects": 0}
        state.state = "RUNNING"
        state.records.clear()
        state.sequence = 0
        state.task = asyncio.create_task(self._poll_device(session_id, state, request, manager, device_id))
        return self.status(session_id)

    def append_bridge(self, session_id, result, *, adapter="native_bridge"):
        state = self._states.setdefault(session_id, _AcquisitionState())
        if state.task and not state.task.done():
            raise ValueError("A server-local acquisition is running for this session")
        if state.adapter != adapter:
            state.records.clear()
            state.sequence = 0
            state.stats = {"polls": 0, "records": 0, "errors": 0, "reconnects": 0}
        state.adapter = adapter
        state.state = "RUNNING"
        state.stats["polls"] += 1
        for key, value in result["values"].items():
            if value is None:
                continue
            state.sequence += 1
            state.records.append(AcquisitionRecord(session_id=session_id, timestamp_ms=int(time.time()*1000),
                                 channel=key, numeric_value=value, unit=result["units"].get(key), sequence=state.sequence,
                                 metadata={"adapter": adapter, "protocol": result.get("protocol")}))
            state.stats["records"] += 1
        del state.records[:-5000]

    async def _poll_device(self, session_id, state, request, manager, device_id):
        from obd.decoding import PIDS
        selected = [p for p in PIDS if int(p.command[2:], 16) in request.pids]
        names = {"coolant_c":"coolant_temp", "speed_kmh":"vehicle_speed", "throttle_percent":"throttle",
                 "maf_gps":"maf", "map_kpa":"map", "short_fuel_trim_percent":"stft", "long_fuel_trim_percent":"ltft"}
        try:
            while True:
                values = await manager.read_live_data(device_id)
                state.stats["polls"] += 1
                if not any(value is not None for value in values.values()):
                    raise ConnectionError("No valid OBD PID values received")
                for pid in selected:
                    value = values.get(pid.key)
                    if value is None:
                        continue
                    state.sequence += 1
                    now = int(time.time()*1000)
                    state.records.append(AcquisitionRecord(session_id=session_id, timestamp_ms=now,
                        channel=pid.key, numeric_value=value, unit=pid.unit, sequence=state.sequence,
                        metadata={"adapter": request.adapter, "device_id": device_id}))
                    telemetry_service.append([TelemetrySample(session_id=session_id, timestamp_ms=now,
                        pid=names.get(pid.key,pid.key), value=value, unit=pid.unit, source="SERVER_LOCAL_OBD")])
                    state.stats["records"] += 1
                del state.records[:-5000]
                await asyncio.sleep(request.poll_interval_ms/1000)
        except asyncio.CancelledError:
            raise
        except Exception:
            state.stats["errors"] += 1
            state.state = "ERROR"

    async def shutdown(self):
        for session_id in list(self._states):
            await self.stop(session_id)

    async def _poll_simulator(
        self,
        session_id: UUID,
        state: _AcquisitionState,
        request: AcquisitionStartRequest,
    ) -> None:
        try:
            while True:
                parameters = state.parameters
                base_values = {0x0C: (parameters.rpm, "rpm"), 0x05: (parameters.coolant_c, "C"),
                               0x0D: (parameters.speed_kmh, "km/h"), 0x11: (parameters.throttle_percent, "%")}
                now_ms = int(time.time() * 1000)
                samples: list[TelemetrySample] = []
                for pid in request.pids:
                    value, unit = base_values.get(pid, (0.0, None))
                    state.sequence += 1
                    state.records.append(AcquisitionRecord(
                        session_id=session_id,
                        timestamp_ms=now_ms,
                        channel=f"0x{pid:02X}",
                        numeric_value=value,
                        unit=unit,
                        sequence=state.sequence,
                        quality="GOOD",
                        metadata={"pid": pid, "adapter": "simulator"},
                    ))
                    samples.append(TelemetrySample(
                        session_id=session_id,
                        timestamp_ms=now_ms,
                        pid=f"0x{pid:02X}",
                        value=value,
                        unit=unit,
                        source="SIMULATOR",
                        metadata={"simulated": True},
                        sequence=state.sequence,
                    ))

                del state.records[:-5000]
                if samples:
                    telemetry_service.append(samples)
                state.stats["polls"] += 1
                state.stats["records"] += len(samples)
                await asyncio.sleep(request.poll_interval_ms / 1000.0)
        except asyncio.CancelledError:
            state.state = "STOPPED"
            raise
        except Exception:
            state.stats["errors"] += 1
            state.state = "ERROR"

    async def stop(self, session_id: UUID) -> AcquisitionStatus:
        state = self._require(session_id)
        if state.task and not state.task.done():
            state.task.cancel()
            try:
                await state.task
            except asyncio.CancelledError:
                pass
        state.task = None
        state.state = "STOPPED"
        return self.status(session_id)

    def status(self, session_id: UUID) -> AcquisitionStatus:
        state = self._require(session_id)
        return AcquisitionStatus(
            session_id=session_id,
            state=state.state,
            adapter=state.adapter,
            stats=state.stats.copy(),
            buffered_records=len(state.records),
            offline_queue_items=0,
        )

    def snapshot(self, session_id: UUID, limit: int = 100):
        return self._require(session_id).records[-limit:]

    def _require(self, session_id: UUID) -> _AcquisitionState:
        if session_id not in self._states:
            raise KeyError(session_id)
        return self._states[session_id]
