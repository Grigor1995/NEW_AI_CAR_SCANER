from .models import AuditEvent

class AuditLog:
    def __init__(self):
        self.events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> AuditEvent:
        self.events.append(event)
        return event

    def for_organization(self, organization_id):
        return [e for e in self.events if e.organization_id == organization_id]
