from __future__ import annotations
from abc import ABC, abstractmethod
from .models import CanFrame

class CanBus(ABC):
    @abstractmethod
    async def send(self, frame: CanFrame) -> None: ...

    @abstractmethod
    async def receive(self, timeout_ms: int = 1000) -> CanFrame | None: ...

    async def request(self, frame: CanFrame, timeout_ms: int = 1000) -> CanFrame | None:
        await self.send(frame)
        return await self.receive(timeout_ms)
