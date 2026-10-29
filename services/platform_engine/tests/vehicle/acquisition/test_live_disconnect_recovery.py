import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest

from vehicle.acquisition.manager import AcquisitionManager
from vehicle.acquisition.models import AcquisitionState
from vehicle.acquisition.sources import ObdPollingSource
from vehicle.obd.protocols.elm327 import ELM327Protocol


class DroppingClient:
    def __init__(self):
        self.transport = SimpleNamespace(connected=False)
        self.protocol = ELM327Protocol()
        self.reads = 0
        self.connects = 0

    async def connect(self):
        self.connects += 1
        self.transport.connected = True

    async def disconnect(self):
        self.transport.connected = False

    async def read_pid(self, pid):
        self.reads += 1
        if self.reads == 1:
            self.transport.connected = False
            raise ConnectionError("adapter unplugged")
        return b"\x1f\x40"


@pytest.mark.asyncio
async def test_transport_disconnect_reaches_manager_and_recovers_readings():
    client = DroppingClient()
    delivered = asyncio.Event()
    manager = AcquisitionManager(ObdPollingSource(client, [0x0C]), session_id=uuid4(),
                                 poll_interval_s=0.001, sink=lambda rows: delivered.set())
    try:
        await manager.start()
        await asyncio.wait_for(delivered.wait(), timeout=1)
        assert manager.stats["reconnects"] == 1
        assert client.connects == 2
        assert manager.snapshot()[-1].numeric_value == 2000
        assert manager.snapshot()[-1].quality != "INVALID"
    finally:
        await manager.stop()
    assert not client.transport.connected
    assert manager.state == AcquisitionState.STOPPED


@pytest.mark.asyncio
async def test_stop_cancels_a_blocked_read_and_closes_the_adapter():
    class BlockedSource:
        def __init__(self):
            self.reading = asyncio.Event()
            self.closed = False

        async def connect(self):
            pass

        async def read_once(self, session_id, sequence):
            self.reading.set()
            await asyncio.Event().wait()

        async def disconnect(self):
            self.closed = True

    source = BlockedSource()
    manager = AcquisitionManager(source, session_id=uuid4())
    await manager.start()
    await asyncio.wait_for(source.reading.wait(), timeout=1)
    await asyncio.wait_for(manager.stop(), timeout=0.5)
    assert source.closed
    assert manager.state == AcquisitionState.STOPPED


@pytest.mark.asyncio
async def test_unsupported_pid_does_not_trigger_a_transport_reconnect():
    client = DroppingClient()
    async def unsupported(pid):
        raise ValueError("NO DATA")
    client.read_pid = unsupported
    source = ObdPollingSource(client, [0x0C])
    await source.connect()
    try:
        rows = await source.read_once(uuid4(), 0)
        assert rows[0].quality == "INVALID"
        assert client.transport.connected
        assert client.connects == 1
    finally:
        await source.disconnect()
