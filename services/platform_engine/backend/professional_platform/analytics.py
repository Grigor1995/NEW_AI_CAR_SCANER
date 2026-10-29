from collections import Counter
from typing import Iterable
from .models import UsageSnapshot

def summarize_events(organization_id, period: str, events: Iterable[dict]) -> UsageSnapshot:
    rows = list(events)
    kinds = Counter(e.get("action") for e in rows)
    return UsageSnapshot(
        organization_id=organization_id,
        period=period,
        active_technicians=len({e.get("actor_user_id") for e in rows if e.get("actor_user_id")}),
        active_vehicles=len({e.get("vehicle_id") for e in rows if e.get("vehicle_id")}),
        diagnostic_sessions=kinds.get("SESSION_CREATED", 0),
        completed_sessions=kinds.get("SESSION_CLOSED", 0),
        dtcs_read=kinds.get("DTC_READ", 0),
        ai_analyses=kinds.get("AI_ANALYSIS_STARTED", 0),
        offline_sync_operations=kinds.get("SYNC_COMPLETED", 0),
    )
