from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from vehicle.acquisition.models import AcquisitionSourceType
from vehicle.acquisition.sources import CanStreamSource, ObdPollingSource, UdsDidPollingSource
from vehicle.can.models import CanFrame


class FakeObdClient:
    def __init__(self):
        self.connected = False
        self.disconnected = False
        self.protocol = SimpleNamespace(
            rpm=lambda raw: raw[0] * 100.0,
            coolant_c=lambda raw: raw[0] - 40.0,
            speed_kmh=lambda raw: raw[0],
            throttle_percent=lambda raw: raw[0] / 2.0,
        )

    async def connect(self):
        self.connected = True

    async def disconnect(self):
        self.disconnected = True

    async def read_pid(self, pid):
        if pid == 0x05:
            raise OSError("PID unavailable")
        if pid == 0x99:
            return "NO DATA"
        return bytes([12])


@pytest.mark.asyncio
async def test_obd_source_connect_read_success_unknown_pid_and_error():
    client = FakeObdClient()
    source = ObdPollingSource(client, pids=[0x0C, 0x99, 0x05])
    session_id = uuid4()

    await source.connect()
    records = await source.read_once(session_id, 7)
    await source.disconnect()

    assert client.connected is True and client.disconnected is True
    assert [record.sequence for record in records] == [7, 7, 7]
    assert records[0].source_type is AcquisitionSourceType.OBD_PID
    assert records[0].channel == "rpm"
    assert records[0].numeric_value == 1200.0
    assert records[0].raw == bytes([12])
    assert records[0].unit == "rpm"
    assert records[1].channel == "pid_0x99"
    assert records[1].numeric_value is None
    assert records[1].raw is None
    assert records[2].quality == "INVALID"
    assert records[2].metadata["error"] == "PID unavailable"


@pytest.mark.asyncio
async def test_obd_source_defaults_and_known_pid_units():
    client = FakeObdClient()
    source = ObdPollingSource(client)
    assert source.pids == [0x0C, 0x05, 0x0D, 0x11]
    records = await source.read_once(uuid4(), 1)
    by_channel = {record.channel: record for record in records}
    assert by_channel["coolant_c"].numeric_value is None  # fake client errors for PID 05
    assert by_channel["speed_kmh"].unit == "km/h"
    assert by_channel["throttle_percent"].unit == "%"


class FakeBus:
    def __init__(self, frames):
        self.frames = iter(frames)
        self.timeouts = []

    async def receive(self, timeout_ms):
        self.timeouts.append(timeout_ms)
        return next(self.frames)


@pytest.mark.asyncio
async def test_can_source_returns_no_record_on_timeout_and_maps_frame_metadata():
    frame = CanFrame(arbitration_id=0x7E8, data=b"\x03\x41\x0C", timestamp_ns=None, is_extended=False)
    bus = FakeBus([None, frame])
    source = CanStreamSource(bus, timeout_ms=55)

    await source.connect()
    assert await source.read_once(uuid4(), 1) == []
    session_id = uuid4()
    records = await source.read_once(session_id, 2)
    await source.disconnect()

    assert bus.timeouts == [55, 55]
    assert len(records) == 1
    record = records[0]
    assert record.session_id == session_id
    assert record.source_type is AcquisitionSourceType.CAN_FRAME
    assert record.channel == "can:0x7E8"
    assert record.raw == b"\x03\x41\x0C"
    assert record.sequence == 2
    assert record.timestamp_ns > 0
    assert record.metadata == {"arbitration_id": 0x7E8, "dlc": 3, "is_extended": False, "is_fd": False}


class FakeUdsClient:
    async def read_data_by_identifier(self, did):
        if did == 0x1003:
            raise TimeoutError("ECU timed out")
        return bytes([did & 0xFF, 7])


@pytest.mark.asyncio
async def test_uds_source_decodes_known_did_keeps_raw_unknown_and_captures_errors():
    source = UdsDidPollingSource(
        FakeUdsClient(),
        [0x1001, 0x1002, 0x1003],
        decoders={0x1001: lambda payload: payload[0] * 2},
    )
    session_id = uuid4()

    records = await source.read_once(session_id, 11)

    assert len(records) == 3
    assert records[0].channel == "uds:0x1001"
    assert records[0].numeric_value == 2.0
    assert records[0].raw == bytes([1, 7])
    assert records[0].metadata["did"] == 0x1001
    assert records[1].numeric_value is None
    assert records[1].raw == bytes([2, 7])
    assert records[1].quality == "GOOD"
    assert records[2].quality == "INVALID"
    assert records[2].raw is None
    assert records[2].metadata["error"] == "ECU timed out"
