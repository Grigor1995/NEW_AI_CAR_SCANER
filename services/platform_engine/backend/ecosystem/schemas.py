from datetime import datetime
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import re

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator
from diagnostic.models import Vehicle


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class ProfileFields(Input):
    full_name: str = Field(min_length=1, max_length=200)
    language: Literal['en', 'hy', 'ru'] = 'en'
    timezone: str = Field(default='UTC', max_length=100)
    mobile: str | None = Field(default=None, max_length=20)

    @field_validator('timezone')
    @classmethod
    def timezone_exists(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as error:
            raise ValueError('Use an IANA timezone') from error
        return value

    @field_validator('mobile')
    @classmethod
    def international_mobile(cls, value):
        if value is not None and not re.fullmatch(r'\+[1-9]\d{6,14}', value):
            raise ValueError('Use an international phone number')
        return value


class Register(ProfileFields):
    email: str = Field(min_length=3, max_length=254)
    password: SecretStr = Field(min_length=12, max_length=128)

    @field_validator('email')
    @classmethod
    def normalized_email(cls, value):
        value = value.casefold()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
            raise ValueError('Invalid email format')
        return value


class Login(Input):
    email: str = Field(min_length=3, max_length=254)
    password: SecretStr = Field(min_length=1, max_length=128)


class ProfilePatch(Input):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    language: Literal['en', 'hy', 'ru'] | None = None
    timezone: str | None = Field(default=None, max_length=100)
    mobile: str | None = Field(default=None, max_length=20)

    @model_validator(mode='after')
    def validate_fields(self):
        values = self.model_dump(exclude_unset=True)
        if any(value is None for key, value in values.items() if key != 'mobile'):
            raise ValueError('Profile fields cannot be null')
        if self.timezone is not None:
            ProfileFields.timezone_exists(self.timezone)
        ProfileFields.international_mobile(self.mobile)
        return self


class Workspace(Input):
    mode: Literal['USER', 'CUSTOMER', 'ADMIN']


class VehicleInput(Input):
    name: str = Field(default='', max_length=200)
    vehicle: Vehicle


class CenterInput(Input):
    name: str = Field(min_length=1, max_length=200)
    address: str = Field(min_length=1, max_length=500)
    phone: str | None = Field(default=None, max_length=20)

    @field_validator('phone')
    @classmethod
    def phone_valid(cls, value):
        return ProfileFields.international_mobile(value)


class InviteInput(Input):
    account_id: UUID


class AcceptInput(Input):
    profile_id: UUID
    expires_in_days: int = Field(default=7, ge=1, le=90)
    scopes: list[Literal['vehicle:read', 'report:read', 'live:read']] = Field(default_factory=lambda: ['vehicle:read', 'report:read'], min_length=1, max_length=3)


# Response contracts are explicit; secrets and internal SQL rows are never serialized.

class AccountOutput(BaseModel):
    id: UUID
    full_name: str
    email: str
    mobile: str | None
    language: Literal['en', 'hy', 'ru']
    timezone: str
    email_verified: bool
    mobile_verified: bool
    roles: list[Literal['USER', 'CUSTOMER', 'ADMIN', 'MARKET']]
    modes: list[Literal['USER', 'CUSTOMER', 'ADMIN']]
    portals: list[Literal['MARKET']]


class TokenOutput(BaseModel):
    access_token: str
    token_type: Literal['bearer']
    expires_in: int


class VehicleOutput(BaseModel):
    id: UUID
    vehicle: Vehicle


class OwnedVehicleOutput(VehicleOutput):
    name: str


class CenterOutput(BaseModel):
    id: UUID
    name: str
    verified: bool


class InviteOutput(BaseModel):
    id: UUID
    expires_at: datetime


class InboxInvitation(InviteOutput):
    center_id: UUID
    center_name: str
    center_verified: bool
    accepted: bool


class ConsentOutput(BaseModel):
    id: UUID
    center_id: UUID
    center_name: str
    center_verified: bool
    profile_id: UUID
    scopes: list[Literal['vehicle:read', 'report:read', 'live:read']]
    expires_at: datetime
    revoked: bool


class ErrorOutput(BaseModel):
    code: str
    detail: str
    fields: list[list[str | int]] | None = None
