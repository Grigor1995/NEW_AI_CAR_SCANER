from uuid import UUID
from .models import Organization, Membership, Fleet, FleetVehicle, Subscription, Role, AuditEvent
from .rbac import require_role

class WorkshopPlatform:
    def __init__(self):
        self.organizations: dict[UUID, Organization] = {}
        self.memberships: dict[UUID, Membership] = {}
        self.fleets: dict[UUID, Fleet] = {}
        self.fleet_vehicles: list[FleetVehicle] = []
        self.subscriptions: dict[UUID, Subscription] = {}
        self.audit: list[AuditEvent] = []

    def create_organization(self, name: str, slug: str, owner_user_id: UUID) -> Organization:
        org = Organization(name=name, slug=slug)
        self.organizations[org.organization_id] = org
        membership = Membership(organization_id=org.organization_id, user_id=owner_user_id, role=Role.OWNER)
        self.memberships[membership.membership_id] = membership
        self.subscriptions[org.organization_id] = Subscription(organization_id=org.organization_id)
        self.record(org.organization_id, owner_user_id, "ORGANIZATION_CREATED", "organization", org.organization_id)
        return org

    def add_member(self, actor: Membership, user_id: UUID, role: Role) -> Membership:
        require_role(actor, Role.ADMIN)
        m = Membership(organization_id=actor.organization_id, user_id=user_id, role=role)
        self.memberships[m.membership_id] = m
        self.record(actor.organization_id, actor.user_id, "MEMBER_ADDED", "membership", m.membership_id)
        return m

    def create_fleet(self, actor: Membership, name: str, description: str | None = None) -> Fleet:
        require_role(actor, Role.ADMIN)
        f = Fleet(organization_id=actor.organization_id, name=name, description=description)
        self.fleets[f.fleet_id] = f
        self.record(actor.organization_id, actor.user_id, "FLEET_CREATED", "fleet", f.fleet_id)
        return f

    def assign_vehicle(self, actor: Membership, fleet_id: UUID, vehicle_id: UUID, nickname: str | None = None):
        require_role(actor, Role.TECHNICIAN)
        fleet = self.fleets[fleet_id]
        if fleet.organization_id != actor.organization_id:
            raise PermissionError("Fleet belongs to another organization")
        item = FleetVehicle(fleet_id=fleet_id, vehicle_id=vehicle_id, nickname=nickname)
        self.fleet_vehicles.append(item)
        self.record(actor.organization_id, actor.user_id, "VEHICLE_ASSIGNED_TO_FLEET", "vehicle", vehicle_id, {"fleet_id": str(fleet_id)})
        return item

    def record(self, organization_id, actor_user_id, action, resource_type, resource_id=None, metadata=None):
        event = AuditEvent(organization_id=organization_id, actor_user_id=actor_user_id, action=action, resource_type=resource_type, resource_id=resource_id, metadata=metadata or {})
        self.audit.append(event)
        return event
