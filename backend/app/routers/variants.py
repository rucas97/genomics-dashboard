from fastapi import APIRouter, Depends, Query
from app.supabase_client import supabase
from app.deps import get_current_user

router = APIRouter(prefix="/variants", tags=["variants"])

@router.get("/")
async def list_variants(
    sample_id: str = None,
    gene: str = None,
    chrom: str = None,
    clinvar: str = None,
    limit: int = Query(100, le=1000),
    offset: int = 0,
    user=Depends(get_current_user),
):
    q = supabase.table("variants").select("*", count="exact")
    if sample_id:
        q = q.eq("sample_id", sample_id)
    if gene:
        q = q.eq("gene", gene)
    if chrom:
        q = q.eq("chrom", chrom)
    if clinvar:
        q = q.eq("clinvar_significance", clinvar)
    resp = q.range(offset, offset + limit - 1).execute()
    return {"data": resp.data, "count": resp.count}
