from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class UdsDtcRecord:
    raw_dtc: int
    code: str
    status_byte: int

    @property
    def confirmed(self) -> bool:
        # ISO 14229 DTC status bit 3 is confirmedDTC. Bit 0 only says
        # testFailed and must not be presented as a confirmed DTC.
        return bool(self.status_byte & 0x08)


def format_uds_dtc(raw_dtc: int) -> str:
    if not 0 <= raw_dtc <= 0xFFFFFF:
        raise ValueError('raw_dtc must fit uint24')
    b0 = (raw_dtc >> 16) & 0xFF
    b1 = (raw_dtc >> 8) & 0xFF
    b2 = raw_dtc & 0xFF
    prefix = ('P', 'C', 'B', 'U')[(b0 >> 6) & 0x03]
    return f'{prefix}{(b0 >> 4) & 0x03}{b0 & 0x0F:X}{b1:02X}{b2:02X}'


def parse_dtc_information(payload: bytes) -> list[UdsDtcRecord]:
    """Decode UDS ReadDTCInformation positive-response payload.

    ``payload`` is the bytes after service ID 0x59. For subfunction 0x02,
    the first byte is the subfunction and the second byte is normally the
    DTCStatusAvailabilityMask, followed by 4-byte DTC/status records.
    Unknown layouts remain represented as raw records only when a complete
    4-byte record is present.
    """
    if not payload:
        return []
    if payload[0] not in range(0x01, 0x20):
        raise ValueError('malformed UDS DTC information response')
    body = payload[2:] if len(payload) >= 2 else b''
    out: list[UdsDtcRecord] = []
    for offset in range(0, len(body) - 3, 4):
        raw = int.from_bytes(body[offset:offset + 3], 'big')
        status = body[offset + 3]
        out.append(UdsDtcRecord(raw_dtc=raw, code=format_uds_dtc(raw), status_byte=status))
    return out
