"""Durable ownership/consent service reusing the canonical vehicle and staff roles."""
from datetime import timedelta, timezone
from uuid import UUID

from sqlalchemy import insert, select, update
from professional_platform.models import Membership, Role
from professional_platform.rbac import AuthorizationError, require_role

from .errors import DomainError
from .models import Account, AccountRole, AuditEvent, Consent, Invitation, Ownership, ServiceCenter, Staff, profiles, uid, utcnow

PRIMARY_MODES = ('USER', 'CUSTOMER', 'ADMIN')


def current_roles(db, account):
    return sorted(db.scalars(select(AccountRole.role).where(AccountRole.account_id == account.id)))


def account_view(db, account):
    roles = current_roles(db, account)
    return dict(id=account.id, full_name=account.full_name, email=account.email, mobile=account.mobile,
                language=account.language, timezone=account.timezone, email_verified=account.email_verified,
                mobile_verified=account.mobile_verified, roles=roles,
                modes=[mode for mode in PRIMARY_MODES if mode in roles], portals=['MARKET'] if 'MARKET' in roles else [])


def record(db, actor, action, target):
    db.add(AuditEvent(actor_id=actor.id, action=action, target_id=str(target)))


def as_utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def staff_access(db, account, center_id, minimum=Role.VIEWER):
    center = db.get(ServiceCenter, center_id)
    staff = db.get(Staff, (center_id, account.id))
    if center is None or not center.active or staff is None or not staff.active:
        raise DomainError('not_found', 404)
    if 'CUSTOMER' not in current_roles(db, account):
        raise DomainError('forbidden')
    membership = Membership(organization_id=UUID(center_id), user_id=UUID(account.id), role=Role(staff.role), active=staff.active)
    try:
        require_role(membership, minimum)
    except AuthorizationError as error:
        raise DomainError('forbidden') from error
    return center


def owned_vehicles(db, account):
    return list(db.scalars(select(profiles.c.payload).join(Ownership, Ownership.profile_id == profiles.c.id)
                           .where(Ownership.account_id == account.id)))


def add_vehicle(db, account, data):
    profile_id = uid()
    payload = {'id': profile_id, 'name': data.name, 'vehicle': data.vehicle.model_dump(mode='json')}
    db.execute(insert(profiles).values(id=profile_id, payload=payload))
    db.add(Ownership(profile_id=profile_id, account_id=account.id))
    record(db, account, 'VEHICLE_CREATED', profile_id)
    db.commit()
    return payload


def create_center(db, account, data):
    center = ServiceCenter(**data.model_dump())
    db.add(center)
    db.flush()
    db.add(Staff(center_id=center.id, account_id=account.id, role=Role.OWNER.value))
    if 'CUSTOMER' not in current_roles(db, account):
        db.add(AccountRole(account_id=account.id, role='CUSTOMER'))
    record(db, account, 'SERVICE_CENTER_CREATED', center.id)
    db.commit()
    return {'id': center.id, 'name': center.name, 'verified': center.verified}


def invite(db, account, center_id, target_id):
    staff_access(db, account, center_id, Role.ADMIN)
    target = db.get(Account, target_id)
    if target is None or not target.active:
        raise DomainError('not_found', 404)
    invitation = Invitation(center_id=center_id, account_id=target_id, expires_at=utcnow() + timedelta(days=7))
    db.add(invitation)
    db.flush()
    record(db, account, 'INVITATION_CREATED', invitation.id)
    db.commit()
    return {'id': invitation.id, 'expires_at': invitation.expires_at}


def accept(db, account, invitation_id, data):
    invitation = db.get(Invitation, invitation_id)
    if invitation is None or invitation.account_id != account.id:
        raise DomainError('not_found', 404)
    center = db.get(ServiceCenter, invitation.center_id)
    if as_utc(invitation.expires_at) <= utcnow() or center is None or not center.active:
        raise DomainError('forbidden')
    if invitation.accepted_at is not None:
        raise DomainError('conflict', 409)
    profile_id = str(data.profile_id)
    ownership = db.get(Ownership, profile_id)
    if ownership is None or ownership.account_id != account.id:
        raise DomainError('not_found', 404)
    claimed = db.execute(update(Invitation).where(Invitation.id == invitation.id, Invitation.accepted_at.is_(None), Invitation.expires_at > utcnow())
                         .values(accepted_at=utcnow()).execution_options(synchronize_session=False))
    if claimed.rowcount != 1:
        raise DomainError('conflict', 409)
    grant = db.scalar(select(Consent).where(Consent.owner_id == account.id, Consent.center_id == invitation.center_id,
                                          Consent.profile_id == profile_id))
    if grant is None:
        grant = Consent(owner_id=account.id, center_id=invitation.center_id, profile_id=profile_id, invitation_id=invitation.id)
        db.add(grant)
    grant.invitation_id = invitation.id
    grant.scopes = sorted(set(data.scopes))
    grant.expires_at = utcnow() + timedelta(days=data.expires_in_days)
    grant.revoked = False
    db.flush()
    record(db, account, 'CONSENT_GRANTED', grant.id)
    db.commit()
    return consent_view(grant, center)


def consent_view(grant, center):
    return dict(id=grant.id, center_id=grant.center_id, center_name=center.name, center_verified=center.verified, profile_id=grant.profile_id,
                scopes=grant.scopes, expires_at=grant.expires_at, revoked=grant.revoked)


def read_shared_vehicle(db, account, center_id, profile_id):
    staff_access(db, account, center_id)
    grant = db.scalar(select(Consent).where(Consent.center_id == center_id, Consent.profile_id == profile_id))
    ownership = db.get(Ownership, profile_id)
    owner = db.get(Account, grant.owner_id) if grant else None
    if (grant is None or grant.revoked or as_utc(grant.expires_at) <= utcnow() or 'vehicle:read' not in grant.scopes
            or ownership is None or ownership.account_id != grant.owner_id or owner is None or not owner.active):
        raise DomainError('not_found', 404)
    payload = db.scalar(select(profiles.c.payload).where(profiles.c.id == profile_id))
    if payload is None:
        raise DomainError('not_found', 404)
    # Do not disclose the owner's profile nickname, personal contact or arbitrary metadata.
    from diagnostic.models import Vehicle
    vehicle = Vehicle.model_validate(payload['vehicle']).model_dump(exclude={'metadata'})
    record(db, account, 'SHARED_VEHICLE_READ', profile_id)
    db.commit()
    return {'id': profile_id, 'vehicle': vehicle}
