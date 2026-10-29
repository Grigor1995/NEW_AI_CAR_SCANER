from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass(frozen=True)
class SecurityAuditEvent:
    actor_id: str
    organization_id: str
    action: str
    resource: str
    timestamp: str
    outcome: str

def event(actor_id: str, organization_id: str, action: str, resource: str, outcome: str="success") -> SecurityAuditEvent:
    return SecurityAuditEvent(actor_id, organization_id, action, resource, datetime.now(timezone.utc).isoformat(), outcome)
