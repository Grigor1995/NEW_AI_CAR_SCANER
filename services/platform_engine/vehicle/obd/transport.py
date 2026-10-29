from __future__ import annotations
from abc import ABC, abstractmethod

class TransportError(ConnectionError): pass

class DiagnosticTransport(ABC):
    """Byte-stream abstraction shared by BLE/Wi-Fi/USB and future VCIs."""
    @abstractmethod
    async def connect(self) -> None: ...
    @abstractmethod
    async def disconnect(self) -> None: ...
    @abstractmethod
    async def write(self, data: bytes) -> None: ...
    @abstractmethod
    async def read_until(self, terminator: bytes=b">", timeout: float=2.0) -> bytes: ...
    @property
    @abstractmethod
    def connected(self) -> bool: ...
