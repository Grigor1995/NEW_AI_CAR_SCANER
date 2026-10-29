from __future__ import annotations
from .models import TelemetrySummary
from diagnostic.models import Evidence, EvidenceSource, EvidenceStatus


def events_to_evidence(summary: TelemetrySummary) -> list[Evidence]:
    evidence: list[Evidence] = []
    for event in summary.events:
        status = EvidenceStatus.MEASURED
        evidence.append(Evidence(
            fact=event.evidence_fact,
            source=EvidenceSource.VEHICLE_MEASURED,
            status=status,
            confidence=0.98 if event.severity == "HIGH" else 0.9,
            source_ref=f"telemetry:{event.session_id}:{event.pid}:{event.event_type.value}:{event.start_ms}:{event.end_ms}",
            metadata={
                "pid": event.pid,
                "event_type": event.event_type.value,
                "start_ms": event.start_ms,
                "end_ms": event.end_ms,
                "metrics": event.metrics,
            },
        ))
    return evidence
