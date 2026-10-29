from __future__ import annotations
from dataclasses import dataclass

@dataclass
class CanFrame:
    arbitration_id: int
    data: bytes = b""
    timestamp_ns: int | None = None
    is_extended: bool = False
    is_fd: bool = False
    @property
    def dlc(self) -> int:
        return len(self.data)
