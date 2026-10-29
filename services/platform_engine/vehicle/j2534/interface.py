from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class J2534Message:
    protocol_id: int
    tx_flags: int
    data: bytes

class J2534PassThru(ABC):
    @abstractmethod
    def open(self): ...
    @abstractmethod
    def close(self): ...
    @abstractmethod
    def connect(self, protocol_id: int, flags: int = 0): ...
    @abstractmethod
    def disconnect(self): ...
    @abstractmethod
    def send(self, messages: list[J2534Message], timeout_ms: int = 1000): ...
    @abstractmethod
    def receive(self, max_messages: int = 1, timeout_ms: int = 1000): ...
