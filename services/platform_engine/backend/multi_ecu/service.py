from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from .models import MultiEcuConnectRequest


@dataclass
class EcuNode:
    ecu_id: str
    name: str
    request_id: int
    response_id: int
    bus: str
    gateway_id: str | None
    address_type: str
    capabilities: frozenset[str]
    metadata: dict = field(default_factory=dict)


@dataclass
class GatewayNode:
    gateway_id: str
    name: str
    bus: str


@dataclass
class VehicleNetworkTopology:
    ecus: tuple[EcuNode, ...]
    gateways: tuple[GatewayNode, ...]

    def to_dict(self) -> dict:
        return {
            "ecus": [vars(e) | {"capabilities": sorted(e.capabilities)} for e in self.ecus],
            "gateways": [vars(g) for g in self.gateways],
        }


@dataclass
class SimDtc:
    code: str
    raw_dtc: int
    status_byte: int
    confirmed: bool

    def to_dict(self) -> dict:
        return vars(self)


@dataclass
class SimIdentity:
    vin: str
    software_version: str
    hardware_version: str

    def to_dict(self) -> dict:
        return vars(self)


@dataclass
class TraceEvent:
    timestamp: str
    event: str
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"timestamp": self.timestamp, "event": self.event, **self.data}


class MultiEcuRuntime:
    """Deterministic multi-ECU simulator with no legacy vehicle.* dependencies."""

    def __init__(self, session_id: UUID, topology: VehicleNetworkTopology):
        self.session_id = session_id
        self.topology = topology
        self.connected = False
        self._trace: list[TraceEvent] = []

    async def connect(self):
        self.connected = True
        self._record("CONNECTED", ecu_count=len(self.topology.ecus))

    async def disconnect(self):
        self.connected = False
        self._record("DISCONNECTED")

    def discover(self):
        self._require_connected()
        self._record("TOPOLOGY_DISCOVERY")
        return self.topology

    async def identify_all(self):
        self._require_connected()
        result = {}
        for ecu in self.topology.ecus:
            result[ecu.ecu_id] = SimIdentity(
                vin=ecu.metadata.get("vin", "SIMULATORVIN0000001"),
                software_version=ecu.metadata.get("software_version", f"{ecu.ecu_id}-SW-1.0"),
                hardware_version=ecu.metadata.get("hardware_version", f"{ecu.ecu_id}-HW-1.0"),
            )
        self._record("IDENTIFY_ALL", ecu_count=len(result))
        return result

    async def read_all_dtcs(self):
        self._require_connected()
        result = {}
        for ecu in self.topology.ecus:
            records = []
            for raw_dtc, status in ecu.metadata.get("dtc_records", []):
                code = self._raw_dtc_to_code(raw_dtc)
                records.append(SimDtc(
                    code=code,
                    raw_dtc=raw_dtc,
                    status_byte=status,
                    confirmed=bool(status & 0x28),
                ))
            result[ecu.ecu_id] = records
        self._record("DTC_READ_ALL", ecu_count=len(result))
        return result

    def correlate_dtcs(self, dtcs):
        by_code: dict[str, list[str]] = {}
        for ecu_id, records in dtcs.items():
            for record in records:
                by_code.setdefault(record.code, []).append(ecu_id)

        correlations = []
        for code, ecu_ids in by_code.items():
            if len(ecu_ids) > 1:
                correlations.append({
                    "type": "SHARED_DTC",
                    "code": code,
                    "ecu_ids": ecu_ids,
                    "relationship": "shared across ECUs",
                })
            else:
                correlations.append({
                    "type": "ECU_LOCAL",
                    "code": code,
                    "ecu_ids": ecu_ids,
                    "relationship": "ECU-local",
                })
        return correlations

    def trace_snapshot(self, limit: int = 500):
        return self._trace[-limit:]

    def _record(self, event: str, **data):
        self._trace.append(TraceEvent(
            datetime.now(timezone.utc).isoformat(), event, data
        ))

    def _require_connected(self):
        if not self.connected:
            raise RuntimeError("multi-ECU diagnostic runtime is not connected")

    @staticmethod
    def _raw_dtc_to_code(raw: int) -> str:
        # ISO 14229-style 3-byte DTC to a readable P/C/B/U code.
        first = (raw >> 16) & 0xFF
        prefix = "PCBU"[(first >> 6) & 0x03]
        digit1 = (first >> 4) & 0x03
        digit2 = first & 0x0F
        digit3 = (raw >> 8) & 0xFF
        return f"{prefix}{digit1}{digit2:X}{digit3:02X}" if prefix else f"P{digit1}{digit2:X}{digit3:02X}"


class MultiEcuDiagnosticService:
    def __init__(self):
        self.runtimes: dict[UUID, MultiEcuRuntime] = {}

    async def connect(self, session_id: UUID, request: MultiEcuConnectRequest):
        existing = self.runtimes.get(session_id)
        if existing and existing.connected:
            return existing

        nodes = [
            EcuNode(
                ecu_id=ecu.ecu_id,
                name=ecu.name,
                request_id=ecu.request_id,
                response_id=ecu.response_id,
                bus=ecu.bus,
                gateway_id=ecu.gateway_id,
                address_type=ecu.address_type,
                capabilities=frozenset(ecu.capabilities),
                metadata={
                    "vin": ecu.vin or "VINTEST1234567890",
                    "software_version": ecu.software_version or f"{ecu.ecu_id}-SW-1.0",
                    "hardware_version": ecu.hardware_version or f"{ecu.ecu_id}-HW-1.0",
                    "dtc_records": ecu.dtc_records or [(0x030200, 0x28)],
                },
            )
            for ecu in request.ecus
        ]
        gateways = tuple(
            GatewayNode(gateway_id=g.gateway_id, name=g.name, bus=g.bus)
            for g in request.gateways
        )
        runtime = MultiEcuRuntime(
            session_id=session_id,
            topology=VehicleNetworkTopology(tuple(nodes), gateways),
        )
        await runtime.connect()
        self.runtimes[session_id] = runtime
        return runtime

    async def disconnect(self, session_id: UUID):
        runtime = self.require(session_id)
        await runtime.disconnect()
        return runtime

    def require(self, session_id: UUID) -> MultiEcuRuntime:
        runtime = self.runtimes.get(session_id)
        if runtime is None:
            raise KeyError(session_id)
        return runtime
