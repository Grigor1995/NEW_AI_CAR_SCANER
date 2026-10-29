import asyncio
import pytest
from uuid import uuid4
from vehicle.acquisition.manager import AcquisitionManager
from vehicle.acquisition.offline_queue import OfflineQueue
from vehicle.acquisition.sources import ObdPollingSource
from vehicle.obd.client import GenericObdClient
from vehicle.obd.adapters.simulator import SimulatorTransport

@pytest.fixture
def responses():
    return {'0100':'41 00 08 18 80 00','ATZ':'ELM327 v2.2','ATE0':'OK','ATL0':'OK','ATS0':'OK','ATSP0':'OK','010C':'41 0C 0B B8','0105':'41 05 5A','010D':'41 0D 28','0111':'41 11 80'}

@pytest.mark.asyncio
async def test_obd_polling_source(responses):
    source=ObdPollingSource(GenericObdClient(SimulatorTransport(responses)))
    await source.connect()
    records=await source.read_once(uuid4(),0)
    await source.disconnect()
    assert {r.channel for r in records} == {'rpm','coolant_c','speed_kmh','throttle_percent'}
    assert next(r.numeric_value for r in records if r.channel=='rpm') == 750.0

@pytest.mark.asyncio
async def test_manager_buffers_and_stops(responses):
    sink=[]
    async def collect(records): sink.extend(records)
    source=ObdPollingSource(GenericObdClient(SimulatorTransport(responses)), [0x0C])
    manager=AcquisitionManager(source, session_id=uuid4(), poll_interval_s=0.02, sink=collect)
    await manager.start()
    await asyncio.sleep(0.09)
    await manager.stop()
    assert manager.state.value == 'STOPPED'
    assert manager.stats['records'] >= 2
    assert sink

@pytest.mark.asyncio
async def test_sink_failure_goes_to_offline_queue(responses,tmp_path):
    async def failing_sink(_): raise RuntimeError('network down')
    queue=OfflineQueue(tmp_path/'queue.jsonl')
    source=ObdPollingSource(GenericObdClient(SimulatorTransport(responses)), [0x0C])
    manager=AcquisitionManager(source, session_id=uuid4(), poll_interval_s=0.02, sink=failing_sink, offline_queue=queue)
    await manager.start(); await asyncio.sleep(0.06); await manager.stop()
    assert queue.size() >= 1
    item=queue.peek(1)[0]
    assert item['source_type']=='OBD_PID'

@pytest.mark.asyncio
async def test_offline_queue_ack(tmp_path):
    q=OfflineQueue(tmp_path/'q.jsonl')
    q.append({'id':1}); q.append({'id':2}); q.append({'id':3})
    assert q.peek(2)==[{'id':1},{'id':2}]
    assert q.ack(2)==2
    assert q.peek(10)==[{'id':3}]
