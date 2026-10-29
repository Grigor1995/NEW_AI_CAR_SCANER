from uuid import uuid4

import pytest

from vehicle_diagnostic.service import VehicleDiagnosticService


@pytest.mark.asyncio
async def test_vehicle_diagnostic_simulator_lifecycle_trace_and_status():
    service = VehicleDiagnosticService()
    sid = uuid4()

    with pytest.raises(KeyError):
        service.status(sid)
    with pytest.raises(NotImplementedError, match="device-side"):
        await service.connect(sid, adapter="usb", request_id=0x7E0, response_id=0x7E8)

    connected = await service.connect(sid, adapter="simulator", request_id=0x7E0, response_id=0x7E8)
    assert connected.connected is True
    assert connected.can and connected.isotp and connected.uds and connected.dtc_read
    assert connected.dtc_clear is False
    assert connected.trace_events == 1

    again = await service.connect(sid, adapter="simulator", request_id=0x7E0, response_id=0x7E8)
    assert again.trace_events == 1

    identity = await service.identify_ecu(sid)
    assert identity.vin == "VINTEST1234567890"
    dtcs = await service.read_dtcs(sid)
    assert dtcs[0].code == "P0102"
    events = service.trace(sid)
    assert [event.event for event in events] == ["CONNECTED", "ECU_IDENTIFICATION", "DTC_READ"]
    assert events[-1].data["count"] == 1
    assert service.trace(sid, limit=0) == []


@pytest.mark.asyncio
async def test_vehicle_diagnostic_disconnected_operations_raise_and_can_reconnect():
    service = VehicleDiagnosticService()
    sid = uuid4()
    await service.connect(sid, adapter="simulator", request_id=0x7E0, response_id=0x7E8)
    status = await service.disconnect(sid)
    assert status.connected is False
    assert status.can is False
    with pytest.raises(RuntimeError, match="stopped"):
        await service.identify_ecu(sid)
    with pytest.raises(RuntimeError, match="stopped"):
        await service.read_dtcs(sid)

    reconnected = await service.connect(sid, adapter="simulator", request_id=0x7E0, response_id=0x7E8)
    assert reconnected.connected is True
    assert reconnected.trace_events == 1  # reconnect creates a fresh simulator runtime
