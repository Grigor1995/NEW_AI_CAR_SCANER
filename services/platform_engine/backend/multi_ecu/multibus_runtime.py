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
from vehicle.network.models import VehicleNetworkTopology, EcuNode
from vehicle.network.multibus import CanBusConfig, GatewayRoutingEngine, MultiBusDemultiplexer

@dataclass
class RoutedEcuRuntime:
    node: EcuNode
    access_bus: str
    direct: bool

class MultiBusDiagnosticRuntime:
    """Simulation/runtime foundation for concurrent UDS over multiple CAN buses.

    Uses operation-scoped demultiplexers to avoid asyncio event-loop affinity
    issues when the API is driven from different client contexts.
    """
    def __init__(self, *, session_id: UUID, topology: VehicleNetworkTopology, buses: tuple[CanBusConfig, ...]):
        self.session_id = session_id
        self.topology = topology
        self.bus_configs = {b.name: b for b in buses}
        if not self.bus_configs:
            raise ValueError('at least one CAN bus is required')
        missing = {e.bus for e in topology.ecus if e.bus not in self.bus_configs}
        if missing:
            raise ValueError(f'ECU references unknown bus(es): {sorted(missing)}')
        self.raw_buses = {name: SimulatedCanBus() for name in self.bus_configs}
        self.traces = {name: ProtocolTraceRecorder(session_id=session_id) for name in self.bus_configs}
        self.routed_buses = {name: TracedCanBus(self.raw_buses[name], self.traces[name]) for name in self.bus_configs}
        self.gateway = GatewayRoutingEngine(self.raw_buses, topology)
        self.ecus: dict[str, RoutedEcuRuntime] = {}
        self.connected = False

    async def connect(self) -> None:
        if self.connected:
            return
        self.gateway.install()
        await self.gateway.start()
        for node in self.topology.ecus:
            UdsEcuSimulator(
                self.raw_buses[node.bus], request_id=node.request_id, response_id=node.response_id,
                vin=node.metadata.get('vin', f'VIN-{node.ecu_id}'),
                software_version=node.metadata.get('software_version', f'{node.ecu_id}-SW-1.0'),
                hardware_version=node.metadata.get('hardware_version', f'{node.ecu_id}-HW-1.0'),
                dtc_records=node.metadata.get('dtc_records', []),
            )
            route = self.gateway.route_for_ecu(node.ecu_id)
            access_bus = route.source_bus if route else node.bus
            self.ecus[node.ecu_id] = RoutedEcuRuntime(node=node, access_bus=access_bus, direct=route is None)
        self.connected = True

    async def disconnect(self) -> None:
        await self.gateway.stop()
        self.ecus.clear()
        self.connected = False

    def topology_view(self) -> dict:
        return {
            'buses': [cfg.to_dict() for cfg in self.bus_configs.values()],
            'network': self.topology.to_dict(),
            'gateway_stats': self.gateway.stats(),
        }

    async def identify_all(self) -> dict[str, object]:
        return await self._concurrent('identify_ecu')

    async def read_all_dtcs(self) -> dict[str, list]:
        return await self._concurrent('read_dtcs')

    async def _concurrent(self, method: str) -> dict[str, object]:
        if not self.connected:
            raise RuntimeError('multi-bus runtime is disconnected')
        routed_target_ecus = {r.target_ecu_id for r in self.topology.routes}
        response_ids_by_bus = {}
        for name in self.bus_configs:
            response_ids_by_bus[name] = [
                e.response_id for e in self.topology.ecus
                if e.bus == name and e.ecu_id not in routed_target_ecus
            ]
        demuxes = {
            name: MultiBusDemultiplexer(self.raw_buses[name], response_ids_by_bus[name])
            for name in self.bus_configs
        }
        for demux in demuxes.values():
            await demux.start()
        try:
            async def one(ecu_id: str, runtime: RoutedEcuRuntime):
                node = runtime.node
                queue = demuxes[runtime.access_bus].queues.setdefault(node.response_id, asyncio.Queue())
                class Channel:
                    async def send(inner, frame):
                        await self.routed_buses[runtime.access_bus].send(frame)
                    async def receive(inner, timeout_ms=1000):
                        try:
                            return await asyncio.wait_for(queue.get(), timeout_ms / 1000)
                        except asyncio.TimeoutError:
                            return None
                diag = UdsDiagnosticSession(UdsClient(IsoTpStack(Channel(), node.request_id, node.response_id)))
                return ecu_id, await getattr(diag, method)()
            return dict(await asyncio.gather(*(one(k, v) for k, v in self.ecus.items())))
        finally:
            for demux in demuxes.values():
                await demux.stop()
