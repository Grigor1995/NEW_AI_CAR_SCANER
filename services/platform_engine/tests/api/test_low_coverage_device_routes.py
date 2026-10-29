
import pytest
from fastapi import HTTPException

import api.device_routes as routes
from device.manager import DeviceCapabilities, DeviceStatus


def make_device(device_id="vci-1", status=None):
    return routes.DeviceDescriptor(
        device_id=device_id,
        manufacturer="Test Vendor",
        model="Test VCI",
        firmware_version="1.2",
        protocol="OBD/CAN",
        connection_type="simulator",
        capabilities=DeviceCapabilities(obd=True, can=True, uds=False),
        status=status or DeviceStatus.DISCONNECTED,
        metadata={"fixture": True},
    )


class FakeManager:
    def __init__(self):
        self.devices = {"vci-1": make_device()}
        self.result = make_device()
        self.error = None
        self.calls = []

    def _call(self, name, *args):
        self.calls.append((name, args))
        if self.error:
            raise self.error
        return self.result

    def add_simulator(self):
        return self._call("add_simulator")

    async def scan(self, *args):
        return self._call("scan", *args)

    async def probe_wifi(self, *args):
        return self._call("probe_wifi", *args)

    async def connect(self, *args):
        return self._call("connect", *args)

    async def reconnect(self, *args):
        return self._call("reconnect", *args)

    async def disconnect(self, *args):
        return self._call("disconnect", *args)

    def status(self, *args):
        return self._call("status", *args)

    async def read_vin(self, *args):
        return self._call("read_vin", *args)

    async def read_dtcs(self, *args):
        return self._call("read_dtcs", *args)

    async def read_live_data(self, *args):
        return self._call("read_live_data", *args)


def test_json_serializes_device_descriptor_fields():
    payload = routes._json(make_device())
    assert payload == {
        "device_id": "vci-1",
        "manufacturer": "Test Vendor",
        "model": "Test VCI",
        "firmware_version": "1.2",
        "protocol": "OBD/CAN",
        "connection_type": "simulator",
        "capabilities": {"obd": True, "can": True, "uds": False},
        "status": "disconnected",
        "metadata": {"fixture": True},
    }


def test_list_devices_serializes_all_registered_devices(monkeypatch):
    manager = FakeManager()
    monkeypatch.setattr(routes, "manager", manager)
    result = routes.list_devices()
    assert [row["device_id"] for row in result["devices"]] == ["vci-1"]


@pytest.mark.asyncio
async def test_scan_devices_returns_lowercase_transport_and_serialized_devices(monkeypatch):
    manager = FakeManager()
    manager.result = [make_device("scan-1")]
    monkeypatch.setattr(routes, "manager", manager)
    result = await routes.scan_devices("SIMULATOR", routes.ScanRequest(timeout=1.2))
    assert result == {"transport": "simulator", "devices": [routes._json(make_device("scan-1"))]}
    assert manager.calls == [("scan", ("SIMULATOR", 1.2))]


@pytest.mark.asyncio
async def test_scan_devices_maps_device_connection_error_to_501(monkeypatch):
    manager = FakeManager()
    manager.error = routes.DeviceConnectionError("transport unsupported")
    monkeypatch.setattr(routes, "manager", manager)
    with pytest.raises(HTTPException) as error:
        await routes.scan_devices("usb", routes.ScanRequest())
    assert error.value.status_code == 501
    assert error.value.detail == "transport unsupported"


@pytest.mark.asyncio
async def test_scan_devices_maps_unexpected_error_to_502(monkeypatch):
    manager = FakeManager()
    manager.error = RuntimeError("scanner crashed")
    monkeypatch.setattr(routes, "manager", manager)
    with pytest.raises(HTTPException) as error:
        await routes.scan_devices("simulator", routes.ScanRequest())
    assert error.value.status_code == 502
    assert "Device scan failed" in error.value.detail


@pytest.mark.asyncio
async def test_wifi_probe_serializes_device_and_maps_connection_error(monkeypatch):
    manager = FakeManager()
    monkeypatch.setattr(routes, "manager", manager)
    result = await routes.wifi_probe(routes.WifiProbeRequest(host="192.0.2.3", port=35000, timeout=1.0))
    assert result["device_id"] == "vci-1"
    assert manager.calls == [("probe_wifi", ("192.0.2.3", 35000, 1.0))]

    manager.error = routes.DeviceConnectionError("Wi-Fi probe unavailable")
    with pytest.raises(HTTPException) as error:
        await routes.wifi_probe(routes.WifiProbeRequest(host="192.0.2.3"))
    assert error.value.status_code == 502


def test_add_simulator_returns_serialized_device(monkeypatch):
    manager = FakeManager()
    monkeypatch.setattr(routes, "manager", manager)
    result = routes.add_simulator()
    assert result["device_id"] == "vci-1"
    assert manager.calls == [("add_simulator", ())]


@pytest.mark.asyncio
async def test_connect_device_passes_config_and_maps_conflict(monkeypatch):
    manager = FakeManager()
    monkeypatch.setattr(routes, "manager", manager)
    result = await routes.connect_device("vci-1", routes.DeviceConnectRequest(config={"baud": 500000}))
    assert result["status"] == "disconnected"
    assert manager.calls == [("connect", ("vci-1", {"baud": 500000}))]

    manager.error = routes.DeviceConnectionError("device busy")
    with pytest.raises(HTTPException) as error:
        await routes.connect_device("vci-1", routes.DeviceConnectRequest())
    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_reconnect_device_maps_missing_device_to_conflict(monkeypatch):
    manager = FakeManager()
    monkeypatch.setattr(routes, "manager", manager)
    assert (await routes.reconnect_device("vci-1"))["device_id"] == "vci-1"
    assert manager.calls == [("reconnect", ("vci-1",))]
    manager.error = routes.DeviceConnectionError("not found")
    with pytest.raises(HTTPException) as error:
        await routes.reconnect_device("missing")
    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_disconnect_device_maps_missing_device_to_404(monkeypatch):
    manager = FakeManager()
    monkeypatch.setattr(routes, "manager", manager)
    assert (await routes.disconnect_device("vci-1"))["device_id"] == "vci-1"
    manager.error = routes.DeviceConnectionError("Device not found")
    with pytest.raises(HTTPException) as error:
        await routes.disconnect_device("missing")
    assert error.value.status_code == 404


def test_device_status_maps_missing_device_to_404(monkeypatch):
    manager = FakeManager()
    monkeypatch.setattr(routes, "manager", manager)
    assert routes.device_status("vci-1")["device_id"] == "vci-1"
    manager.error = routes.DeviceConnectionError("Device not found")
    with pytest.raises(HTTPException) as error:
        routes.device_status("missing")
    assert error.value.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("handler", "name", "args", "key", "value"),
    [
        (routes.read_vin, "read_vin", ("vci-1",), "vin", "WDD2110801A123456"),
        (routes.read_dtcs, "read_dtcs", ("vci-1",), "dtcs", ["P0102"]),
        (routes.read_live_data, "read_live_data", ("vci-1",), "values", {"rpm": 1696.0}),
    ],
)
async def test_obd_read_routes_include_device_id(monkeypatch, handler, name, args, key, value):
    manager = FakeManager()
    manager.result = value
    monkeypatch.setattr(routes, "manager", manager)
    result = await handler(*args)
    assert result == {"device_id": "vci-1", key: value}
    assert manager.calls == [(name, args)]


@pytest.mark.asyncio
@pytest.mark.parametrize("handler", [routes.read_vin, routes.read_dtcs, routes.read_live_data])
async def test_obd_read_routes_map_connection_errors_to_409(monkeypatch, handler):
    manager = FakeManager()
    manager.error = routes.DeviceConnectionError("device disconnected")
    monkeypatch.setattr(routes, "manager", manager)
    with pytest.raises(HTTPException) as error:
        await handler("vci-1")
    assert error.value.status_code == 409


@pytest.mark.asyncio
@pytest.mark.parametrize('facade', [False, True])
async def test_protocol_observation_handles_both_backend_manager_shapes(monkeypatch, facade):
    from types import SimpleNamespace
    seen = []

    async def command(value):
        seen.append(value)
        return {'ATSP0': 'OK', '0100': '41 00 BE 1F A8 13', 'ATDPN': 'A6'}[value]

    physical = SimpleNamespace(connected_obd=lambda device_id: SimpleNamespace(command=command))
    manager = SimpleNamespace(_physical=lambda: physical) if facade else physical
    monkeypatch.setattr(routes, 'manager', manager)
    result = await routes.read_device_obd_protocol('wifi:127.0.0.1:35000')
    assert result['confirmed_ecu_communication'] is True
    assert result['simulated'] is False
    assert result['protocol_id'] == 'iso15765_4_can11_500'
    assert seen == ['ATSP0', '0100', 'ATDPN']


@pytest.mark.asyncio
async def test_protocol_simulator_is_never_reported_as_physical_observation(monkeypatch):
    monkeypatch.setattr(routes, 'manager', object())
    result = await routes.read_device_obd_protocol('simulator-vci')
    assert result['simulated'] is True
    assert result['observed'] is False
    assert result['confirmed_ecu_communication'] is False
    assert result['protocol_id'] is None


@pytest.mark.asyncio
async def test_protocol_connection_failure_is_public_conflict(monkeypatch):
    from types import SimpleNamespace

    def missing(_device_id):
        raise RuntimeError('Adapter is disconnected')

    monkeypatch.setattr(routes, 'manager', SimpleNamespace(connected_obd=missing))
    with pytest.raises(HTTPException) as error:
        await routes.read_device_obd_protocol('usb:COM9')
    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_discovery_simulator_is_explicit_and_never_returns_fake_ecus(monkeypatch):
    manager = FakeManager()
    monkeypatch.setattr(routes, 'manager', manager)
    result = await routes.diagnostic_discovery('vci-1', routes.DeviceConnectRequest())
    assert result['simulated'] is True
    assert result['vin'] is None
    assert result['modules'] == []
    assert manager.calls[-1][0] == 'connect'


@pytest.mark.asyncio
async def test_discovery_real_device_collects_readonly_replies_under_client_lock(monkeypatch):
    import asyncio
    from types import SimpleNamespace
    manager = FakeManager()
    manager.result.connection_type = 'USB'
    calls = []
    async def command(step):
        assert client._lock.locked()
        calls.append(step)
        return '7E8 06 41 00 BE 3E B8 13' if step == '0100' else 'NO DATA'
    client = SimpleNamespace(_lock=asyncio.Lock(), _command_unlocked=command)
    manager.connected_obd = lambda device_id: client
    monkeypatch.setattr(routes, 'manager', manager)
    result = await routes.diagnostic_discovery('vci-1', routes.DeviceConnectRequest())
    assert calls == ['0902','ATH1','0100','ATDPN','ATH0']
    assert result['modules'][0]['address'] == '7E8'
    assert result['identification_status'] == 'vin_unavailable'
    assert not client._lock.locked()
