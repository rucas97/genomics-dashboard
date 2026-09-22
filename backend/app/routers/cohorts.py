from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from app.supabase_client import supabase
from app.deps import get_current_user
from app.services.audit import log_action
from app.services.cohort import compute_pca

router = APIRouter(prefix="/cohorts", tags=["cohorts"])


class CohortCreate(BaseModel):
    name: str
    description: str | None = None
    sample_ids: list[str]


@router.get("/")
async def list_cohorts(user=Depends(get_current_user)):
    resp = supabase.table("cohorts").select("*").order("created_at", desc=True).execute()
    return resp.data


@router.post("/")
async def create_cohort(body: CohortCreate, user=Depends(get_current_user)):
    if not body.sample_ids:
        raise HTTPException(400, "At least one sample is required")
    if len(body.sample_ids) < 2:
        raise HTTPException(400, "At least 2 samples are required for a cohort")

    resp = supabase.table("cohorts").insert({
        "name": body.name,
        "description": body.description,
        "sample_ids": body.sample_ids,
        "created_by": user.id,
    }).execute()

    if not resp.data:
        raise HTTPException(500, "Failed to create cohort")

    cohort_id = resp.data[0]["id"]
    log_action(user.id, "create", "cohort", cohort_id, {"name": body.name, "n_samples": len(body.sample_ids)})
    return resp.data[0]


@router.get("/{cohort_id}")
async def get_cohort(cohort_id: str, user=Depends(get_current_user)):
    resp = supabase.table("cohorts").select("*").eq("id", cohort_id).execute()
    if not resp.data:
        raise HTTPException(404, "Cohort not found")
    log_action(user.id, "view", "cohort", cohort_id)
    return resp.data[0]


@router.get("/{cohort_id}/pca")
async def cohort_pca(cohort_id: str, user=Depends(get_current_user)):
    resp = supabase.table("cohorts").select("*").eq("id", cohort_id).execute()
    if not resp.data:
        raise HTTPException(404, "Cohort not found")

    cohort = resp.data[0]
    sample_ids = cohort.get("sample_ids") or []
    if len(sample_ids) < 2:
        raise HTTPException(400, "Need at least 2 samples for PCA")

    result = compute_pca(sample_ids)
    log_action(user.id, "run_pca", "cohort", cohort_id, {"n_samples": len(sample_ids)})
    return result


@router.delete("/{cohort_id}")
async def delete_cohort(cohort_id: str, user=Depends(get_current_user)):
    supabase.table("cohorts").delete().eq("id", cohort_id).execute()
    log_action(user.id, "delete", "cohort", cohort_id)
    return {"ok": True}
