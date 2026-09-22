from fastapi import Header, HTTPException, Depends
from supabase import create_client
from app.config import settings
from app.services.orgs import get_user_org

_auth_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


async def get_current_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth header")
    token = authorization.replace("Bearer ", "")
    try:
        res = _auth_client.auth.get_user(token)
        if not res or not res.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return res.user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Auth failed: {e}")


async def get_current_org(user=Depends(get_current_user)):
    """Return the user's org membership row, including the org itself."""
    org = get_user_org(user.id)
    if not org:
        raise HTTPException(status_code=403, detail="No organization membership")
    return org


def require_role(required: str):
    """FastAPI dependency factory for role-gated endpoints."""
    async def checker(org=Depends(get_current_org)):
        ranks = {"owner": 4, "admin": 3, "analyst": 2, "viewer": 1}
        if ranks.get(org.get("role"), 0) < ranks.get(required, 0):
            raise HTTPException(
                status_code=403,
                detail=f"This action requires {required} role or higher",
            )
        return org
    return checker
