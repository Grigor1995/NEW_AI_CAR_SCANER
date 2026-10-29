from __future__ import annotations
from collections import deque
from vehicle.can.models import CanFrame


class UdsEcuSimulator:
    """Deterministic read-only UDS ECU simulator used by Phase 16 protocol tests."""

    def __init__(self, bus, request_id=0x7E0, response_id=0x7E8, *, vin='VINTEST1234567890', software_version='SW-1.0', hardware_version='HW-1.0', dtc_records=None):
        self.bus = bus
        self.request_id = request_id
        self.response_id = response_id
        self.vin = vin
        self.software_version = software_version
        self.hardware_version = hardware_version
        self.dtc_records = list(dtc_records) if dtc_records is not None else [(0x030200, 0x28)]
        self._pending_cf: deque[CanFrame] = deque()
        if hasattr(bus, 'add_tx_hook'):
            bus.add_tx_hook(self.on_tx)

    def _positive(self, service_id: int, payload: bytes = b'') -> bytes:
        return bytes([(service_id + 0x40) & 0xFF]) + payload

    def _negative(self, service_id: int, nrc: int) -> bytes:
        return bytes([0x7F, service_id, nrc])

    def _response_payload(self, service_id: int, payload: bytes) -> bytes:
        if service_id == 0x10 and payload:
            return self._positive(service_id, bytes([payload[0]]))
        if service_id == 0x22 and len(payload) >= 2:
            did = int.from_bytes(payload[:2], 'big')
            values = {
                0xF190: self.vin.encode('ascii'),
                0xF187: self.software_version.encode('ascii'),
                0xF191: self.hardware_version.encode('ascii'),
            }
            value = values.get(did)
            if value is None:
                return self._negative(service_id, 0x31)
            return self._positive(service_id, did.to_bytes(2, 'big') + value)
        if service_id == 0x19 and payload:
            if payload[0] != 0x02:
                return self._negative(service_id, 0x12)
            body = bytes([payload[0], 0xFF]) + b''.join(raw.to_bytes(3, 'big') + bytes([status]) for raw, status in self.dtc_records)
            return self._positive(service_id, body)
        return self._negative(service_id, 0x11)

    async def on_tx(self, frame: CanFrame):
        if frame.arbitration_id == self.request_id:
            if not frame.data:
                return
            pci = frame.data[0] >> 4
            if pci == 0:
                length = frame.data[0] & 0x0F
                request = frame.data[1:1 + length]
                if not request:
                    return
                payload = self._response_payload(request[0], bytes(request[1:]))
                self._queue_response(payload)
            elif pci == 3 and self._pending_cf:
                # Client sent flow-control; release the queued consecutive frames.
                status = frame.data[0] & 0x0F
                if status == 0:
                    while self._pending_cf:
                        self.bus.inject(self._pending_cf.popleft())

    def _queue_response(self, uds_payload: bytes):
        if len(uds_payload) <= 7:
            self.bus.inject(CanFrame(self.response_id, bytes([len(uds_payload)]) + uds_payload))
            return
        length = len(uds_payload)
        self.bus.inject(CanFrame(self.response_id, bytes([0x10 | ((length >> 8) & 0x0F), length & 0xFF]) + uds_payload[:6]))
        offset = 6
        seq = 1
        while offset < length:
            chunk = uds_payload[offset:offset + 7]
            self._pending_cf.append(CanFrame(self.response_id, bytes([0x20 | (seq & 0x0F)]) + chunk))
            offset += len(chunk)
            seq = (seq + 1) & 0x0F

    # Backward-compatible manual processing hook.
    def process(self):
        while (frame := self.bus.pop_tx()) is not None:
            result = self.on_tx(frame)
            # process() is intentionally synchronous for legacy tests; the new path uses bus hooks.
            if hasattr(result, '__await__'):
                continue
