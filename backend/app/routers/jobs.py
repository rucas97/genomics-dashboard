import json
import sqlite3
import uuid
from fastapi import APIRouter, Depends, HTTPException
from app.config import settings
from app.deps import get_current_user
from app.user import CurrentUser

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _conn():
    con = sqlite3.connect(settings.LOCAL_DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    return con


def _create_job(user_id: str, kind: str, args: dict) -> str:
    job_id = str(uuid.uuid4())
    con = _conn()
    con.execute(
        "INSERT INTO jobs (id, user_id, kind, status, args) VALUES (?,?,?,?,?)",
        (job_id, user_id, kind, "queued", json.dumps(args))
    )
    con.commit()
    con.close()
    return job_id


@router.get("/")
async def list_jobs(user: CurrentUser = Depends(get_current_user)):
    con = _conn()
    cur = con.execute(
        "SELECT id, kind, status, args, result, error, created_at, started_at, finished_at "
        "FROM jobs WHERE user_id = ? ORDER BY created_at DESC LIMIT 100",
        (user.id,)
    )
    rows = cur.fetchall()
    con.close()
    jobs = [dict(r) for r in rows]
    for j in jobs:
        if j.get("args"):
            try: j["args"] = json.loads(j["args"])
            except: pass
        if j.get("result"):
            try: j["result"] = json.loads(j["result"])
            except: pass
    return jobs


@router.get("/{job_id}")
async def get_job(job_id: str, user: CurrentUser = Depends(get_current_user)):
    con = _conn()
    cur = con.execute("SELECT * FROM jobs WHERE id = ? AND user_id = ?", (job_id, user.id))
    row = cur.fetchone()
    con.close()
    if not row:
        raise HTTPException(404, "Job not found")
    j = dict(row)
    for k in ("args", "result"):
        if j.get(k):
            try: j[k] = json.loads(j[k])
            except: pass
    return j


@router.post("/process-vcf")
async def create_vcf_job(
    sample_id: str,
    provider: str,
    storage_path: str,
    user: CurrentUser = Depends(get_current_user),
):
    job_id = _create_job(user.id, "process_vcf", {
        "sample_id": sample_id,
        "provider": provider,
        "storage_path": storage_path,
    })
    return {"job_id": job_id, "status": "queued"}


@router.post("/annotate")
async def create_annotate_job(
    sample_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    job_id = _create_job(user.id, "annotate", {"sample_id": sample_id})
    return {"job_id": job_id, "status": "queued"}


@router.post("/report")
async def create_report_job(
    kind: str,
    resource_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    job_id = _create_job(user.id, "report", {"kind": kind, "resource_id": resource_id})
    return {"job_id": job_id, "status": "queued"}
