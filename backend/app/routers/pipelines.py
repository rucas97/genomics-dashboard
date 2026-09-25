from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from app.db import get_db
from app.deps import get_current_user, get_current_org
from app.user import CurrentUser
from app.services.audit import log_action
from app.services.pipelines import list_pipelines, run_pipeline, PIPELINES

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


class RunRequest(BaseModel):
    pipeline_id: str
    sample_id: str


@router.get("/")
async def list_runs(user: CurrentUser = Depends(get_current_user), org=Depends(get_current_org)):
    db = get_db()
    return db.list_pipeline_runs(user.id)


@router.get("/available")
async def available(user: CurrentUser = Depends(get_current_user)):
    return list_pipelines()


@router.post("/run")
async def start_run(
    body: RunRequest,
    background: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
    org=Depends(get_current_org),
):
    db = get_db()
    if body.pipeline_id not in PIPELINES:
        raise HTTPException(400, f"Unknown pipeline: {body.pipeline_id}")

    sample = db.get_sample(body.sample_id)
    if not sample:
        raise HTTPException(404, "Sample not found")

    run = db.create_pipeline_run({
        "user_id": user.id,
        "sample_id": body.sample_id,
        "pipeline_name": PIPELINES[body.pipeline_id]["name"],
        "status": "queued",
    })

    run_id = run["id"]
    log_action(user.id, "run_pipeline", "pipeline_run", run_id, {
        "pipeline": body.pipeline_id,
        "sample_id": body.sample_id,
    })

    background.add_task(run_pipeline, run_id, body.pipeline_id, body.sample_id)
    return {"run_id": run_id, "status": "queued"}


@router.get("/{run_id}")
async def get_run(run_id: str, user: CurrentUser = Depends(get_current_user)):
    db = get_db()
    run = db.get_pipeline_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return run


@router.delete("/{run_id}")
async def delete_run(run_id: str, user: CurrentUser = Depends(get_current_user)):
    db = get_db()
    run = db.get_pipeline_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    db.delete_pipeline_run(run_id)
    log_action(user.id, "delete", "pipeline_run", run_id, {"name": run.get("pipeline_name")})
    return {"ok": True}


from pydantic import BaseModel as _BulkBase

class BulkRunDeleteRequest(_BulkBase):
    ids: list[str]

@router.post("/bulk-delete")
async def bulk_delete_runs(
    body: BulkRunDeleteRequest,
    user: CurrentUser = Depends(get_current_user),
    org=Depends(get_current_org),
):
    db = get_db()
    deleted = 0
    for rid in body.ids:
        run = db.get_pipeline_run(rid)
        if not run:
            continue
        db.delete_pipeline_run(rid)
        log_action(user.id, "delete", "pipeline_run", rid, {"bulk": True, "name": run.get("pipeline_name")})
        deleted += 1
    return {"ok": True, "deleted": deleted}
