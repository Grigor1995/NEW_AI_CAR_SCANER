import asyncio

import pytest

from vehicle.can.models import CanFrame
from vehicle.isotp.models import IsoTpProtocolError, IsoTpTimeout
from vehicle.isotp.stack import IsoTpStack


class QueueBus:
    def __init__(self, frames=()):
        self.frames = list(frames)
        self.sent = []
    async def send(self, frame):
        self.sent.append(frame)
    async def receive(self, timeout_ms=1000):
        if self.frames:
            return self.frames.pop(0)
        return None


@pytest.mark.asyncio
async def test_receive_times_out_and_skips_frames_for_other_arbitration_ids():
    bus = QueueBus([CanFrame(0x701, b"\x01A"), CanFrame(0x708, b"\x01B")])
    stack = IsoTpStack(bus, 0x700, 0x708)
    assert await stack.receive() == b"B"

    with pytest.raises(IsoTpTimeout):
        await IsoTpStack(QueueBus(), 0x700, 0x708)._receive_expected()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "frame",
    [
        CanFrame(0x708, b""),
        CanFrame(0x708, b"\x08ABC"),
        CanFrame(0x708, b"\x20ABC"),
        CanFrame(0x708, b"\x10"),
        CanFrame(0x708, b"\x10\x00ABC"),
    ],
)
async def test_receive_rejects_invalid_pci_or_lengths(frame):
    with pytest.raises(IsoTpProtocolError):
        await IsoTpStack(QueueBus([frame]), 0x700, 0x708).receive()


@pytest.mark.asyncio
async def test_receive_rejects_consecutive_frame_sequence_mismatch():
    payload = b"0123456789ABC"
    bus = QueueBus([
        CanFrame(0x708, bytes([0x10, len(payload)]) + payload[:6]),
        CanFrame(0x708, b"\x22" + payload[6:]),
    ])
    with pytest.raises(IsoTpProtocolError, match="unexpected sequence"):
        await IsoTpStack(bus, 0x700, 0x708).receive()


@pytest.mark.asyncio
async def test_receive_rejects_non_consecutive_frame_during_multiframe():
    payload = b"0123456789ABC"
    bus = QueueBus([
        CanFrame(0x708, bytes([0x10, len(payload)]) + payload[:6]),
        CanFrame(0x708, b"\x30\x00\x00"),
    ])
    with pytest.raises(IsoTpProtocolError, match="expected consecutive"):
        await IsoTpStack(bus, 0x700, 0x708).receive()


@pytest.mark.asyncio
async def test_send_rejects_payload_limits_and_bad_flow_control():
    with pytest.raises(IsoTpProtocolError, match="payload too large"):
        await IsoTpStack(QueueBus(), 0x700, 0x708, max_payload=8).send(b"012345678")
    bus = QueueBus([CanFrame(0x708, b"\x21\x00\x00")])
    with pytest.raises(IsoTpProtocolError, match="expected flow control"):
        await IsoTpStack(bus, 0x700, 0x708).send(b"0123456789ABC")


@pytest.mark.asyncio
async def test_send_rejects_flow_control_overflow_and_invalid_wait_followup():
    payload = b"0123456789ABC"
    overflow = QueueBus([CanFrame(0x708, b"\x32\x00\x00")])
    with pytest.raises(IsoTpProtocolError, match="receiver overflow"):
        await IsoTpStack(overflow, 0x700, 0x708).send(payload)

    wait_then_wait = QueueBus([
        CanFrame(0x708, b"\x31\x00\x00"),
        CanFrame(0x708, b"\x31\x00\x00"),
    ])
    with pytest.raises(IsoTpProtocolError, match="did not become CTS"):
        await IsoTpStack(wait_then_wait, 0x700, 0x708).send(payload)


@pytest.mark.asyncio
async def test_send_handles_wait_cts_block_size_and_extended_frames(monkeypatch):
    payload = b"0123456789ABCDEFGHIJKLMN"
    bus = QueueBus([
        CanFrame(0x18DAF110, b"\x31\x01\x00", is_extended=True),
        CanFrame(0x18DAF110, b"\x30\x01\x00", is_extended=True),
        CanFrame(0x18DAF110, b"\x30\x00\x00", is_extended=True),
    ])
    # Replace sleep with an async no-op so STmin/block handling never incurs wall-clock delay.
    async def no_sleep(_seconds):
        return None
    monkeypatch.setattr(asyncio, "sleep", no_sleep)
    stack = IsoTpStack(bus, 0x18DA10F1, 0x18DAF110, extended=True)
    await stack.send(payload)
    assert bus.sent[0].data[0] >> 4 == 1
    assert all(frame.is_extended for frame in bus.sent)
    assert len(bus.sent) >= 4


@pytest.mark.asyncio
async def test_send_rejects_non_cts_flow_control_after_block():
    payload = b"0123456789ABCDEFGHIJKLMN"
    bus = QueueBus([
        CanFrame(0x708, b"\x30\x01\x00"),
        CanFrame(0x708, b"\x31\x01\x00"),
    ])
    with pytest.raises(IsoTpProtocolError, match="expected CTS"):
        await IsoTpStack(bus, 0x700, 0x708).send(payload)
