from uuid import uuid4

import pytest

from professional_platform.models import Membership, Role
from professional_platform.rbac import (
    AuthorizationError,
    can_manage_workshop,
    can_modify_diagnostics,
    can_read,
    require_role,
)


def _membership(role: Role, active: bool = True) -> Membership:
    return Membership(organization_id=uuid4(), user_id=uuid4(), role=role, active=active)


def test_require_role_allows_equal_or_higher_active_role():
    require_role(_membership(Role.TECHNICIAN), Role.TECHNICIAN)
    require_role(_membership(Role.OWNER), Role.ADMIN)


def test_require_role_rejects_inactive_membership_and_insufficient_role():
    with pytest.raises(AuthorizationError, match="inactive"):
        require_role(_membership(Role.OWNER, active=False), Role.VIEWER)
    with pytest.raises(AuthorizationError, match="cannot perform"):
        require_role(_membership(Role.VIEWER), Role.TECHNICIAN)


@pytest.mark.parametrize(
    ("role", "expected_modify", "expected_manage"),
    [
        (Role.VIEWER, False, False),
        (Role.TECHNICIAN, True, False),
        (Role.ADMIN, True, True),
        (Role.OWNER, True, True),
    ],
)
def test_capability_helpers_follow_role_order(role, expected_modify, expected_manage):
    membership = _membership(role)
    assert can_read(membership) is True
    assert can_modify_diagnostics(membership) is expected_modify
    assert can_manage_workshop(membership) is expected_manage


def test_inactive_membership_has_no_capabilities():
    membership = _membership(Role.OWNER, active=False)
    assert can_read(membership) is False
    assert can_modify_diagnostics(membership) is False
    assert can_manage_workshop(membership) is False
