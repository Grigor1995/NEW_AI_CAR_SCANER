from __future__ import annotations
import asyncio
from .models import FlowStatus, IsoTpProtocolError, IsoTpTimeout
from vehicle.can.models import CanFrame

class IsoTpStack:
    """ISO-TP sender/receiver over an abstract CAN bus."""
    def __init__(self, bus, tx_id: int, rx_id: int, *, extended: bool = False,
                 timeout_ms: int = 1000, max_payload: int = 4095):
        self.bus = bus; self.tx_id = tx_id; self.rx_id = rx_id
        self.extended = extended; self.timeout_ms = timeout_ms; self.max_payload = max_payload

    async def _receive_expected(self, timeout_ms=None):
        frame = await self.bus.receive(self.timeout_ms if timeout_ms is None else timeout_ms)
        if frame is None: raise IsoTpTimeout("ISO-TP receive timeout")
        if frame.arbitration_id != self.rx_id: return await self._receive_expected(timeout_ms)
        return frame

    async def send(self, payload: bytes) -> None:
        if len(payload) > self.max_payload: raise IsoTpProtocolError("payload too large")
        if len(payload) <= 7:
            await self.bus.send(CanFrame(self.tx_id, bytes([len(payload)]) + payload, is_extended=self.extended))
            return
        if len(payload) > 0xFFF: raise IsoTpProtocolError("classic ISO-TP payload exceeds 4095 bytes")
        first = bytes([0x10 | ((len(payload) >> 8) & 0x0F), len(payload) & 0xFF]) + payload[:6]
        await self.bus.send(CanFrame(self.tx_id, first, is_extended=self.extended))
        fc = await self._receive_expected()
        if not fc.data or fc.data[0] >> 4 != 3: raise IsoTpProtocolError("expected flow control")
        status = FlowStatus(fc.data[0] & 0x0F)
        if status == FlowStatus.OVERFLOW: raise IsoTpProtocolError("receiver overflow")
        if status == FlowStatus.WAIT:
            fc = await self._receive_expected()
            if (fc.data[0] & 0x0F) != FlowStatus.CTS: raise IsoTpProtocolError("flow control did not become CTS")
        bs = fc.data[1] if len(fc.data) > 1 else 0
        st_min = fc.data[2] if len(fc.data) > 2 else 0
        offset = 6; seq = 1; sent_in_block = 0
        while offset < len(payload):
            chunk = payload[offset:offset+7]
            await self.bus.send(CanFrame(self.tx_id, bytes([0x20 | (seq & 0x0F)]) + chunk, is_extended=self.extended))
            offset += len(chunk); seq = (seq + 1) & 0x0F; sent_in_block += 1
            if st_min:
                delay = st_min / 1000 if st_min <= 0x7F else (st_min & 0x0F) * 0.0001
                await asyncio.sleep(delay)
            if bs and sent_in_block >= bs and offset < len(payload):
                fc = await self._receive_expected()
                if (fc.data[0] & 0x0F) != FlowStatus.CTS: raise IsoTpProtocolError("expected CTS")
                bs = fc.data[1]; sent_in_block = 0

    async def receive(self) -> bytes:
        frame = await self._receive_expected()
        if not frame.data: raise IsoTpProtocolError("empty CAN frame")
        pci = frame.data[0] >> 4
        if pci == 0:
            length = frame.data[0] & 0x0F
            if length > 7 or length > len(frame.data)-1: raise IsoTpProtocolError("invalid single frame")
            return bytes(frame.data[1:1+length])
        if pci != 1: raise IsoTpProtocolError("expected single/first frame")
        if len(frame.data) < 2: raise IsoTpProtocolError("invalid first frame")
        length = ((frame.data[0] & 0x0F) << 8) | frame.data[1]
        if length == 0 or length > self.max_payload: raise IsoTpProtocolError("invalid payload length")
        result = bytearray(frame.data[2:])
        await self.bus.send(CanFrame(self.tx_id, bytes([0x30, 0x00, 0x00]), is_extended=self.extended))
        expected_seq = 1
        while len(result) < length:
            cf = await self._receive_expected()
            if cf.data[0] >> 4 != 2: raise IsoTpProtocolError("expected consecutive frame")
            if (cf.data[0] & 0x0F) != expected_seq: raise IsoTpProtocolError("unexpected sequence number")
            result.extend(cf.data[1:]); expected_seq = (expected_seq + 1) & 0x0F
        return bytes(result[:length])
