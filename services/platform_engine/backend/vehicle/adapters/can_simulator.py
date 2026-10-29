from __future__ import annotations
import asyncio

class SimulatedCanBus:
    def __init__(self):
        self.queue=asyncio.Queue()
    async def send(self, frame):
        await self.queue.put(frame)
    async def receive(self, timeout_ms=1000):
        try: return await asyncio.wait_for(self.queue.get(), timeout_ms/1000)
        except asyncio.TimeoutError: return None
