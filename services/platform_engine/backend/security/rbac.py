ROLE_PERMISSIONS = {
    "owner": {"*"},
    "admin": {"session:read","session:write","vehicle:read","vehicle:write","report:read","report:write","device:manage","member:manage"},
    "technician": {"session:read","session:write","vehicle:read","vehicle:write","report:read","report:write","device:use"},
    "viewer": {"session:read","vehicle:read","report:read"},
}

def allowed(roles: tuple[str, ...], permission: str) -> bool:
    return any("*" in ROLE_PERMISSIONS.get(role, set()) or permission in ROLE_PERMISSIONS.get(role, set()) for role in roles)
