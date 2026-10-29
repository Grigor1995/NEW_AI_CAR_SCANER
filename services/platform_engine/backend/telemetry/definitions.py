from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class SignalDefinition:
    pid: str
    unit: str | None = None
    hard_min: float | None = None
    hard_max: float | None = None
    step_threshold: float | None = None
    rate_threshold_per_second: float | None = None


SIGNAL_DEFINITIONS = {
    "rpm": SignalDefinition("rpm", "rpm", 0.0, 9000.0, 900.0, 2500.0),
    "engine_rpm": SignalDefinition("engine_rpm", "rpm", 0.0, 9000.0, 900.0, 2500.0),
    "coolant_temp": SignalDefinition("coolant_temp", "C", -40.0, 160.0, 25.0, 60.0),
    "battery_voltage": SignalDefinition("battery_voltage", "V", 6.0, 18.0, 1.5, 4.0),
    "vehicle_speed": SignalDefinition("vehicle_speed", "km/h", 0.0, 350.0, 35.0, 100.0),
    "maf": SignalDefinition("maf", "g/s", 0.0, 600.0, 35.0, 250.0),
    "map": SignalDefinition("map", "kPa", 0.0, 300.0, 40.0, 250.0),
    "throttle": SignalDefinition("throttle", "%", 0.0, 100.0, 30.0, 250.0),
    "stft": SignalDefinition("stft", "%", -100.0, 100.0, 15.0, 60.0),
    "ltft": SignalDefinition("ltft", "%", -100.0, 100.0, 15.0, 30.0),
}
