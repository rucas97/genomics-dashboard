from fastapi import APIRouter, Depends
from app.supabase_client import supabase
from app.deps import get_current_user

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/")
async def list_reports(user=Depends(get_current_user)):
    return supabase.table("reports").select("*").order("created_at", desc=True).execute().data
