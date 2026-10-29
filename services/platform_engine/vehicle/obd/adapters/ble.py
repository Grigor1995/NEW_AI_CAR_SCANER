from __future__ import annotations
from vehicle.obd.transport import DiagnosticTransport, TransportError

class ObdBleTransport(DiagnosticTransport):
    """BLE GATT transport seam. UUIDs are adapter-specific and therefore configurable."""
    def __init__(self, address: str, tx_uuid: str, rx_uuid: str):
        self.address, self.tx_uuid, self.rx_uuid = address, tx_uuid, rx_uuid
        self._client=None; self._buffer=bytearray()
    @property
    def connected(self): return bool(self._client and self._client.is_connected)
    async def connect(self):
        try:
            from bleak import BleakClient
            self._client=BleakClient(self.address); await self._client.connect()
            await self._client.start_notify(self.rx_uuid, lambda _, data: self._buffer.extend(data))
        except Exception as e: raise TransportError(str(e)) from e
    async def disconnect(self):
        if self._client and self._client.is_connected: await self._client.disconnect()
        self._client=None
    async def write(self, data: bytes):
        if not self.connected: raise TransportError("BLE transport is not connected")
        await self._client.write_gatt_char(self.tx_uuid, data, response=False)
    async def read_until(self, terminator=b">", timeout=2.0):
        import asyncio, time
        start=time.monotonic()
        while time.monotonic()-start < timeout:
            idx=self._buffer.find(terminator)
            if idx >= 0:
                out=bytes(self._buffer[:idx+len(terminator)]); del self._buffer[:idx+len(terminator)]; return out
            await asyncio.sleep(0.01)
        raise TransportError("BLE read timeout")
