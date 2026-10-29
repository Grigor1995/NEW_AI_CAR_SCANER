from __future__ import annotations
from math import sqrt
from statistics import mean
from typing import Sequence
from .definitions import SIGNAL_DEFINITIONS
from .models import SampleQuality, SignalEvent, SignalEventType, SignalStats, TelemetrySample


def _sorted_valid(samples: Sequence[TelemetrySample]) -> list[TelemetrySample]:
    return sorted((s for s in samples if s.quality != SampleQuality.INVALID), key=lambda s: (s.timestamp_ms, s.sequence or -1))


def _stddev(values: list[float], avg: float) -> float:
    if len(values) < 2:
        return 0.0
    return sqrt(sum((x - avg) ** 2 for x in values) / (len(values) - 1))


def compute_stats(session_id, pid: str, samples: Sequence[TelemetrySample]) -> SignalStats:
    xs = _sorted_valid(samples)
    if not xs:
        return SignalStats(session_id=session_id, pid=pid, count=0)
    values = [s.value for s in xs]
    deltas = [abs(b.value - a.value) for a, b in zip(xs, xs[1:])]
    duration = max(xs[-1].timestamp_ms - xs[0].timestamp_ms, 0)
    slope = None
    if duration > 0:
        slope = (xs[-1].value - xs[0].value) / (duration / 1000.0)
    hz = None
    if duration > 0 and len(xs) > 1:
        hz = (len(xs) - 1) / (duration / 1000.0)
    avg = mean(values)
    return SignalStats(
        session_id=session_id,
        pid=pid,
        count=len(xs),
        start_ms=xs[0].timestamp_ms,
        end_ms=xs[-1].timestamp_ms,
        duration_ms=duration,
        min_value=min(values),
        max_value=max(values),
        mean=avg,
        stddev=_stddev(values, avg),
        slope_per_second=slope,
        mean_abs_delta=mean(deltas) if deltas else 0.0,
        max_abs_delta=max(deltas) if deltas else 0.0,
        sample_rate_hz=hz,
    )


def detect_events(session_id, pid: str, samples: Sequence[TelemetrySample]) -> list[SignalEvent]:
    xs = _sorted_valid(samples)
    definition = SIGNAL_DEFINITIONS.get(pid)
    if len(xs) < 2:
        return []
    events: list[SignalEvent] = []
    for prev, cur in zip(xs, xs[1:]):
        dt = max(cur.timestamp_ms - prev.timestamp_ms, 1)
        dv = cur.value - prev.value
        abs_dv = abs(dv)
        rate = abs_dv / (dt / 1000.0)
        if definition and definition.hard_min is not None and cur.value < definition.hard_min:
            events.append(SignalEvent(
                session_id=session_id, pid=pid, event_type=SignalEventType.OUT_OF_RANGE,
                start_ms=cur.timestamp_ms, end_ms=cur.timestamp_ms, severity="HIGH",
                message=f"{pid} is below configured plausibility range.",
                evidence_fact=f"Measured {pid}={cur.value:g}{cur.unit or ''} below configured minimum {definition.hard_min:g}{cur.unit or ''}.",
                metrics={"value": cur.value, "hard_min": definition.hard_min},
            ))
        if definition and definition.hard_max is not None and cur.value > definition.hard_max:
            events.append(SignalEvent(
                session_id=session_id, pid=pid, event_type=SignalEventType.OUT_OF_RANGE,
                start_ms=cur.timestamp_ms, end_ms=cur.timestamp_ms, severity="HIGH",
                message=f"{pid} is above configured plausibility range.",
                evidence_fact=f"Measured {pid}={cur.value:g}{cur.unit or ''} above configured maximum {definition.hard_max:g}{cur.unit or ''}.",
                metrics={"value": cur.value, "hard_max": definition.hard_max},
            ))
        if definition and definition.step_threshold is not None and abs_dv >= definition.step_threshold:
            events.append(SignalEvent(
                session_id=session_id, pid=pid, event_type=SignalEventType.STEP_CHANGE,
                start_ms=prev.timestamp_ms, end_ms=cur.timestamp_ms, severity="MEDIUM",
                message=f"{pid} changed rapidly between consecutive samples.",
                evidence_fact=f"Measured {pid} changed by {dv:+g}{cur.unit or ''} in {dt} ms.",
                metrics={"delta": dv, "interval_ms": dt},
            ))
        if definition and definition.rate_threshold_per_second is not None and rate >= definition.rate_threshold_per_second:
            events.append(SignalEvent(
                session_id=session_id, pid=pid, event_type=SignalEventType.RATE_SPIKE,
                start_ms=prev.timestamp_ms, end_ms=cur.timestamp_ms, severity="MEDIUM",
                message=f"{pid} rate of change exceeded configured threshold.",
                evidence_fact=f"Measured {pid} rate of change was {rate:.2f}{cur.unit or ''}/s.",
                metrics={"rate_per_second": rate, "threshold": definition.rate_threshold_per_second},
            ))
    return events
