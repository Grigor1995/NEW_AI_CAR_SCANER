import asyncio
import sys
import types
from collections import deque

import pytest

from vehicle.obd.transport import TransportError
from vehicle.obd.adapters.ble import ObdBleTransport
from vehicle.obd.adapters.usb_serial import ObdUsbSerialTransport
from vehicle.obd.adapters.tcp_wifi import ObdWifiTransport
from vehicle.obd.adapters.simulator import SimulatorTransport


@pytest.mark.asyncio
async def test_simulator_fixed_responses_and_connection_lifecycle():
    transport = SimulatorTransport({"010C": "41 0C 1A F8"})
    assert not transport.connected
    await transport.connect()
    assert transport.connected
    await transport.write(b" 010c\r")
    assert transport.last_command == "010C"
    assert await transport.read_until() == b"41 0C 1A F8>"
    await transport.write(b"012F")
    assert await transport.read_until() == b"NO DATA>"
    await transport.disconnect()
    assert not transport.connected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("command", "prefix"),
    [("010C", "41 0C "), ("0105", "41 05 "), ("010D", "41 0D "), ("0111", "41 11 ")],
)
async def test_dynamic_simulator_emits_supported_pid_response(command, prefix):
    transport = SimulatorTransport(dynamic=True)
    await transport.connect()
    await transport.write(command.encode())
    response = await transport.read_until()
    assert response.startswith(prefix.encode())
    assert response.endswith(b">")
    assert transport._tick == 1


@pytest.mark.asyncio
async def test_dynamic_simulator_falls_back_for_unknown_pid():
    transport = SimulatorTransport({"012F": "41 2F 80"}, dynamic=True)
    await transport.connect()
    await transport.write(b"012F")
    assert await transport.read_until() == b"41 2F 80>"


class FakeBleakClient:
    def __init__(self, address):
        self.address = address
        self.is_connected = False
        self.notifications = []
        self.writes = []
        self.disconnected = False

    async def connect(self):
        self.is_connected = True

    async def start_notify(self, uuid, callback):
        self.notifications.append((uuid, callback))

    async def write_gatt_char(self, uuid, data, response=False):
        self.writes.append((uuid, data, response))

    async def disconnect(self):
        self.disconnected = True
        self.is_connected = False


@pytest.mark.asyncio
async def test_ble_connect_notify_write_read_and_disconnect(monkeypatch):
    fake_client = FakeBleakClient("AA:BB")
    monkeypatch.setitem(sys.modules, "bleak", types.SimpleNamespace(BleakClient=lambda address: fake_client))
    transport = ObdBleTransport("AA:BB", "tx", "rx")
    await transport.connect()
    assert transport.connected
    assert fake_client.notifications[0][0] == "rx"

    callback = fake_client.notifications[0][1]
    callback(None, bytearray(b"41 0C "))
    callback(None, bytearray(b"1A F8>EXTRA"))
    assert await transport.read_until() == b"41 0C 1A F8>"
    assert await transport.read_until(terminator=b"EXTRA", timeout=0.1) == b"EXTRA"

    await transport.write(b"010C")
    assert fake_client.writes == [("tx", b"010C", False)]
    await transport.disconnect()
    assert fake_client.disconnected
    assert not transport.connected


@pytest.mark.asyncio
async def test_ble_wraps_optional_dependency_or_connect_errors(monkeypatch):
    def fail_client(_address):
        raise RuntimeError("adapter unavailable")
    monkeypatch.setitem(sys.modules, "bleak", types.SimpleNamespace(BleakClient=fail_client))
    transport = ObdBleTransport("AA:BB", "tx", "rx")
    with pytest.raises(TransportError, match="adapter unavailable"):
        await transport.connect()


@pytest.mark.asyncio
async def test_ble_write_requires_connection_and_read_times_out():
    transport = ObdBleTransport("AA:BB", "tx", "rx")
    with pytest.raises(TransportError, match="not connected"):
        await transport.write(b"010C")
    with pytest.raises(TransportError, match="read timeout"):
        await transport.read_until(timeout=0.02)


class FakeSerial:
    def __init__(self, port, baudrate, timeout):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.is_open = True
        self.chunks = deque([b"4", b"1", b" ", b">"])
        self.writes = []
        self.closed = False

    def read(self, size):
        return self.chunks.popleft() if self.chunks else b""

    def write(self, data):
        self.writes.append(data)
        return len(data)

    def close(self):
        self.closed = True
        self.is_open = False


@pytest.mark.asyncio
async def test_usb_serial_connect_write_read_and_disconnect(monkeypatch):
    fake = FakeSerial("COM7", 38400, 0.1)
    monkeypatch.setitem(sys.modules, "serial", types.SimpleNamespace(Serial=lambda *args, **kwargs: fake))
    transport = ObdUsbSerialTransport("COM7", baudrate=38400)
    await transport.connect()
    assert transport.connected
    await transport.write(b"010C")
    assert fake.writes == [b"010C"]
    assert await transport.read_until(timeout=0.3) == b"41 >"
    await transport.disconnect()
    assert fake.closed
    assert not transport.connected


@pytest.mark.asyncio
async def test_usb_serial_wraps_connect_errors(monkeypatch):
    def fail_serial(*_args, **_kwargs):
        raise OSError("port is busy")
    monkeypatch.setitem(sys.modules, "serial", types.SimpleNamespace(Serial=fail_serial))
    transport = ObdUsbSerialTransport("COM7")
    with pytest.raises(TransportError, match="port is busy"):
        await transport.connect()


@pytest.mark.asyncio
async def test_usb_serial_unconnected_operations_fail():
    transport = ObdUsbSerialTransport("COM7")
    with pytest.raises(TransportError, match="not connected"):
        await transport.write(b"010C")
    with pytest.raises(TransportError, match="not connected"):
        await transport.read_until()


class FakeStreamReader:
    def __init__(self, result=b"41 0C>"):
        self.result = result
    async def readuntil(self, terminator):
        if isinstance(self.result, Exception):
            raise self.result
        assert self.result.endswith(terminator)
        return self.result


class FakeStreamWriter:
    def __init__(self):
        self.payloads = []
        self.closed = False
    def is_closing(self):
        return self.closed
    def write(self, data):
        self.payloads.append(data)
    async def drain(self):
        return None
    def close(self):
        self.closed = True
    async def wait_closed(self):
        return None


@pytest.mark.asyncio
async def test_wifi_connect_write_read_disconnect_and_connection_error(monkeypatch):
    reader, writer = FakeStreamReader(), FakeStreamWriter()
    async def open_connection(host, port):
        assert (host, port) == ("192.168.0.10", 35000)
        return reader, writer
    monkeypatch.setattr(asyncio, "open_connection", open_connection)
    transport = ObdWifiTransport("192.168.0.10")
    await transport.connect()
    assert transport.connected
    await transport.write(b"010C")
    assert writer.payloads == [b"010C"]
    assert await transport.read_until() == b"41 0C>"
    await transport.disconnect()
    assert not transport.connected

    async def fail_connection(*_args):
        raise OSError("connection refused")
    monkeypatch.setattr(asyncio, "open_connection", fail_connection)
    with pytest.raises(TransportError, match="connection refused"):
        await transport.connect()


@pytest.mark.asyncio
async def test_wifi_unconnected_write_and_read_fail():
    transport = ObdWifiTransport("127.0.0.1")
    with pytest.raises(TransportError, match="not connected"):
        await transport.write(b"010C")
    with pytest.raises(TransportError, match="not connected"):
        await transport.read_until()


@pytest.mark.asyncio
async def test_wifi_read_timeout_and_incomplete_stream_are_wrapped():
    reader = FakeStreamReader(asyncio.IncompleteReadError(partial=b"41", expected=4))
    transport = ObdWifiTransport("127.0.0.1")
    transport._reader = reader
    with pytest.raises(TransportError):
        await transport.read_until()

    async def never_finishes(_terminator):
        await asyncio.sleep(1)
    transport._reader = types.SimpleNamespace(readuntil=never_finishes)
    with pytest.raises(TransportError):
        await transport.read_until(timeout=0.01)
