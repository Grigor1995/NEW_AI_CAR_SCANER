from dataclasses import dataclass
from enum import Enum
import time

class HealthLevel(str, Enum):
    OK="ok"; WARNING="warning"; CRITICAL="critical"

@dataclass(frozen=True)
class DeviceHealth:
    battery_percent: float
    temperature_c: float
    storage_free_mb: int
    connectivity: str
    level: HealthLevel
    timestamp: float

class HealthMonitor:
    def evaluate(self, battery_percent: float, temperature_c: float, storage_free_mb: int, connectivity: str) -> DeviceHealth:
        level = HealthLevel.OK
        if battery_percent < 15 or storage_free_mb < 500 or temperature_c >= 75:
            level = HealthLevel.CRITICAL
        elif battery_percent < 30 or storage_free_mb < 1000 or temperature_c >= 65:
            level = HealthLevel.WARNING
        return DeviceHealth(battery_percent, temperature_c, storage_free_mb, connectivity, level, time.time())
