from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from vehicle.devices.models import DeviceCapabilities, DeviceDescriptor, DeviceStatus
from vehicle.obd.adapters.ble import ObdBleTransport
from vehicle.obd.adapters.simulator import SimulatorTransport
from vehicle.obd.adapters.tcp_wifi import ObdWifiTransport
from vehicle.obd.adapters.usb_serial import ObdUsbSerialTransport
from vehicle.obd.client import GenericObdClient
from vehicle.obd.transport import DiagnosticTransport


@dataclass
class ManagedConnection:
    descriptor: DeviceDescriptor
    transport: DiagnosticTransport
    obd: GenericObdClient | None = None


class DeviceConnectionError(ConnectionError):
    pass


class VCIConnectionManager:
    """Runtime device discovery and connection manager.

    Physical discovery is intentionally generic: USB means serial adapters,
    BLE means discoverable GATT peripherals, and Wi-Fi uses explicit host/port
    probing because a generic automotive TCP broadcast protocol does not exist.
    """

    def __init__(self) -> None:
        self.devices: dict[str, DeviceDescriptor] = {}
        self.connections: dict[str, ManagedConnection] = {}

    def _register(self, descriptor: DeviceDescriptor) -> DeviceDescriptor:
        self.devices[descriptor.device_id] = descriptor
        return descriptor

    async def scan(self, transport: str, timeout: float = 3.0) -> list[DeviceDescriptor]:
        transport = transport.lower().strip()
        if transport == "usb":
            return await self._scan_usb()
        if transport == "ble":
            return await self._scan_ble(timeout)
        raise DeviceConnectionError(
            "Generic Wi-Fi discovery is intentionally not automatic; provide a host/port and use Wi-Fi probe."
        )

    async def _scan_usb(self) -> list[DeviceDescriptor]:
        try:
            from serial.tools import list_ports
        except ImportError as exc:
            raise DeviceConnectionError("pyserial is required for USB device discovery") from exc

        ports = await asyncio.to_thread(lambda: list(list_ports.comports()))
        found: list[DeviceDescriptor] = []
        for port in ports:
            descriptor = DeviceDescriptor(
                device_id=f"usb:{port.device}",
                manufacturer=(port.manufacturer or "Unknown USB").strip(),
                model=(port.product or port.description or "Serial VCI").strip(),
                protocol="ELM327-compatible serial",
                connection_type="USB",
                capabilities=DeviceCapabilities(obd=True, can=False, uds=False, usb=True),
                metadata={
                    "port": port.device,
                    "serial_number": port.serial_number,
                    "vid": port.vid,
                    "pid": port.pid,
                    "description": port.description,
                    "hwid": port.hwid,
                },
            )
            found.append(self._register(descriptor))
        return found

    async def _scan_ble(self, timeout: float) -> list[DeviceDescriptor]:
        try:
            from bleak import BleakScanner
        except ImportError as exc:
            raise DeviceConnectionError("bleak is required for BLE discovery") from exc

        devices = await BleakScanner.discover(timeout=max(0.5, min(timeout, 30.0)))
        found: list[DeviceDescriptor] = []
        for device in devices:
            metadata = dict(getattr(device, "metadata", {}) or {})
            descriptor = DeviceDescriptor(
                device_id=f"ble:{device.address}",
                manufacturer="Unknown BLE",
                model=(device.name or "BLE VCI").strip(),
                protocol="BLE GATT / adapter-specific",
                connection_type="BLE",
                capabilities=DeviceCapabilities(obd=True, ble=True),
                metadata={
                    "address": device.address,
                    "name": device.name,
                    "rssi": getattr(device, "rssi", None),
                    "details": metadata,
                },
            )
            found.append(self._register(descriptor))
        return found

    async def probe_wifi(self, host: str, port: int = 35000, timeout: float = 2.0) -> DeviceDescriptor:
        host = host.strip()
        if not host:
            raise DeviceConnectionError("Wi-Fi host is required")
        try:
            reader, writer = await asyncio.wait_for(asyncio.open_connection(host, int(port)), timeout=timeout)
            writer.close()
            await writer.wait_closed()
        except Exception as exc:
            raise DeviceConnectionError(f"Wi-Fi probe failed for {host}:{port}: {exc}") from exc

        descriptor = DeviceDescriptor(
            device_id=f"wifi:{host}:{int(port)}",
            manufacturer="Unknown Wi-Fi",
            model="TCP OBD VCI",
            protocol="ELM327-compatible TCP",
            connection_type="Wi-Fi",
            capabilities=DeviceCapabilities(obd=True, wifi=True),
            metadata={"host": host, "port": int(port)},
        )
        return self._register(descriptor)

    def add_simulator(self) -> DeviceDescriptor:
        device_id = f"simulator:{uuid4()}"
        descriptor = DeviceDescriptor(
            device_id=device_id,
            manufacturer="AI Auto Diagnostic",
            model="OBD-II Simulator",
            firmware_version="sim-1",
            protocol="ELM327 simulator",
            connection_type="SIMULATOR",
            capabilities=DeviceCapabilities(obd=True, can=True, uds=True),
            metadata={
                "responses": {
                    "0100": "41 00 08 18 80 00",
                    "ATZ": "ELM327 v2.2",
                    "ATE0": "OK",
                    "ATL0": "OK",
                    "ATS0": "OK",
                    "ATSP0": "OK",
                    "0902": "49 02 01 57 44 44 32 31 31 30 38 30 31 41 31 32 33 34 35 36",
                    "03": "43 01 02",
                    "010C": "41 0C 1A 80",
                    "0105": "41 05 5A",
                    "010D": "41 0D 28",
                    "0111": "41 11 80",
                }
            },
        )
        return self._register(descriptor)

    def _transport_for(self, descriptor: DeviceDescriptor, config: dict[str, Any]) -> DiagnosticTransport:
        kind = descriptor.connection_type.upper().replace("-", "") if descriptor.connection_type else ""
        if kind == "USB":
            port = str(config.get("port") or descriptor.metadata.get("port") or "")
            if not port:
                raise DeviceConnectionError("USB serial port is required")
            return ObdUsbSerialTransport(port, int(config.get("baudrate", 115200)))
        if kind == "WIFI":
            host = str(config.get("host") or descriptor.metadata.get("host") or "")
            port = int(config.get("port") or descriptor.metadata.get("port") or 35000)
            return ObdWifiTransport(host, port)
        if kind == "BLE":
            address = str(config.get("address") or descriptor.metadata.get("address") or "")
            tx_uuid = str(config.get("tx_uuid") or "")
            rx_uuid = str(config.get("rx_uuid") or "")
            if not tx_uuid or not rx_uuid:
                raise DeviceConnectionError("BLE TX UUID and RX UUID are required for adapter-specific GATT communication")
            return ObdBleTransport(address, tx_uuid, rx_uuid)
        if kind == "SIMULATOR":
            return SimulatorTransport(dict(descriptor.metadata.get("responses") or {}))
        raise DeviceConnectionError(f"Unsupported device connection type: {kind}")

    async def connect(self, device_id: str, config: dict[str, Any] | None = None) -> DeviceDescriptor:
        descriptor = self.devices.get(device_id)
        if descriptor is None:
            raise DeviceConnectionError(f"Unknown device: {device_id}")
        config = dict(config or {})
        if device_id in self.connections:
            await self.disconnect(device_id)
        descriptor.status = DeviceStatus.CONNECTING
        transport = None
        try:
            transport = self._transport_for(descriptor, config)
            obd = GenericObdClient(transport, protocol_id=str(config.get("protocol_id", "auto")))
            await obd.connect()
            self.connections[device_id] = ManagedConnection(descriptor, transport, obd)
            descriptor.status = DeviceStatus.CONNECTED
            descriptor.metadata["last_error"] = None
            descriptor.metadata["connection_config"] = config
            return descriptor
        except BaseException as exc:
            if transport is not None:
                await transport.disconnect()
            descriptor.status = DeviceStatus.ERROR
            descriptor.metadata["last_error"] = str(exc)
            if isinstance(exc, asyncio.CancelledError):
                raise
            raise DeviceConnectionError(str(exc)) from exc

    async def disconnect(self, device_id: str) -> DeviceDescriptor:
        descriptor = self.devices.get(device_id)
        if descriptor is None:
            raise DeviceConnectionError(f"Unknown device: {device_id}")
        managed = self.connections.pop(device_id, None)
        if managed:
            await managed.transport.disconnect()
        descriptor.status = DeviceStatus.DISCONNECTED
        return descriptor

    def status(self, device_id: str) -> DeviceDescriptor:
        descriptor = self.devices.get(device_id)
        if descriptor is None:
            raise DeviceConnectionError(f"Unknown device: {device_id}")
        managed = self.connections.get(device_id)
        if managed is not None and not managed.transport.connected:
            descriptor.status = DeviceStatus.ERROR
        return descriptor

    async def reconnect(self, device_id: str) -> DeviceDescriptor:
        descriptor = self.devices.get(device_id)
        if descriptor is None:
            raise DeviceConnectionError(f"Unknown device: {device_id}")
        config = dict(descriptor.metadata.get("connection_config") or {})
        try:
            await self.disconnect(device_id)
        except DeviceConnectionError:
            pass
        return await self.connect(device_id, config)

    def connected_obd(self, device_id: str) -> GenericObdClient:
        managed = self.connections.get(device_id)
        if managed is None or managed.obd is None:
            raise DeviceConnectionError(f"Device is not connected: {device_id}")
        return managed.obd

    async def read_vin(self, device_id: str) -> str | None:
        return await self.connected_obd(device_id).read_vin()

    async def read_dtcs(self, device_id: str) -> list[str]:
        return await self.connected_obd(device_id).read_dtcs()

    async def read_live_data(self, device_id: str) -> dict[str, Any]:
        return await self.connected_obd(device_id).read_standard_live_data()

    async def shutdown(self) -> None:
        for device_id in list(self.connections):
            try:
                await self.disconnect(device_id)
            except Exception:
                pass
