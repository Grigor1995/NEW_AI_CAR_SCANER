from uuid import uuid4
import pytest
from professional_platform.models import Role
from professional_platform.service import WorkshopPlatform
from professional_platform.rbac import AuthorizationError

def test_create_org_owner_and_subscription():
    p = WorkshopPlatform(); user = uuid4()
    org = p.create_organization("Demo Workshop", "demo-workshop", user)
    assert org.name == "Demo Workshop"
    assert p.subscriptions[org.organization_id].plan.value == "trial"
    assert len(p.memberships) == 1

def test_admin_can_add_member_and_create_fleet():
    p = WorkshopPlatform(); owner = uuid4(); tech = uuid4()
    org = p.create_organization("Workshop", "workshop", owner)
    owner_membership = next(iter(p.memberships.values()))
    p.add_member(owner_membership, tech, Role.TECHNICIAN)
    fleet = p.create_fleet(owner_membership, "Fleet A")
    assert fleet.organization_id == org.organization_id

def test_technician_can_assign_vehicle():
    p = WorkshopPlatform(); owner = uuid4(); tech = uuid4(); vehicle = uuid4()
    p.create_organization("Workshop", "workshop", owner)
    owner_m = next(iter(p.memberships.values()))
    tech_m = p.add_member(owner_m, tech, Role.TECHNICIAN)
    fleet = p.create_fleet(owner_m, "Fleet")
    assignment = p.assign_vehicle(tech_m, fleet.fleet_id, vehicle, "My W211")
    assert assignment.vehicle_id == vehicle

def test_viewer_cannot_create_fleet():
    p = WorkshopPlatform(); owner = uuid4(); viewer = uuid4()
    p.create_organization("Workshop", "workshop", owner)
    owner_m = next(iter(p.memberships.values()))
    viewer_m = p.add_member(owner_m, viewer, Role.VIEWER)
    with pytest.raises(AuthorizationError):
        p.create_fleet(viewer_m, "Forbidden")
