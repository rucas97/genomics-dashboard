from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from app.deps import get_current_user, get_current_org, require_role
from app.services import orgs as svc
from app.services.audit import log_action

router = APIRouter(prefix="/orgs", tags=["orgs"])


class InviteRequest(BaseModel):
    email: EmailStr
    role: str = "viewer"


class RoleUpdate(BaseModel):
    role: str


class OrgSettings(BaseModel):
    name: str | None = None
    hipaa_enabled: bool | None = None
    gdpr_enabled: bool | None = None
    data_retention_days: int | None = None
    billing_email: str | None = None
    technical_contact: str | None = None


@router.get("/me")
async def my_org(org=Depends(get_current_org)):
    """Return the current user's org + their role."""
    return {
        "org": org.get("organizations") or {},
        "role": org.get("role"),
        "org_id": org.get("org_id"),
        "status": org.get("status"),
    }


@router.get("/me/members")
async def list_my_members(org=Depends(get_current_org)):
    return svc.list_members(org["org_id"])


@router.post("/me/invitations")
async def invite_member(
    body: InviteRequest,
    user=Depends(get_current_user),
    org=Depends(require_role("admin")),
):
    if body.role not in ("admin", "analyst", "viewer"):
        raise HTTPException(400, "Invalid role")

    inv = svc.create_invitation(org["org_id"], body.email, body.role, user.id)
    if not inv:
        raise HTTPException(500, "Failed to create invitation")

    log_action(user.id, "invite", "org_member", org["org_id"], {
        "email": body.email, "role": body.role,
    })
    return inv


@router.get("/me/invitations")
async def list_invitations(org=Depends(require_role("admin"))):
    return svc.list_invitations(org["org_id"])


@router.delete("/me/invitations/{invitation_id}")
async def revoke_invitation(
    invitation_id: str,
    user=Depends(get_current_user),
    org=Depends(require_role("admin")),
):
    ok = svc.revoke_invitation(invitation_id, org["org_id"])
    if not ok:
        raise HTTPException(500, "Failed to revoke")
    log_action(user.id, "revoke_invite", "org_member", org["org_id"], {
        "invitation_id": invitation_id,
    })
    return {"ok": True}


@router.put("/me/members/{user_id}/role")
async def update_role(
    user_id: str,
    body: RoleUpdate,
    user=Depends(get_current_user),
    org=Depends(require_role("admin")),
):
    if body.role not in ("owner", "admin", "analyst", "viewer"):
        raise HTTPException(400, "Invalid role")
    if user_id == user.id and body.role != "owner":
        raise HTTPException(400, "You cannot demote yourself")

    ok = svc.update_member_role(org["org_id"], user_id, body.role)
    if not ok:
        raise HTTPException(500, "Failed to update role")
    log_action(user.id, "change_role", "org_member", user_id, {"new_role": body.role})
    return {"ok": True}


@router.delete("/me/members/{user_id}")
async def remove_member(
    user_id: str,
    user=Depends(get_current_user),
    org=Depends(require_role("admin")),
):
    if user_id == user.id:
        raise HTTPException(400, "You cannot remove yourself")
    ok = svc.remove_member(org["org_id"], user_id)
    if not ok:
        raise HTTPException(500, "Failed to remove")
    log_action(user.id, "remove_member", "org_member", user_id, {})
    return {"ok": True}


@router.put("/me/settings")
async def update_settings(
    body: OrgSettings,
    user=Depends(get_current_user),
    org=Depends(require_role("admin")),
):
    patch = {k: v for k, v in body.dict().items() if v is not None}
    if not patch:
        raise HTTPException(400, "No settings provided")
    ok = svc.update_org_settings(org["org_id"], patch)
    if not ok:
        raise HTTPException(500, "Failed to update settings")
    log_action(user.id, "update_org_settings", "org", org["org_id"], patch)
    return {"ok": True}


@router.post("/accept/{token}")
async def accept_invite(token: str, user=Depends(get_current_user)):
    inv = svc.accept_invitation(token, user.id)
    if not inv:
        raise HTTPException(400, "Invalid or expired invitation")
    log_action(user.id, "accept_invite", "org_member", inv["org_id"], {
        "role": inv["role"],
    })
    return {"ok": True, "org_id": inv["org_id"]}
