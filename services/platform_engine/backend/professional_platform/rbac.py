from .models import Membership, Role

ROLE_ORDER = {Role.VIEWER: 10, Role.TECHNICIAN: 20, Role.ADMIN: 30, Role.OWNER: 40}

class AuthorizationError(PermissionError):
    pass

def require_role(membership: Membership, minimum: Role) -> None:
    if not membership.active:
        raise AuthorizationError("Membership is inactive")
    if ROLE_ORDER[membership.role] < ROLE_ORDER[minimum]:
        raise AuthorizationError(f"Role {membership.role.value} cannot perform {minimum.value}-level action")

def can_read(membership: Membership) -> bool:
    return membership.active

def can_modify_diagnostics(membership: Membership) -> bool:
    return membership.active and ROLE_ORDER[membership.role] >= ROLE_ORDER[Role.TECHNICIAN]

def can_manage_workshop(membership: Membership) -> bool:
    return membership.active and ROLE_ORDER[membership.role] >= ROLE_ORDER[Role.ADMIN]
