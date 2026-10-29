from __future__ import annotations
import asyncio
from dataclasses import dataclass
from uuid import UUID
from vehicle.adapters.can_simulator import SimulatedCanBus
from vehicle.adapters.uds_simulator import UdsEcuSimulator
from vehicle.isotp.stack import IsoTpStack
from vehicle.protocol.trace import ProtocolTraceRecorder, TracedCanBus
from vehicle.uds.client import UdsClient
from vehicle.uds.diagnostics import UdsDiagnosticSession
from .models import EcuNode, VehicleNetworkTopology
from .multiplexer import CanBusDemultiplexer

@dataclass
class EcuRuntime:
    node: EcuNode
    connected: bool = True

class MultiEcuRuntime:
    """Shared-bus multi-ECU read-only diagnostic runtime.

    Per-operation UDS channels are intentionally created fresh. This keeps the
    transport loop independent from HTTP request event loops used by desktop,
    mobile and API test clients while retaining one logical vehicle session.
    """
    def __init__(self, *, session_id: UUID, topology: VehicleNetworkTopology):
        self.session_id = session_id
        self.topology = topology
        self.raw_bus = SimulatedCanBus()
        self.trace = ProtocolTraceRecorder(session_id=session_id)
        self.traced_bus = TracedCanBus(self.raw_bus, self.trace)
        self.mux = CanBusDemultiplexer(self.traced_bus)
        self.ecus: dict[str, EcuRuntime] = {}
        self.gateways = {g.gateway_id: g for g in topology.gateways}
        self._simulators: list[UdsEcuSimulator] = []
        self.connected = False

    async def connect(self) -> None:
        if self.connected:
            return
        for node in self.topology.ecus:
            UdsEcuSimulator(
                self.raw_bus,
                request_id=node.request_id,
                response_id=node.response_id,
                vin=node.metadata.get('vin', 'VINTEST1234567890'),
                software_version=node.metadata.get('software_version', f'{node.ecu_id}-SW-1.0'),
                hardware_version=node.metadata.get('hardware_version', f'{node.ecu_id}-HW-1.0'),
                dtc_records=node.metadata.get('dtc_records'),
            )
            self.ecus[node.ecu_id] = EcuRuntime(node=node)
        self.connected = True

    async def disconnect(self) -> None:
        await self.mux.stop()
        for runtime in self.ecus.values():
            runtime.connected = False
        self.ecus.clear()
        self.connected = False

    async def identify_all(self) -> dict[str, object]:
        self._require_connected()
        return await self._run_concurrent('identify_ecu')

    async def read_all_dtcs(self) -> dict[str, list]:
        self._require_connected()
        return await self._run_concurrent('read_dtcs')

    async def _run_concurrent(self, method: str) -> dict[str, object]:
        # Each HTTP/API operation gets fresh queues/channels to avoid asyncio
        # queue loop affinity across independent request event loops.
        await self.mux.start()
        channels = {r.node.ecu_id: self.mux.register(r.node.response_id) for r in self.ecus.values()}
        try:
            async def one(ecu_id: str, runtime: EcuRuntime):
                channel = channels[ecu_id]
                client = UdsClient(IsoTpStack(channel, runtime.node.request_id, runtime.node.response_id))
                diag = UdsDiagnosticSession(client)
                value = await getattr(diag, method)()
                return ecu_id, value
            pairs = await asyncio.gather(*(one(ecu_id, runtime) for ecu_id, runtime in self.ecus.items()), return_exceptions=False)
            return dict(pairs)
        finally:
            for channel in channels.values():
                self.mux.unregister(channel)
            await self.mux.stop()

    def correlate_dtcs(self, dtcs_by_ecu: dict[str, list]) -> list[dict]:
        by_code: dict[str, list[str]] = {}
        for ecu_id, records in dtcs_by_ecu.items():
            for record in records:
                by_code.setdefault(record.code, []).append(ecu_id)
        correlations = []
        for code, ecus in by_code.items():
            if len(ecus) > 1:
                correlations.append({
                    'type': 'SHARED_DTC', 'code': code, 'ecu_ids': sorted(ecus),
                    'evidence': f'DTC {code} reported by multiple ECUs',
                    'interpretation': 'Cross-ECU correlation; root cause is not confirmed.',
                })
            if code.startswith('U'):
                correlations.append({
                    'type': 'NETWORK_DTC', 'code': code, 'ecu_ids': sorted(ecus),
                    'evidence': f'Network-related DTC {code} reported by ECU set',
                    'interpretation': 'Consider communication path, gateway, power or bus integrity checks.',
                })
        return correlations

    def discover(self) -> VehicleNetworkTopology:
        return self.topology

    def trace_snapshot(self, limit: int = 500):
        return self.trace.snapshot(limit)

    def _require_connected(self) -> None:
        if not self.connected:
            raise RuntimeError('multi-ECU diagnostic runtime is disconnected')
