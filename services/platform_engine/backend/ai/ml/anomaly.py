from __future__ import annotations
from dataclasses import dataclass
from math import sqrt
from statistics import mean

@dataclass(frozen=True)
class AnomalyResult:
    signal: str
    value: float
    baseline_mean: float
    z_score: float
    anomalous: bool
    explanation: str

class NumericAnomalyDetector:
    """Dependency-free baseline detector for live-data smoke analysis; production can swap in ML models."""
    def score(self, signal: str, value: float, baseline: list[float], z_threshold: float = 3.0) -> AnomalyResult:
        if len(baseline) < 2:
            return AnomalyResult(signal, value, baseline[0] if baseline else value, 0.0, False, "Insufficient baseline data.")
        mu = mean(baseline)
        variance = sum((x - mu) ** 2 for x in baseline) / len(baseline)
        sd = sqrt(variance)
        z = 0.0 if sd == 0 else (value - mu) / sd
        return AnomalyResult(signal, value, mu, z, abs(z) >= z_threshold, "Signal is outside the configured baseline threshold." if abs(z) >= z_threshold else "Signal is within the baseline range.")
