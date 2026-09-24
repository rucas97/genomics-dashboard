from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.deps import get_current_user
from app.user import CurrentUser
from app.services.license import (
    get_license_status,
    activate_license,
    deactivate_license,
    get_machine_fingerprint,
    TIERS,
)

router = APIRouter(prefix="/license", tags=["license"])


@router.get("/status")
async def status():
    """Public endpoint — no auth required. Frontend polls this on startup."""
    return get_license_status()


@router.get("/machine")
async def machine():
    """Return the machine fingerprint. Used for offline activation."""
    return {"machine_fingerprint": get_machine_fingerprint()}


@router.get("/tiers")
async def list_tiers():
    return [{"id": k, **v} for k, v in TIERS.items()]


class ActivateRequest(BaseModel):
    token: dict


@router.post("/activate")
async def activate(body: ActivateRequest, user: CurrentUser = Depends(get_current_user)):
    result = activate_license(body.token)
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "Activation failed"))
    return result


@router.post("/deactivate")
async def deactivate(user: CurrentUser = Depends(get_current_user)):
    return deactivate_license()
