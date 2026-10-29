"""Shared explicit read-only UDS request and positive-response validation."""


def read_request(did: int | None, dtc_status_mask: int | None) -> bytes:
    if (did is None) == (dtc_status_mask is None):
        raise ValueError('Provide exactly one DID or DTC status mask')
    if did is not None:
        if not 0 <= did <= 65535:
            raise ValueError('DID must fit uint16')
        return b'\x22'+did.to_bytes(2,'big')
    if not 0 <= dtc_status_mask <= 255:
        raise ValueError('DTC status mask must fit uint8')
    return bytes((0x19,2,dtc_status_mask))


def validate_read_request(request: bytes):
    if not ((len(request) == 3 and request[0] == 0x22)
            or (len(request) == 3 and request[:2] == b'\x19\x02')):
        raise ValueError('Only ReadDataByIdentifier and reportDTCByStatusMask are supported')


def validate_positive(request: bytes, response: bytes):
    validate_read_request(request)
    if response[:1] == b'\x7F':
        raise ValueError(f'Negative UDS response: {response.hex().upper()}')
    expected = bytes((request[0]+0x40,)) + request[1:3 if request[0] == 0x22 else 2]
    if not response.startswith(expected):
        raise ValueError('UDS service/DID/subfunction response mismatch')
    if request[0] == 0x19 and (len(response) < 3 or (len(response)-3) % 4):
        raise ValueError('Truncated UDS DTC status/record response')
