"""ISO 13400-2 TCP routing activation and bounded read-only UDS exchanges.

No discovery inference, authentication bypass, coding or programming services.
TLS-only gateways need a separate authenticated/TLS transport, not this client.
"""
from __future__ import annotations

import asyncio
import struct
from vehicle.uds.read_only import validate_read_request, validate_positive


class DoipError(ConnectionError):
    pass


class DoipClient:
    def __init__(self, host: str, *, source_address: int, target_address: int,
                 port: int = 13400, timeout: float = 5):
        if not host.strip() or not 1 <= port <= 65535:
            raise ValueError('A valid host and TCP port are required')
        if not all(1 <= address <= 65535 for address in (source_address, target_address)):
            raise ValueError('Logical addresses must be nonzero uint16 values')
        if not 0 < timeout <= 30:
            raise ValueError('Timeout must be within 0..30 seconds')
        self.host, self.port = host, port
        self.source, self.target, self.timeout = source_address, target_address, timeout
        self.reader = self.writer = None
        self.lock = asyncio.Lock()

    async def close(self):
        writer, self.writer = self.writer, None
        self.reader = None
        if writer:
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass

    async def _send(self, kind: int, payload: bytes):
        self.writer.write(struct.pack('!BBHI', 2, 0xFD, kind, len(payload)) + payload)
        await self.writer.drain()

    async def _receive(self):
        header = await self.reader.readexactly(8)
        version, inverse, kind, size = struct.unpack('!BBHI', header)
        if version not in (2, 3) or version ^ inverse != 255:
            raise DoipError('Invalid DoIP version/header')
        if size > 65536:
            raise DoipError('DoIP payload exceeds 64 KiB limit')
        return kind, await self.reader.readexactly(size)

    async def _read_exchange(self, request: bytes):
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        await self._send(5, struct.pack('!HB4x', self.source, 0))
        kind, body = await self._receive()
        if kind != 6 or len(body) not in (9, 13) or int.from_bytes(body[:2], 'big') != self.source or body[4] != 0x10:
            raise DoipError('DoIP routing activation was not accepted')
        await self._send(0x8001, struct.pack('!HH', self.source, self.target) + request)
        for _ in range(32):
            kind, body = await self._receive()
            if kind == 7 and not body:
                await self._send(8, self.source.to_bytes(2, 'big'))
                continue
            if kind == 0x8002:
                if len(body) < 5 or body[:4] != struct.pack('!HH', self.target, self.source) or body[4] != 0:
                    raise DoipError('Invalid diagnostic acknowledgement')
                continue
            if kind != 0x8001 or len(body) < 5:
                raise DoipError(f'DoIP diagnostic request rejected (payload type 0x{kind:04X})')
            if body[:4] != struct.pack('!HH', self.target, self.source):
                raise DoipError('Diagnostic logical addresses do not match the requested ECU')
            response = body[4:]
            if response == bytes((0x7F, request[0], 0x78)):
                continue  # responsePending remains within the overall deadline.
            try:
                validate_positive(request, response)
            except ValueError as error:
                raise DoipError(str(error)) from error
            return response
        raise DoipError('DoIP response frame limit exceeded')

    async def read(self, request: bytes) -> bytes:
        validate_read_request(request)
        async with self.lock:
            try:
                async with asyncio.timeout(self.timeout):
                    return await self._read_exchange(request)
            except DoipError:
                raise
            except (TimeoutError, OSError, asyncio.IncompleteReadError) as error:
                raise DoipError(f'DoIP transport failed: {type(error).__name__}') from error
            finally:
                await self.close()
