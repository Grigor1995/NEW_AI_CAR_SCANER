from __future__ import annotations
import asyncio
from dataclasses import dataclass
from typing import Iterable
from vehicle.can.models import CanFrame
from vehicle.adapters.can_simulator import SimulatedCanBus
from .models import GatewayRoute, VehicleNetworkTopology

@dataclass(frozen=True)
class CanBusConfig:
    name: str
    bitrate: int = 500_000
    can_fd: bool = False
    data_bitrate: int | None = None
    def to_dict(self) -> dict:
        return {'name': self.name, 'bitrate': self.bitrate, 'can_fd': self.can_fd, 'data_bitrate': self.data_bitrate}

class GatewayRoutingEngine:
    """Read-only bidirectional diagnostic routing abstraction."""
    def __init__(self, buses: dict[str, SimulatedCanBus], topology: VehicleNetworkTopology):
        self.buses = buses; self.topology = topology
        self._request_to_target: dict[tuple[str, int], str] = {}
        self._response_to_source: dict[tuple[str, int], str] = {}
        self.forwarded_frames = 0; self.blocked_frames = 0

    def install(self) -> None:
        for route in self.topology.routes:
            ecu = self.topology.ecu(route.target_ecu_id)
            if route.source_bus not in self.buses or route.target_bus not in self.buses:
                raise ValueError(f'route references unknown bus: {route}')
            self._request_to_target[(route.source_bus, ecu.request_id)] = route.target_bus
            self._response_to_source[(route.target_bus, ecu.response_id)] = route.source_bus
        for bus_name, bus in self.buses.items():
            async def tx_hook(frame: CanFrame, source_bus=bus_name):
                target_bus = self._request_to_target.get((source_bus, frame.arbitration_id))
                if target_bus and target_bus != source_bus:
                    self.forwarded_frames += 1
                    await self.buses[target_bus].send(frame)
            bus.add_tx_hook(tx_hook)
            def rx_hook(frame: CanFrame, target_bus=bus_name):
                source_bus = self._response_to_source.get((target_bus, frame.arbitration_id))
                if source_bus and source_bus != target_bus:
                    self.forwarded_frames += 1
                    self.buses[source_bus].inject(frame)
            bus.add_rx_hook(rx_hook)

    async def start(self) -> None:
        return None
    async def stop(self) -> None:
        return None
    def route_for_ecu(self, ecu_id: str, source_bus: str | None = None) -> GatewayRoute | None:
        candidates = [r for r in self.topology.routes if r.target_ecu_id == ecu_id]
        if source_bus is not None: candidates = [r for r in candidates if r.source_bus == source_bus]
        return candidates[0] if candidates else None
    def stats(self) -> dict:
        return {'forwarded_frames': self.forwarded_frames, 'blocked_frames': self.blocked_frames}

class MultiBusDemultiplexer:
    """One receive task per physical/logical CAN bus."""
    def __init__(self, bus: SimulatedCanBus, response_ids: Iterable[int], poll_timeout_ms: int = 100):
        self.bus = bus; self.response_ids = set(response_ids); self.poll_timeout_ms = poll_timeout_ms
        self.queues: dict[int, asyncio.Queue] = {rid: asyncio.Queue() for rid in self.response_ids}
        self._task: asyncio.Task | None = None; self._stop: asyncio.Event | None = None
        self.unmatched: list[CanFrame] = []
    async def start(self) -> None:
        if self._task and not self._task.done(): return
        self._stop = asyncio.Event(); self._task = asyncio.create_task(self._run(), name='multi-bus-demux')
    async def stop(self) -> None:
        if self._stop: self._stop.set()
        if self._task: await self._task
        self._task = None
    async def _run(self) -> None:
        while self._stop and not self._stop.is_set():
            frame = await self.bus.receive(self.poll_timeout_ms)
            if frame is None: continue
            queue = self.queues.get(frame.arbitration_id)
            if queue is None:
                self.unmatched.append(frame)
                if len(self.unmatched) > 500: del self.unmatched[:250]
            else: queue.put_nowait(frame)
