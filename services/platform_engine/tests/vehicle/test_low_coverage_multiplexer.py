import asyncio

import pytest

from vehicle.adapters.can_simulator import SimulatedCanBus
from vehicle.can.models import CanFrame
from vehicle.network.multiplexer import CanBusDemultiplexer


@pytest.mark.asyncio
async def test_demultiplexer_routes_matching_frames_to_registered_channels():
    bus = SimulatedCanBus()
    mux = CanBusDemultiplexer(bus, poll_timeout_ms=5)
    channel_a = mux.register(0x7E8)
    channel_b = mux.register(0x7E9)

    await mux.start()
    await mux.start()  # idempotent start
    frame_a = CanFrame(0x7E8, b"\x02\x41\x0C")
    frame_b = CanFrame(0x7E9, b"\x02\x41\x0D")
    bus.inject(frame_a)
    bus.inject(frame_b)
    assert await channel_a.receive(timeout_ms=100) == frame_a
    assert await channel_b.receive(timeout_ms=100) == frame_b

    assert await channel_a.receive(timeout_ms=1) is None
    await mux.stop()
    await mux.stop()
    assert mux._task is None


@pytest.mark.asyncio
async def test_demultiplexer_tracks_unmatched_frames_and_caps_history():
    bus = SimulatedCanBus()
    mux = CanBusDemultiplexer(bus, poll_timeout_ms=5)
    for index in range(1002):
        bus.inject(CanFrame(0x100, bytes([index % 256])))

    await mux.start()
    for _ in range(100):
        if len(mux.unmatched_frames) == 501:
            break
        await asyncio.sleep(0.001)
    await mux.stop()

    assert len(mux.unmatched_frames) == 502
    assert mux.unmatched_frames[-1].data == bytes([1001 % 256])
    channel = mux.register(0x7E8)
    mux.unregister(channel)
    assert 0x7E8 not in mux._channels
    mux.unregister(channel)  # unregister is safe even for an unknown channel

@pytest.mark.asyncio
async def test_routed_channel_send_and_multiple_subscribers_receive_same_response():
    bus = SimulatedCanBus()
    mux = CanBusDemultiplexer(bus, poll_timeout_ms=5)
    channel_a = mux.register(0x7E8)
    channel_b = mux.register(0x7E8)
    request = CanFrame(0x7E0, b"\x01\x03")
    await channel_a.send(request)
    assert bus.pop_tx() == request

    await mux.start()
    response = CanFrame(0x7E8, b"\x02\x41\x0C")
    bus.inject(response)
    assert await channel_a.receive(timeout_ms=100) == response
    assert await channel_b.receive(timeout_ms=100) == response

    mux.unregister(channel_a)
    assert len(mux._channels[0x7E8]) == 1
    mux.unregister(channel_b)
    assert 0x7E8 not in mux._channels
    await mux.stop()
