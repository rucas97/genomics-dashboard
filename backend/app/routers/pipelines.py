from fastapi import APIRouter, Depends
from app.supabase_client import supabase
from app.deps import get_current_user

router = APIRouter(prefix="/pipelines", tags=["pipelines"])

@router.get("/")
async def list_runs(user=Depends(get_current_user)):
    return supabase.table("pipeline_runs").select("*").order("created_at", desc=True).execute().data
