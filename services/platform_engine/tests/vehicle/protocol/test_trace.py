from uuid import uuid4
import asyncio
from vehicle.can.models import CanFrame
from vehicle.adapters.can_simulator import SimulatedCanBus
from vehicle.protocol.trace import ProtocolTraceRecorder, TracedCanBus


def test_trace_records_and_exports(tmp_path):
    sid = uuid4(); recorder = ProtocolTraceRecorder(session_id=sid, max_events=2)
    recorder.record_can('TX', CanFrame(0x123, b'\x01'))
    recorder.record_can('RX', CanFrame(0x123, b'\x02'))
    recorder.record_can('TX', CanFrame(0x123, b'\x03'))
    assert len(recorder.snapshot()) == 2
    path = tmp_path / 'trace.jsonl'
    assert recorder.export_jsonl(path) == 2
    assert 'data_hex' in path.read_text()


def test_traced_bus_captures_tx_rx():
    async def run():
        bus = SimulatedCanBus(); recorder = ProtocolTraceRecorder(); traced = TracedCanBus(bus, recorder)
        bus.inject(CanFrame(0x708, b'\x02AB'))
        await traced.send(CanFrame(0x700, b'\x01'))
        await traced.receive()
        assert [e.direction for e in recorder.snapshot()] == ['TX', 'RX']
    asyncio.run(run())
