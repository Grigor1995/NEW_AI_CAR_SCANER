from __future__ import annotations
import asyncio
from vehicle.obd.transport import DiagnosticTransport, TransportError

class ObdUsbSerialTransport(DiagnosticTransport):
    """USB serial transport. pyserial is optional and imported only when used."""
    def __init__(self, port: str, baudrate: int = 115200):
        self.port, self.baudrate, self._serial = port, baudrate, None
    @property
    def connected(self): return self._serial is not None and self._serial.is_open
    async def connect(self):
        try:
            import serial
            self._serial = serial.Serial(self.port, self.baudrate, timeout=0.1)
        except Exception as e: raise TransportError(str(e)) from e
    async def disconnect(self):
        if self._serial: self._serial.close()
        self._serial=None
    async def write(self, data: bytes):
        if not self.connected: raise TransportError("USB transport is not connected")
        await asyncio.to_thread(self._serial.write, data)
    async def read_until(self, terminator=b">", timeout=2.0):
        if not self.connected: raise TransportError("USB transport is not connected")
        async def read():
            buf=bytearray()
            while True:
                b=await asyncio.to_thread(self._serial.read, 1)
                if b: buf += b;
                if buf.endswith(terminator): return bytes(buf)
        try: return await asyncio.wait_for(read(), timeout)
        except asyncio.TimeoutError as e: raise TransportError("USB read timeout") from e
