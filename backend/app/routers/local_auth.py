from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from app.config import settings
from app.db import get_db
from app.services.local_auth import create_token, decode_token

router = APIRouter(prefix="/local-auth", tags=["local-auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class CreateUserRequest(BaseModel):
    email: str
    password: str
    name: str | None = None
    role: str = "viewer"


@router.get("/status")
async def status():
    """Tell the frontend whether local mode is on."""
    return {
        "mode": settings.MODE,
        "is_local": settings.is_local,
        "first_run": True,  # frontend can prompt to change admin password
    }


@router.post("/login")
async def login(body: LoginRequest):
    if not settings.is_local:
        raise HTTPException(400, "Local auth only available in local mode")
    db = get_db()
    user = db.verify_password(body.email, body.password)
    if not user:
        raise HTTPException(401, "Invalid email or password")
    token = create_token(user["id"], user["role"])
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user.get("name"),
            "role": user["role"],
        },
    }


@router.get("/me")
async def me(authorization: str = Header(...)):
    if not settings.is_local:
        raise HTTPException(400, "Local auth only available in local mode")
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid auth header")
    token = authorization.replace("Bearer ", "")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(401, "Invalid or expired token")
    db = get_db()
    user = db.get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(401, "User not found")
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user.get("name"),
        "role": user["role"],
    }


@router.get("/users")
async def list_users(authorization: str = Header(...)):
    if not settings.is_local:
        raise HTTPException(400, "Local auth only available in local mode")
    payload = _require_admin(authorization)
    db = get_db()
    return db.list_users()


@router.post("/users")
async def create_user(body: CreateUserRequest, authorization: str = Header(...)):
    if not settings.is_local:
        raise HTTPException(400, "Local auth only available in local mode")
    _require_admin(authorization)
    if body.role not in ("admin", "analyst", "viewer"):
        raise HTTPException(400, "Invalid role")
    db = get_db()
    try:
        user = db.create_user(body.email, body.password, body.role, body.name)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"id": user["id"], "email": user["email"], "role": user["role"]}


@router.put("/users/{user_id}/role")
async def update_role(user_id: str, role: str, authorization: str = Header(...)):
    if not settings.is_local:
        raise HTTPException(400, "Local auth only available in local mode")
    _require_admin(authorization)
    db = get_db()
    if not db.update_user_role(user_id, role):
        raise HTTPException(400, "Invalid role or user")
    return {"ok": True}


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, authorization: str = Header(...)):
    if not settings.is_local:
        raise HTTPException(400, "Local auth only available in local mode")
    _require_admin(authorization)
    db = get_db()
    if not db.delete_user(user_id):
        raise HTTPException(400, "Cannot delete the last admin")
    return {"ok": True}


def _require_admin(authorization: str) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid auth header")
    token = authorization.replace("Bearer ", "")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(401, "Invalid or expired token")
    if payload.get("role") != "admin":
        raise HTTPException(403, "Admin role required")
    return payload
