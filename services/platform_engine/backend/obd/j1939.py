"""Passive J1939-73 DM1/DM2 decoding. No emissions Mode 01 PID assumptions."""


def decode_diagnostic_frame(arbitration_id: int, payload: bytes) -> dict:
    if not 0 <= arbitration_id <= 0x1FFFFFFF or len(payload) not in (6, 8):
        raise ValueError('Expected a 29-bit CAN identifier and a 6- or 8-byte single CAN frame')
    pf, ps = (arbitration_id >> 16) & 255, (arbitration_id >> 8) & 255
    pgn = (arbitration_id >> 8) & 0x3FFFF
    if pf < 240:
        pgn &= 0x3FF00
    if pgn not in (65226, 65227):
        raise ValueError('Only complete single-frame DM1/DM2 are supported; TP requires reassembly')
    records = []
    body = payload[2:]
    if len(body) not in (0, 4, 6) or (len(body) == 6 and body[4:] != b'\xFF\xFF'):
        raise ValueError('Truncated or invalid DM diagnostic record/padding')
    if len(body) >= 4 and body[:4] not in (b'\x00'*4, b'\xFF'*4):
        a, b, c, d = body[:4]
        cm = bool(d & 128)
        records.append({'spn': None if cm else a | (b << 8) | ((c & 224) << 11),
                        'fmi': c & 31, 'occurrence_count': d & 127,
                        'conversion_method': int(cm), 'raw': body[:4].hex().upper(),
                        'status': 'legacy_conversion_requires_profile' if cm else 'decoded'})
    return {'pgn': pgn, 'source_address': arbitration_id & 255,
            'destination_address': ps if pf < 240 else None,
            'kind': 'DM1' if pgn == 65226 else 'DM2',
            'lamp_status': payload[0], 'lamp_flash': payload[1], 'dtcs': records,
            'source': 'native_can_capture', 'hardware_verified': False}


def decode_bam_capture(frames: list[tuple[int, bytes]]) -> dict:
    """Reassemble one complete globally broadcast TP.BAM DM1/DM2 capture.

    Captures must already be time ordered. RTS/CTS and overlapping unrelated
    sessions are intentionally rejected instead of guessing packet ownership.
    """
    if not frames:
        raise ValueError('A complete BAM capture is required')
    identifier, announcement = frames[0]
    if not 0 <= identifier <= 0x1FFFFFFF or (identifier >> 8) & 0x3FFFF != 0xECFF:
        raise ValueError('First frame must be a global TP.CM BAM announcement')
    if len(announcement) != 8 or announcement[0] != 32 or announcement[4] != 255:
        raise ValueError('Invalid BAM announcement')
    size = int.from_bytes(announcement[1:3], 'little')
    count = announcement[3]
    pgn = int.from_bytes(announcement[5:8], 'little')
    if pgn not in (65226, 65227) or not 9 <= size <= 1785 or count != (size+6)//7 or len(frames) != count+1:
        raise ValueError('Incomplete/unsupported BAM diagnostic message')
    source = identifier & 255
    message = bytearray()
    for sequence, (identifier, payload) in enumerate(frames[1:], 1):
        if not 0 <= identifier <= 0x1FFFFFFF or (identifier >> 8) & 0x3FFFF != 0xEBFF or identifier & 255 != source:
            raise ValueError('BAM data source/destination mismatch')
        if len(payload) != 8 or payload[0] != sequence:
            raise ValueError('BAM data packet missing or out of sequence')
        message.extend(payload[1:])
    if any(value != 255 for value in message[size:]):
        raise ValueError('Invalid BAM trailing padding')
    message = message[:size]
    if (len(message)-2) % 4:
        raise ValueError('Truncated BAM diagnostic record')
    dtcs = []
    for offset in range(2, len(message), 4):
        decoded = decode_diagnostic_frame((pgn << 8) | source, bytes(message[:2]+message[offset:offset+4]))
        dtcs.extend(decoded['dtcs'])
    return {'pgn': pgn, 'source_address': source, 'kind': 'DM1' if pgn == 65226 else 'DM2',
            'lamp_status': message[0], 'lamp_flash': message[1], 'dtcs': dtcs,
            'transport': 'TP.BAM', 'source': 'native_can_capture', 'hardware_verified': False}
