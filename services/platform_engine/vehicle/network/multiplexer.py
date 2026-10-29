from __future__ import annotations
import asyncio
from collections import defaultdict

class RoutedCanChannel:
    def __init__(self, mux: 'CanBusDemultiplexer', response_id: int):
        self.mux = mux
        self.response_id = response_id
        self.queue: asyncio.Queue = asyncio.Queue()

    async def send(self, frame):
        await self.mux.bus.send(frame)

    async def receive(self, timeout_ms: int = 1000):
        try:
            return await asyncio.wait_for(self.queue.get(), timeout_ms / 1000)
        except asyncio.TimeoutError:
            return None

class CanBusDemultiplexer:
    """One physical CAN receive loop, fan-out by arbitration ID.

    This prevents concurrent UDS clients from consuming each other's ECU
    responses when multiple ECUs share one CAN bus.
    """
    def __init__(self, bus, *, poll_timeout_ms: int = 100):
        self.bus = bus
        self.poll_timeout_ms = poll_timeout_ms
        self._channels: dict[int, list[RoutedCanChannel]] = defaultdict(list)
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self.unmatched_frames: list = []

    def register(self, response_id: int) -> RoutedCanChannel:
        channel = RoutedCanChannel(self, response_id)
        self._channels[response_id].append(channel)
        return channel

    def unregister(self, channel: RoutedCanChannel) -> None:
        group = self._channels.get(channel.response_id, [])
        if channel in group:
            group.remove(channel)
        if not group:
            self._channels.pop(channel.response_id, None)

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name='can-demultiplexer')

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            try:
                await self._task
            finally:
                self._task = None

    async def _run(self) -> None:
        while not self._stop.is_set():
            frame = await self.bus.receive(self.poll_timeout_ms)
            if frame is None:
                continue
            channels = list(self._channels.get(frame.arbitration_id, ()))
            if not channels:
                self.unmatched_frames.append(frame)
                if len(self.unmatched_frames) > 1000:
                    del self.unmatched_frames[:500]
                continue
            for channel in channels:
                channel.queue.put_nowait(frame)
