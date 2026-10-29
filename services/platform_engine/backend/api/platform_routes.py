from uuid import UUID
from fastapi import APIRouter
from professional_platform.models import Role
from professional_platform.service import WorkshopPlatform

router = APIRouter(prefix="/api/v1/platform", tags=["professional-platform"])
platform = WorkshopPlatform()

@router.get("/roles")
def roles():
    return {"roles": [r.value for r in Role]}

@router.get("/organizations/{organization_id}/audit")
def audit(organization_id: UUID):
    return [e.model_dump(mode="json") for e in platform.audit if e.organization_id == organization_id]
