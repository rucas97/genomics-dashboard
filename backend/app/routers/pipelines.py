from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from app.supabase_client import supabase
from app.db import sb_select, sb_insert
from app.deps import get_current_user
from app.services.audit import log_action
from app.services.pipelines import list_pipelines, run_pipeline, PIPELINES

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


class RunRequest(BaseModel):
    pipeline_id: str
    sample_id: str


@router.get("/")
async def list_runs(user=Depends(get_current_user)):
    resp = sb_select("pipeline_runs", order="created_at", desc=True)
    return resp.data


@router.get("/available")
async def available(user=Depends(get_current_user)):
    return list_pipelines()


@router.post("/run")
async def start_run(body: RunRequest, background: BackgroundTasks, user=Depends(get_current_user)):
    if body.pipeline_id not in PIPELINES:
        raise HTTPException(400, f"Unknown pipeline: {body.pipeline_id}")

    sresp = supabase.table("samples").select("*").eq("id", body.sample_id).execute()
    if not sresp.data:
        raise HTTPException(404, "Sample not found")

    resp = sb_insert("pipeline_runs", {
        "sample_id": body.sample_id,
        "pipeline_name": PIPELINES[body.pipeline_id]["name"],
        "status": "queued",
        "created_by": user.id,
    })

    if not resp.data:
        raise HTTPException(500, "Failed to create run")

    run_id = resp.data[0]["id"]
    log_action(user.id, "run_pipeline", "pipeline_run", run_id, {
        "pipeline": body.pipeline_id,
        "sample_id": body.sample_id,
    })

    background.add_task(run_pipeline, run_id, body.pipeline_id, body.sample_id)
    return {"run_id": run_id, "status": "queued"}


@router.get("/{run_id}")
async def get_run(run_id: str, user=Depends(get_current_user)):
    resp = supabase.table("pipeline_runs").select("*").eq("id", run_id).execute()
    if not resp.data:
        raise HTTPException(404, "Run not found")
    return resp.data[0]
