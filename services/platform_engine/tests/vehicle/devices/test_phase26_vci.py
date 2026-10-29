from __future__ import annotations

import asyncio

from vehicle.devices.connection import VCIConnectionManager
from vehicle.devices.models import DeviceStatus


def test_simulator_device_connects_and_reads_obd_values():
    manager = VCIConnectionManager()
    descriptor = manager.add_simulator()

    async def scenario():
        connected = await manager.connect(descriptor.device_id)
        vin = await manager.read_vin(descriptor.device_id)
        dtcs = await manager.read_dtcs(descriptor.device_id)
        live = await manager.read_live_data(descriptor.device_id)
        connected_status = connected.status
        await manager.disconnect(descriptor.device_id)
        return connected_status, vin, dtcs, live

    connected_status, vin, dtcs, live = asyncio.run(scenario())
    assert connected_status == DeviceStatus.CONNECTED
    assert vin == "WDD2110801A123456"
    assert dtcs == ["P0102"]
    assert live["rpm"] == 1696.0
    assert live["coolant_c"] == 50.0
    assert live["speed_kmh"] == 40.0
    assert live["throttle_percent"] > 49.0


def test_wifi_probe_requires_host_and_does_not_claim_discovery_without_endpoint():
    manager = VCIConnectionManager()
    try:
        asyncio.run(manager.scan("wifi"))
    except Exception as exc:
        assert "Generic Wi-Fi discovery" in str(exc)
    else:
        raise AssertionError("Generic Wi-Fi discovery should require an explicit endpoint")
