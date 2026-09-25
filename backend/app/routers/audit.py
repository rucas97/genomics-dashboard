from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from app.config import settings
from app.db import get_db
from app.deps import get_current_user
from app.user import CurrentUser
from app.services.audit import log_action

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/")
async def list_audit(
    limit: int = Query(500, le=2000),
    user: CurrentUser = Depends(get_current_user),
):
    db = get_db()
    if user.role == "admin":
        return db.list_audit(limit=limit)
    return db.list_audit(user_id=user.id, limit=limit)


@router.delete("/")
async def clear_audit(user: CurrentUser = Depends(get_current_user)):
    """Clear the entire audit log. Admin-only. Leaves one entry recording the clear."""
    if user.role != "admin":
        raise HTTPException(403, "Admin role required")

    db = get_db()
    if settings.is_local:
        count = db.clear_audit()
    else:
        count = db.clear_audit(user_id=user.id)

    log_action(user.id, "clear_audit", "audit_log", None, {"rows_deleted": count})
    return {"ok": True, "deleted": count}


class BulkAuditDeleteRequest(BaseModel):
    ids: list[str]


@router.post("/bulk-delete")
async def bulk_delete_audit(
    body: BulkAuditDeleteRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Delete specific audit entries in one batch. Admin-only."""
    if user.role != "admin":
        raise HTTPException(403, "Admin role required")

    if not body.ids:
        return {"ok": True, "deleted": 0}

    db = get_db()
    deleted = 0

    try:
        if settings.is_local:
            con = db._conn()
            placeholders = ",".join(["?"] * len(body.ids))
            cur = con.execute(f"DELETE FROM audit_log WHERE id IN ({placeholders})", body.ids)
            deleted = cur.rowcount
            con.commit()
            con.close()
        else:
            from app.supabase_client import supabase
            r = supabase.table("audit_log").delete().in_("id", body.ids).execute()
            deleted = len(r.data or [])
    except Exception as e:
        print(f"Bulk audit delete failed: {e}")
        raise HTTPException(500, f"Delete failed: {e}")

    log_action(user.id, "delete", "audit_log", None, {"bulk": True, "count": deleted})
    return {"ok": True, "deleted": deleted}
