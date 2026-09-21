from fastapi import APIRouter, Depends, Query
from app.supabase_client import supabase
from app.deps import get_current_user

router = APIRouter(prefix="/audit", tags=["audit"])

@router.get("/")
async def list_audit(limit: int = Query(100, le=500), user=Depends(get_current_user)):
    resp = supabase.table("audit_log").select("*").order("created_at", desc=True).limit(limit).execute()
    return resp.data
