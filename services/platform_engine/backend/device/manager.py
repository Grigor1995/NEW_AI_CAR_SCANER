from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class DeviceConnectionError(RuntimeError):
    pass


class DeviceStatus(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"


@dataclass
class DeviceCapabilities:
    obd: bool = True
    can: bool = True
    uds: bool = True


@dataclass
class DeviceDescriptor:
    device_id: str
    manufacturer: str = "AI-CAR-SCANER"
    model: str = "Simulator"
    firmware_version: str | None = None
    protocol: str = "OBD/CAN"
    connection_type: str = "simulator"
    capabilities: DeviceCapabilities = field(default_factory=DeviceCapabilities)
    status: DeviceStatus = DeviceStatus.DISCONNECTED
    metadata: dict = field(default_factory=dict)


class VCIConnectionManager:
    """Backend device facade: explicit simulator plus real server-local transports."""

    def __init__(self):
        self.devices: dict[str, DeviceDescriptor] = {}
        self.connections: dict[str, dict] = {}
        self._physical_manager = None

    def _physical(self):
        if self._physical_manager is None:
            from vehicle.devices.connection import VCIConnectionManager as PhysicalManager
            self._physical_manager = PhysicalManager()
        return self._physical_manager

    def _publish(self, descriptor):
        self.devices[descriptor.device_id] = descriptor
        return descriptor

    async def _physical_call(self, method, *args):
        try:
            result = await getattr(self._physical(), method)(*args)
            return result
        except Exception as error:
            raise DeviceConnectionError(str(error)) from error

    def add_simulator(self) -> DeviceDescriptor:
        device = DeviceDescriptor(
            device_id="simulator-vci",
            status=DeviceStatus.DISCONNECTED,
            metadata={"simulated": True},
        )
        self.devices[device.device_id] = device
        self.connections.pop(device.device_id, None)
        return device

    async def scan(self, transport: str, timeout: float = 3.0):
        if transport.lower() == "simulator":
            return [self.add_simulator()]
        return [self._publish(d) for d in await self._physical_call("scan", transport, timeout)]

    async def probe_wifi(self, host: str, port: int, timeout: float):
        return self._publish(await self._physical_call("probe_wifi", host, port, timeout))

    async def connect(self, device_id: str, config: dict | None = None):
        if device_id != "simulator-vci":
            return self._publish(await self._physical_call("connect", device_id, config))
        device = self._get(device_id)
        device.status = DeviceStatus.CONNECTED
        self.connections[device_id] = dict(config or {})
        return device

    async def reconnect(self, device_id: str):
        if device_id != "simulator-vci":
            return self._publish(await self._physical_call("reconnect", device_id))
        return await self.connect(device_id, self.connections.get(device_id, {}))

    async def disconnect(self, device_id: str):
        if device_id != "simulator-vci":
            return self._publish(await self._physical_call("disconnect", device_id))
        device = self._get(device_id)
        device.status = DeviceStatus.DISCONNECTED
        return device

    def status(self, device_id: str) -> DeviceDescriptor:
        if device_id != "simulator-vci":
            try:
                return self._physical().status(device_id)
            except Exception as error:
                raise DeviceConnectionError(str(error)) from error
        return self._get(device_id)

    async def read_vin(self, device_id: str):
        if device_id != "simulator-vci":
            return await self._physical_call("read_vin", device_id)
        self._require_connected(device_id)
        return "WDD2110801A123456"

    async def read_dtcs(self, device_id: str):
        if device_id != "simulator-vci":
            return await self._physical_call("read_dtcs", device_id)
        self._require_connected(device_id)
        return ["P0102"]

    async def read_live_data(self, device_id: str):
        if device_id != "simulator-vci":
            return await self._physical_call("read_live_data", device_id)
        self._require_connected(device_id)
        return {
            "rpm": 1696.0,
            "coolant_temp_c": 50.0,
            "vehicle_speed_kmh": 40.0,
            "throttle_pct": 52.0,
        }

    def _get(self, device_id: str) -> DeviceDescriptor:
        device = self.devices.get(device_id)
        if device is None:
            raise DeviceConnectionError(f"Device not found: {device_id}")
        return device

    def _require_connected(self, device_id: str) -> DeviceDescriptor:
        device = self._get(device_id)
        if device.status != DeviceStatus.CONNECTED:
            raise DeviceConnectionError(f"Device is not connected: {device_id}")
        return device

    async def shutdown(self):
        if self._physical_manager is not None:
            await self._physical_manager.shutdown()


def _build_vci_manager():
    """Use real USB/BLE/Wi-Fi adapters ONLY with explicit local opt-in.

    Cloud backends have no access to the user's mobile BLE adapter and must
    never probe local devices or expose LAN probing by default.
    """
    import os
    enabled = os.getenv("AI_CAR_ENABLE_PHYSICAL_VCI", "").strip().lower() in {"1", "true", "yes"}
    host = os.getenv("AI_CAR_BACKEND_HOST", "127.0.0.1").strip().lower()
    if not enabled or host not in {"127.0.0.1", "localhost", "::1"}:
        return VCIConnectionManager()
    from vehicle.devices.connection import VCIConnectionManager as PhysicalManager

    class LocalVciManager(PhysicalManager):
        async def scan(self, transport: str, timeout: float = 3.0):
            if transport.strip().lower() == "simulator":
                return [self.add_simulator()]
            return await super().scan(transport, timeout)

    return LocalVciManager()


vci_manager = _build_vci_manager()
if type(vci_manager).__name__ == "LocalVciManager":
    # Keep the public API's error mapping (409/502) consistent across real and
    # simulated manager implementations.
    from vehicle.devices.connection import DeviceConnectionError as DeviceConnectionError
