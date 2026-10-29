"""Passive SAE J1708 checksum and J1587 parameter framing decoder.

The bridge supplies one complete packet, including its checksum. Electrical
bus arbitration/timing and OEM parameter scaling require an appropriate driver.
"""


def decode_packet(packet: bytes) -> dict:
    if not 4 <= len(packet) <= 21:
        raise ValueError('J1708 packets must contain 4..21 bytes including checksum')
    if sum(packet) & 255:
        raise ValueError('J1708 checksum mismatch')
    if packet[0] < 128:
        raise ValueError('Expected a J1587 application MID (128..255)')
    cursor, end, parameters = 1, len(packet)-1, []
    while cursor < end:
        pid = packet[cursor]
        cursor += 1
        extended = pid == 255
        if extended:
            if cursor >= end:
                raise ValueError('Missing extended PID')
            pid = packet[cursor]
            cursor += 1
        if pid >= 254:
            raise ValueError('Reserved/data-link escape PID needs a dedicated decoder')
        size = 1 if pid < 128 else 2 if pid < 192 else None
        if size is None:
            if cursor >= end:
                raise ValueError('Missing variable parameter length')
            size = packet[cursor]
            cursor += 1
        if size < 1 or cursor+size > end:
            raise ValueError('Truncated or empty J1587 parameter')
        parameters.append({'pid': pid+256 if extended else pid,
                           'raw_hex': packet[cursor:cursor+size].hex().upper()})
        cursor += size
    return {'mid': packet[0], 'parameters': parameters, 'checksum_valid': True,
            'source': 'native_j1708_capture', 'scope': 'Parameter framing only; no OEM scaling',
            'hardware_verified': False}
