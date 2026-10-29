from __future__ import annotations
from collections import defaultdict
from uuid import UUID
from .analysis import compute_stats, detect_events
from .channels import channel_name
from .models import TelemetrySample, TelemetrySummary


class TelemetryService:
    """In-memory streaming facade; PostgreSQL/time-series persistence can be attached without changing callers."""

    def __init__(self):
        self._samples: dict[UUID, list[TelemetrySample]] = defaultdict(list)

    def append(self, samples: list[TelemetrySample]) -> int:
        for sample in samples:
            bucket = self._samples[sample.session_id]
            bucket.append(sample)
        return len(samples)

    def samples(self, session_id: UUID, pid: str | None = None) -> list[TelemetrySample]:
        items = self._samples.get(session_id, [])
        if pid is not None:
            items = [x for x in items if x.pid == pid]
        return sorted(items, key=lambda x: (x.timestamp_ms, x.sequence or -1))

    def summarize(self, session_id: UUID) -> TelemetrySummary:
        items = self.samples(session_id)
        grouped: dict[str, list[TelemetrySample]] = defaultdict(list)
        for item in items:
            grouped[item.pid].append(item)
        stats = []
        events = []
        for pid, signal_samples in sorted(grouped.items()):
            signal_stats = compute_stats(session_id, pid, signal_samples)
            signal_stats.display_name = channel_name(pid)
            signal_events = detect_events(session_id, pid, signal_samples)
            signal_stats.anomaly_count = sum(1 for e in signal_events if e.event_type.value in {"STEP_CHANGE", "RATE_SPIKE", "OUT_OF_RANGE"})
            signal_stats.event_count = len(signal_events)
            stats.append(signal_stats)
            events.extend(signal_events)
        return TelemetrySummary(
            session_id=session_id,
            sample_count=len(items),
            signal_count=len(grouped),
            start_ms=items[0].timestamp_ms if items else None,
            end_ms=items[-1].timestamp_ms if items else None,
            stats=stats,
            events=events,
        )
