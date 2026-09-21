from fastapi import APIRouter, Depends
from app.supabase_client import supabase
from app.deps import get_current_user

router = APIRouter(prefix="/cohorts", tags=["cohorts"])

@router.get("/")
async def list_cohorts(user=Depends(get_current_user)):
    return supabase.table("cohorts").select("*").execute().data
