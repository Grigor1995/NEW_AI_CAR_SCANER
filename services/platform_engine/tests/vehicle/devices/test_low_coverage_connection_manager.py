import asyncio
import sys
import types

import pytest

import vehicle.devices.connection as connection
from vehicle.devices.connection import DeviceConnectionError, VCIConnectionManager
from vehicle.devices.models import DeviceCapabilities, DeviceDescriptor, DeviceStatus


def descriptor(kind, *, metadata=None, device_id="test-device"):
    return DeviceDescriptor(
        device_id=device_id,
        manufacturer="Test",
        model="VCI",
        connection_type=kind,
        capabilities=DeviceCapabilities(obd=True),
        metadata=metadata or {},
    )


def test_scan_normalizes_transport_and_rejects_automatic_wifi_discovery():
    manager = VCIConnectionManager()
    with pytest.raises(DeviceConnectionError, match="not automatic"):
        asyncio.run(manager.scan(" WiFi "))


def test_ble_scan_registers_metadata_and_clamps_timeout(monkeypatch):
    seen = {}
    class FakeScanner:
        @staticmethod
        async def discover(timeout):
            seen["timeout"] = timeout
            return [
                types.SimpleNamespace(
                    address="AA:BB:CC",
                    name="BLE VCI",
                    rssi=-42,
                    metadata={"manufacturer": "test"},
                ),
                types.SimpleNamespace(address="DD:EE:FF", name=None),
            ]
    monkeypatch.setitem(sys.modules, "bleak", types.SimpleNamespace(BleakScanner=FakeScanner))
    manager = VCIConnectionManager()

    found = asyncio.run(manager.scan("ble", timeout=90))

    assert seen["timeout"] == 30.0
    assert len(found) == 2
    assert found[0].device_id == "ble:AA:BB:CC"
    assert found[0].metadata["rssi"] == -42
    assert found[0].metadata["details"] == {"manufacturer": "test"}
    assert found[1].model == "BLE VCI"
    assert manager.devices[found[0].device_id] is found[0]


def test_ble_scan_reports_missing_optional_dependency(monkeypatch):
    monkeypatch.setitem(sys.modules, "bleak", None)
    with pytest.raises(DeviceConnectionError, match="bleak is required"):
        asyncio.run(VCIConnectionManager().scan("ble"))


def test_usb_scan_registers_discovered_serial_ports(monkeypatch):
    port = types.SimpleNamespace(
        device="COM7",
        manufacturer=" Manufacturer ",
        product=" Product ",
        description="fallback",
        serial_number="serial-1",
        vid=123,
        pid=456,
        hwid="USB VID:PID",
    )
    serial = types.ModuleType("serial")
    serial.__path__ = []
    tools = types.ModuleType("serial.tools")
    tools.__path__ = []
    list_ports = types.ModuleType("serial.tools.list_ports")
    list_ports.comports = lambda: [port]
    monkeypatch.setitem(sys.modules, "serial", serial)
    monkeypatch.setitem(sys.modules, "serial.tools", tools)
    monkeypatch.setitem(sys.modules, "serial.tools.list_ports", list_ports)

    manager = VCIConnectionManager()
    found = asyncio.run(manager.scan("usb"))

    assert len(found) == 1
    assert found[0].device_id == "usb:COM7"
    assert found[0].manufacturer == "Manufacturer"
    assert found[0].model == "Product"
    assert found[0].metadata["serial_number"] == "serial-1"
    assert found[0].capabilities.usb
    assert manager.devices["usb:COM7"] is found[0]


def test_usb_scan_reports_missing_optional_dependency(monkeypatch):
    monkeypatch.setitem(sys.modules, "serial", None)
    with pytest.raises(DeviceConnectionError, match="pyserial is required"):
        asyncio.run(VCIConnectionManager().scan("usb"))


@pytest.mark.asyncio
async def test_probe_wifi_requires_host_and_registers_successful_probe(monkeypatch):
    manager = VCIConnectionManager()
    with pytest.raises(DeviceConnectionError, match="host is required"):
        await manager.probe_wifi("  ")

    class FakeWriter:
        def __init__(self):
            self.closed = False
        def close(self):
            self.closed = True
        async def wait_closed(self):
            return None

    writer = FakeWriter()
    async def open_connection(host, port):
        assert (host, port) == ("192.168.0.20", 35000)
        return object(), writer
    monkeypatch.setattr(connection.asyncio, "open_connection", open_connection)

    result = await manager.probe_wifi(" 192.168.0.20 ")
    assert result.device_id == "wifi:192.168.0.20:35000"
    assert result.metadata == {"host": "192.168.0.20", "port": 35000}
    assert writer.closed


@pytest.mark.asyncio
async def test_probe_wifi_wraps_connection_failures(monkeypatch):
    async def fail(*_args, **_kwargs):
        raise OSError("connection refused")
    monkeypatch.setattr(connection.asyncio, "open_connection", fail)
    with pytest.raises(DeviceConnectionError, match="Wi-Fi probe failed.*connection refused"):
        await VCIConnectionManager().probe_wifi("192.168.0.20")


def test_transport_factory_validates_usb_ble_and_unknown_types():
    manager = VCIConnectionManager()
    with pytest.raises(DeviceConnectionError, match="USB serial port is required"):
        manager._transport_for(descriptor("USB"), {})
    with pytest.raises(DeviceConnectionError, match="TX UUID and RX UUID are required"):
        manager._transport_for(descriptor("BLE", metadata={"address": "AA:BB"}), {})
    with pytest.raises(DeviceConnectionError, match="Unsupported device connection type"):
        manager._transport_for(descriptor("CAN"), {})


def test_transport_factory_uses_descriptor_defaults():
    manager = VCIConnectionManager()
    usb = manager._transport_for(descriptor("USB", metadata={"port": "COM8"}), {})
    assert usb.port == "COM8"
    wifi = manager._transport_for(descriptor("WIFI", metadata={"host": "192.168.0.30", "port": 35001}), {})
    assert wifi.host == "192.168.0.30"
    assert wifi.port == 35001
    ble = manager._transport_for(
        descriptor("BLE", metadata={"address": "AA:BB"}),
        {"tx_uuid": "tx", "rx_uuid": "rx"},
    )
    assert ble.address == "AA:BB"
    assert ble.tx_uuid == "tx"
    assert ble.rx_uuid == "rx"


@pytest.mark.asyncio
async def test_connect_failure_updates_descriptor_status_and_last_error():
    manager = VCIConnectionManager()
    device = descriptor("USB", metadata={"port": ""})
    manager._register(device)

    with pytest.raises(DeviceConnectionError, match="USB serial port is required"):
        await manager.connect(device.device_id)

    assert device.status == DeviceStatus.ERROR
    assert "USB serial port is required" in device.metadata["last_error"]
    assert device.device_id not in manager.connections


@pytest.mark.asyncio
async def test_connection_status_reconnect_and_connected_obd_lifecycle():
    manager = VCIConnectionManager()
    device = manager.add_simulator()

    connected = await manager.connect(device.device_id)
    assert connected.status == DeviceStatus.CONNECTED
    assert manager.connected_obd(device.device_id) is manager.connections[device.device_id].obd
    assert manager.status(device.device_id).status == DeviceStatus.CONNECTED

    await manager.connections[device.device_id].transport.disconnect()
    assert manager.status(device.device_id).status == DeviceStatus.ERROR

    reconnected = await manager.reconnect(device.device_id)
    assert reconnected.status == DeviceStatus.CONNECTED
    disconnected = await manager.disconnect(device.device_id)
    assert disconnected.status == DeviceStatus.DISCONNECTED
    assert device.device_id not in manager.connections


def test_unknown_device_and_not_connected_obd_raise_clear_errors():
    manager = VCIConnectionManager()
    with pytest.raises(DeviceConnectionError, match="Unknown device"):
        manager.status("missing")
    with pytest.raises(DeviceConnectionError, match="Unknown device"):
        asyncio.run(manager.disconnect("missing"))
    with pytest.raises(DeviceConnectionError, match="Unknown device"):
        asyncio.run(manager.reconnect("missing"))
    with pytest.raises(DeviceConnectionError, match="Device is not connected"):
        manager.connected_obd("missing")
    with pytest.raises(DeviceConnectionError, match="Device is not connected"):
        asyncio.run(manager.read_vin("missing"))
