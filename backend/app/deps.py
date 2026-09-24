"""
Auth dependencies that work in both cloud and local modes.

Cloud mode: bearer token is a Supabase JWT. Org context comes from org_members.
Local mode: bearer token is our own JWT. Single-user org — no org isolation.
"""
from fastapi import Depends, HTTPException, Header
from app.config import settings
from app.auth_scheme import bearer_scheme, _auth_client
from app.user import CurrentUser, from_supabase_user, from_local_user
from app.db import get_db


async def get_current_user(authorization: str = Header(None)) -> CurrentUser:
    """
    Return the authenticated user as a CurrentUser object.
    Works in both modes.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.replace("Bearer ", "")

    if settings.is_local:
        # Local mode: decode our own JWT
        from app.services.local_auth import decode_token
        payload = decode_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        db = get_db()
        row = db.get_user_by_id(payload["sub"])
        if not row:
            raise HTTPException(status_code=401, detail="User not found")
        return from_local_user(row)

    # Cloud mode: Supabase JWT
    try:
        res = _auth_client.auth.get_user(token)
        if not res or not res.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return from_supabase_user(res.user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Auth failed: {e}")


async def get_current_org(user: CurrentUser = Depends(get_current_user)) -> dict:
    """
    In cloud mode: returns the user's org membership row.
    In local mode: returns a fake single-user org so existing code keeps working.
    """
    if settings.is_local:
        # Local mode: single-user "org" — every action is scoped to this user
        return {
            "org_id": "local",
            "user_id": user.id,
            "role": user.role,
            "status": "active",
            "organizations": {"name": "Local Installation", "slug": "local"},
        }

    # Cloud mode
    from app.services.orgs import get_user_org
    org = get_user_org(user.id)
    if not org:
        raise HTTPException(status_code=403, detail="No organization membership")
    return org


def require_role(required: str):
    """
    Dependency factory.
    Cloud: checks role in org_members.
    Local: checks user.role directly.
    """
    async def checker(
        user: CurrentUser = Depends(get_current_user),
        org: dict = Depends(get_current_org),
    ):
        ranks = {"owner": 4, "admin": 3, "analyst": 2, "viewer": 1}
        role = user.role if settings.is_local else org.get("role")
        if ranks.get(role, 0) < ranks.get(required, 0):
            raise HTTPException(
                status_code=403,
                detail=f"This action requires {required} role or higher",
            )
        return org

    return checker
