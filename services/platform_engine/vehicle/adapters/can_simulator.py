from __future__ import annotations
import asyncio
from collections import deque
from vehicle.can.models import CanFrame

class SimulatedCanBus:
    """Deterministic CAN bus simulator with TX and RX hooks."""
    def __init__(self):
        self.rx = deque(); self.tx = deque(); self.waiters = []
        self.tx_hooks = []; self.rx_hooks = []
    def add_tx_hook(self, hook): self.tx_hooks.append(hook)
    def add_rx_hook(self, hook): self.rx_hooks.append(hook)
    async def send(self, frame: CanFrame):
        self.tx.append(frame)
        for hook in list(self.tx_hooks):
            result = hook(frame)
            if hasattr(result, '__await__'): await result
    async def receive(self, timeout_ms: int = 1000):
        if self.rx: return self.rx.popleft()
        try: return await asyncio.wait_for(self._wait_frame(), timeout_ms / 1000)
        except asyncio.TimeoutError: return None
    async def _wait_frame(self):
        while not self.rx: await asyncio.sleep(0)
        return self.rx.popleft()
    def inject(self, frame: CanFrame):
        self.rx.append(frame)
        for hook in list(self.rx_hooks):
            result = hook(frame)
            if hasattr(result, '__await__'):
                try:
                    asyncio.get_running_loop().create_task(result)
                except RuntimeError:
                    # No event loop owns this coroutine; close it so synchronous
                    # callers do not leak an un-awaited coroutine warning.
                    close = getattr(result, "close", None)
                    if callable(close):
                        close()
    def pop_tx(self): return self.tx.popleft() if self.tx else None
