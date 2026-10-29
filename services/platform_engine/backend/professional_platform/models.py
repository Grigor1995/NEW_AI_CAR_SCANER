from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    TECHNICIAN = "technician"
    VIEWER = "viewer"

class SubscriptionPlan(str, Enum):
    TRIAL = "trial"
    WORKSHOP = "workshop"
    FLEET = "fleet"
    ENTERPRISE = "enterprise"

class Organization(BaseModel):
    organization_id: UUID = Field(default_factory=uuid4)
    name: str
    slug: str
    active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Membership(BaseModel):
    membership_id: UUID = Field(default_factory=uuid4)
    organization_id: UUID
    user_id: UUID
    role: Role
    active: bool = True


class Fleet(BaseModel):
    fleet_id: UUID = Field(default_factory=uuid4)
    organization_id: UUID
    name: str
    description: str | None = None

class FleetVehicle(BaseModel):
    fleet_id: UUID
    vehicle_id: UUID
    nickname: str | None = None

class Subscription(BaseModel):
    subscription_id: UUID = Field(default_factory=uuid4)
    organization_id: UUID
    plan: SubscriptionPlan = SubscriptionPlan.TRIAL
    status: str = "active"
    seat_limit: int = 3
    vehicle_limit: int = 50
    renews_at: datetime | None = None

class AuditEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    organization_id: UUID
    actor_user_id: UUID | None = None
    action: str
    resource_type: str
    resource_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UsageSnapshot(BaseModel):
    organization_id: UUID
    period: str
    active_technicians: int = 0
    active_vehicles: int = 0
    diagnostic_sessions: int = 0
    completed_sessions: int = 0
    dtcs_read: int = 0
    ai_analyses: int = 0
    offline_sync_operations: int = 0
