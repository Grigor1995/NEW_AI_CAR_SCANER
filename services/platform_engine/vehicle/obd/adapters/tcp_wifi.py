from __future__ import annotations
import asyncio
from vehicle.obd.transport import DiagnosticTransport, TransportError

class ObdWifiTransport(DiagnosticTransport):
    """Generic TCP transport for Wi-Fi OBD adapters exposing a socket."""
    def __init__(self, host: str, port: int = 35000):
        self.host, self.port = host, port
        self._reader=None; self._writer=None
    @property
    def connected(self): return self._writer is not None and not self._writer.is_closing()
    async def connect(self):
        try: self._reader, self._writer = await asyncio.wait_for(asyncio.open_connection(self.host, self.port), timeout=5)
        except (OSError, asyncio.TimeoutError) as e: raise TransportError(str(e)) from e
    async def disconnect(self):
        if self._writer:
            self._writer.close(); await self._writer.wait_closed()
        self._reader=self._writer=None
    async def write(self, data: bytes):
        if not self.connected: raise TransportError("Wi-Fi transport is not connected")
        self._writer.write(data); await self._writer.drain()
    async def read_until(self, terminator=b">", timeout=2.0):
        if not self._reader: raise TransportError("Wi-Fi transport is not connected")
        try: return await asyncio.wait_for(self._reader.readuntil(terminator), timeout)
        except (asyncio.TimeoutError, asyncio.IncompleteReadError) as e: raise TransportError(str(e)) from e
