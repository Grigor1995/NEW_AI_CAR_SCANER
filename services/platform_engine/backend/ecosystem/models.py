"""Additive identity tables; vehicle payloads stay in the existing profile table."""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, JSON, String, Table, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def uid():
    return str(uuid4())


def utcnow():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# Reference the legacy two-column SQL contract, not a second vehicle/catalog model.
profiles = Table('vehicle_profiles', Base.metadata,
                 Column('id', String(64), primary_key=True), Column('payload', JSON, nullable=False),
                 info={'legacy': True})


class Account(Base):
    __tablename__ = 'ecosystem_accounts'
    __table_args__ = (CheckConstraint("language IN ('en','hy','ru')", name='ck_eco_language'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    full_name: Mapped[str] = mapped_column(String(200))
    mobile: Mapped[str | None] = mapped_column(String(20), nullable=True)
    language: Mapped[str] = mapped_column(String(2), default='en')
    timezone: Mapped[str] = mapped_column(String(100), default='UTC')
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    mobile_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AccountRole(Base):
    __tablename__ = 'ecosystem_account_roles'
    __table_args__ = (CheckConstraint("role IN ('USER','CUSTOMER','ADMIN','MARKET')", name='ck_eco_role'),)
    account_id: Mapped[str] = mapped_column(ForeignKey('ecosystem_accounts.id', ondelete='CASCADE'), primary_key=True)
    role: Mapped[str] = mapped_column(String(16), primary_key=True)


class AuthSession(Base):
    __tablename__ = 'ecosystem_auth_sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey('ecosystem_accounts.id', ondelete='CASCADE'), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class ServiceCenter(Base):
    __tablename__ = 'ecosystem_service_centers'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(200))
    address: Mapped[str] = mapped_column(String(500))
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Staff(Base):
    __tablename__ = 'ecosystem_staff'
    __table_args__ = (CheckConstraint("role IN ('owner','admin','technician','viewer')", name='ck_eco_staff_role'),)
    center_id: Mapped[str] = mapped_column(ForeignKey('ecosystem_service_centers.id', ondelete='CASCADE'), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey('ecosystem_accounts.id', ondelete='CASCADE'), primary_key=True)
    role: Mapped[str] = mapped_column(String(16))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Ownership(Base):
    __tablename__ = 'ecosystem_vehicle_ownership'
    profile_id: Mapped[str] = mapped_column(ForeignKey('vehicle_profiles.id', ondelete='CASCADE'), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey('ecosystem_accounts.id', ondelete='CASCADE'), index=True)


class Invitation(Base):
    __tablename__ = 'ecosystem_invitations'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    center_id: Mapped[str] = mapped_column(ForeignKey('ecosystem_service_centers.id', ondelete='CASCADE'))
    account_id: Mapped[str] = mapped_column(ForeignKey('ecosystem_accounts.id', ondelete='CASCADE'), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Consent(Base):
    __tablename__ = 'ecosystem_access_consents'
    __table_args__ = (UniqueConstraint('owner_id', 'center_id', 'profile_id', name='uq_eco_vehicle_consent'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey('ecosystem_accounts.id', ondelete='CASCADE'), index=True)
    center_id: Mapped[str] = mapped_column(ForeignKey('ecosystem_service_centers.id', ondelete='CASCADE'), index=True)
    profile_id: Mapped[str] = mapped_column(ForeignKey('vehicle_profiles.id', ondelete='CASCADE'))
    invitation_id: Mapped[str] = mapped_column(ForeignKey('ecosystem_invitations.id', ondelete='CASCADE'))
    scopes: Mapped[list] = mapped_column(JSON)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class AuditEvent(Base):
    __tablename__ = 'ecosystem_audit_events'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey('ecosystem_accounts.id', ondelete='SET NULL'), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(80))
    target_id: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
