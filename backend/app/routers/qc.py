from fastapi import APIRouter, Depends
from app.supabase_client import supabase
from app.deps import get_current_user

router = APIRouter(prefix="/qc", tags=["qc"])

@router.get("/{sample_id}")
async def get_qc(sample_id: str, user=Depends(get_current_user)):
    resp = supabase.table("qc_metrics").select("*").eq("sample_id", sample_id).execute()
    return resp.data
