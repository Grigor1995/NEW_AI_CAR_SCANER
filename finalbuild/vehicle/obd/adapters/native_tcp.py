"""Opt-in C++ TCP transport. Protocol decoding remains in the shared Python core."""
from __future__ import annotations

import asyncio
from vehicle.obd.transport import DiagnosticTransport, TransportError


class NativeObdWifiTransport(DiagnosticTransport):
    """POSIX numeric-IPv4 transport; not a claim of physical adapter support.

    Calls run on a worker thread. Cancellation drains the bounded native call
    before closing its socket, preventing a close/read race and stale reuse.
    GenericObdClient retains command-level serialization.
    """

    def __init__(self, host: str, port: int = 35000):
        try:
            from _obd_native import TcpTransport
        except ImportError as exc:
            raise TransportError("Build native/obd and add its output to PYTHONPATH") from exc
        self.host, self.port = host, port
        self._native = TcpTransport()
        self._lock = asyncio.Lock()
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    async def _call(self, method, *args):
        async with self._lock:
            task = asyncio.create_task(asyncio.to_thread(method, *args))
            try:
                result = await asyncio.shield(task)
                self._connected = self._native.connected
                return result
            except asyncio.CancelledError:
                # Keep ownership until the worker exits (max 120 seconds).
                while not task.done():
                    try:
                        await asyncio.shield(task)
                    except asyncio.CancelledError:
                        continue
                    except Exception:
                        break
                if task.done() and not task.cancelled():
                    task.exception()  # consume worker failure during cancellation
                self._native.disconnect()
                self._connected = False
                raise
            except (RuntimeError, ValueError) as exc:
                self._native.disconnect()
                self._connected = False
                raise TransportError(str(exc)) from exc

    async def connect(self) -> None:
        await self._call(self._native.connect, self.host, self.port, 5.0)

    async def disconnect(self) -> None:
        await self._call(self._native.disconnect)

    async def write(self, data: bytes) -> None:
        await self._call(self._native.write, data, 3.0)

    async def read_until(self, terminator: bytes = b">", timeout: float = 2.0) -> bytes:
        return await self._call(self._native.read_until, terminator, timeout)
