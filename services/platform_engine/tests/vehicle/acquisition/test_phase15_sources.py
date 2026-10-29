import asyncio
import pytest
from uuid import uuid4
from vehicle.acquisition.factory import build_obd_transport
from vehicle.acquisition.models import AcquisitionSourceType, ReconnectPolicy
from vehicle.acquisition.manager import AcquisitionManager
from vehicle.acquisition.sources import CanStreamSource
from vehicle.can.models import CanFrame
from vehicle.adapters.can_simulator import SimulatedCanBus


def test_build_physical_obd_transports():
    from vehicle.obd.adapters.ble import ObdBleTransport
    from vehicle.obd.adapters.tcp_wifi import ObdWifiTransport
    from vehicle.obd.adapters.usb_serial import ObdUsbSerialTransport
    assert isinstance(build_obd_transport('ble', {'address':'AA:BB','tx_uuid':'tx','rx_uuid':'rx'}), ObdBleTransport)
    assert isinstance(build_obd_transport('wifi', {'host':'127.0.0.1'}), ObdWifiTransport)
    assert isinstance(build_obd_transport('usb', {'port':'COM1'}), ObdUsbSerialTransport)
    with pytest.raises(ValueError): build_obd_transport('unknown', {})

@pytest.mark.asyncio
async def test_can_stream_source():
    bus=SimulatedCanBus()
    bus.inject(CanFrame(0x123, b'\x01\x02', timestamp_ns=2_000_000))
    records=await CanStreamSource(bus).read_once(uuid4(), 7)
    assert len(records)==1
    assert records[0].source_type == AcquisitionSourceType.CAN_FRAME
    assert records[0].channel == 'can:0x123'
    assert records[0].raw == b'\x01\x02'

class FlakySource:
    async def connect(self): pass
    async def disconnect(self): pass
    async def read_once(self, session_id, sequence):
        if sequence == 0: raise ConnectionError('drop')
        from vehicle.acquisition.models import AcquisitionRecord
        return [AcquisitionRecord(session_id=session_id, channel='test', numeric_value=1.0, sequence=sequence)]

@pytest.mark.asyncio
async def test_manager_reconnects_after_read_failure():
    manager=AcquisitionManager(FlakySource(), session_id=uuid4(), poll_interval_s=0.01, reconnect_policy=ReconnectPolicy(max_attempts=2, initial_backoff_s=0.001, max_backoff_s=0.002))
    await manager.start(); await asyncio.sleep(0.05); await manager.stop()
    assert manager.stats['reconnects'] >= 1
    assert manager.stats['records'] >= 1
