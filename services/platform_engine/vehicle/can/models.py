from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class CanFrame:
    arbitration_id: int
    data: bytes
    timestamp_ns: int | None = None
    is_extended: bool = False
    is_fd: bool = False

    def __post_init__(self):
        if not 0 <= self.arbitration_id <= (0x1FFFFFFF if self.is_extended else 0x7FF):
            raise ValueError("invalid CAN arbitration id")
        max_len = 64 if self.is_fd else 8
        if len(self.data) > max_len:
            raise ValueError(f"CAN payload exceeds {max_len} bytes")

    @property
    def dlc(self) -> int:
        return len(self.data)
