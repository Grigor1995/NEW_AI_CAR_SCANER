from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from vehicle.acquisition.manager import AcquisitionManager
from vehicle.acquisition.models import AcquisitionRecord, AcquisitionSourceType, AcquisitionState, ReconnectPolicy
from vehicle.acquisition.offline_queue import OfflineQueue


class FakeSource:
    def __init__(self, *, connect_failures=0, read_failures=0):
        self.connect_failures = connect_failures
        self.read_failures = read_failures
        self.connect_calls = 0
        self.disconnect_calls = 0
        self.read_calls = 0

    async def connect(self):
        self.connect_calls += 1
        if self.connect_calls <= self.connect_failures:
            raise OSError("connect failed")

    async def disconnect(self):
        self.disconnect_calls += 1

    async def read_once(self, session_id, sequence):
        self.read_calls += 1
        if self.read_calls <= self.read_failures:
            raise RuntimeError("read failed")
        return [AcquisitionRecord(
            session_id=session_id, source_type=AcquisitionSourceType.OBD_PID,
            channel="rpm", numeric_value=750.0, unit="rpm", sequence=sequence,
            raw=b"\x02\xee",
        )]


def _policy(attempts=2):
    return ReconnectPolicy(max_attempts=attempts, initial_backoff_s=0.001, max_backoff_s=0.005)


@pytest.mark.asyncio
async def test_manager_retries_connect_delivers_records_and_stops_cleanly():
    sid = uuid4()
    source = FakeSource(connect_failures=1)
    delivered = []
    async def sink(records):
        delivered.extend(records)

    manager = AcquisitionManager(
        source, session_id=sid, poll_interval_s=0.005,
        reconnect_policy=_policy(), sink=sink,
    )
    await manager.start()
    await asyncio.sleep(0.025)
    await manager.stop()

    assert source.connect_calls >= 2
    assert source.disconnect_calls == 1
    assert manager.state is AcquisitionState.STOPPED
    assert manager.stats["records"] >= 1
    assert delivered
    assert all(item.session_id == sid for item in manager.snapshot(2))
    assert manager.snapshot(0) == []
    with pytest.raises(ValueError, match="limit"):
        manager.snapshot(-1)


@pytest.mark.asyncio
async def test_manager_connection_failure_sets_error_state():
    manager = AcquisitionManager(
        FakeSource(connect_failures=99), session_id=uuid4(),
        reconnect_policy=_policy(attempts=2),
    )
    with pytest.raises(ConnectionError, match="connect failed"):
        await manager.start()
    assert manager.state is AcquisitionState.ERROR
    assert manager.stats["errors"] == 2


@pytest.mark.asyncio
async def test_manager_reconnects_after_read_error_and_queues_when_sink_fails(tmp_path):
    source = FakeSource(read_failures=1)
    queue = OfflineQueue(tmp_path / "offline.jsonl", max_items=4)
    def failed_sink(_records):
        raise OSError("network unavailable")

    manager = AcquisitionManager(
        source, session_id=uuid4(), poll_interval_s=0.005,
        reconnect_policy=_policy(), offline_queue=queue, sink=failed_sink,
    )
    await manager.start()
    await asyncio.sleep(0.035)
    await manager.stop()

    assert manager.stats["reconnects"] >= 1
    assert manager.stats["queued_offline"] >= 1
    assert queue.size() >= 1
    first = queue.peek(1)[0]
    assert first["channel"] == "rpm"
    assert first["raw_hex"] == "02ee"
    assert first["source_type"] == "OBD_PID"


@pytest.mark.asyncio
async def test_manager_rejects_nonpositive_poll_interval_and_start_is_idempotent():
    with pytest.raises(ValueError, match="poll_interval_s"):
        AcquisitionManager(FakeSource(), session_id=uuid4(), poll_interval_s=0)

    source = FakeSource()
    manager = AcquisitionManager(source, session_id=uuid4(), poll_interval_s=0.01)
    await manager.start()
    await manager.start()
    assert source.connect_calls == 1
    await manager.stop()
