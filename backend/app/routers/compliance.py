from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from app.deps import get_current_user, get_current_org, require_role
from app.services import compliance as svc
from app.services.audit import log_action

router = APIRouter(prefix="/compliance", tags=["compliance"])


class ConsentCreate(BaseModel):
    sample_id: str
    subject_id: str
    consent_type: str
    granted: bool = True
    granted_by: str | None = None
    expires_at: str | None = None
    notes: str | None = None


class PHITag(BaseModel):
    categories: list[str]


class LegalHold(BaseModel):
    hold: bool


class RetentionRequest(BaseModel):
    dry_run: bool = True


# ---------- SESSIONS ----------

@router.post("/session/touch")
async def touch_session(
    request: Request,
    user=Depends(get_current_user),
    org=Depends(get_current_org),
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    svc.record_activity(user.id, org["org_id"], ip, ua)
    return {"ok": True}


@router.get("/session/status")
async def session_status(user=Depends(get_current_user), org=Depends(get_current_org)):
    timeout = svc.get_org_session_timeout(org["org_id"])
    expired = svc.is_session_expired(user.id, org["org_id"], timeout)
    return {"timeout_minutes": timeout, "expired": expired}


# ---------- CONSENT ----------

@router.post("/consent")
async def create_consent(
    body: ConsentCreate,
    user=Depends(get_current_user),
    org=Depends(require_role("analyst")),
):
    record = svc.record_consent(
        org_id=org["org_id"],
        sample_id=body.sample_id,
        subject_id=body.subject_id,
        consent_type=body.consent_type,
        granted=body.granted,
        granted_by=body.granted_by,
        expires_at=body.expires_at,
        notes=body.notes,
    )
    if not record:
        raise HTTPException(500, "Failed to record consent")

    log_action(user.id, "record_consent", "sample", body.sample_id, {
        "consent_type": body.consent_type, "granted": body.granted,
    })
    return record


@router.get("/consent")
async def list_consent(
    sample_id: str = None,
    user=Depends(get_current_user),
    org=Depends(get_current_org),
):
    return svc.list_consent(org["org_id"], sample_id)


@router.delete("/consent/{consent_id}")
async def revoke_consent(
    consent_id: str,
    reason: str = None,
    user=Depends(get_current_user),
    org=Depends(require_role("analyst")),
):
    ok = svc.revoke_consent(consent_id, org["org_id"], reason)
    if not ok:
        raise HTTPException(500, "Failed to revoke")
    log_action(user.id, "revoke_consent", "consent", consent_id, {"reason": reason})
    return {"ok": True}


# ---------- RIGHT TO ERASURE ----------

@router.post("/erase/sample/{sample_id}")
async def erase_sample(
    sample_id: str,
    user=Depends(get_current_user),
    org=Depends(require_role("admin")),
):
    result = svc.erase_sample(sample_id, org["org_id"], user.id)
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "Erase failed"))
    return result


# ---------- RETENTION ----------

@router.post("/retention/run")
async def run_retention(
    body: RetentionRequest,
    user=Depends(get_current_user),
    org=Depends(require_role("admin")),
):
    result = svc.apply_retention_policy(org["org_id"], dry_run=body.dry_run)
    log_action(user.id, "retention_run", "org", org["org_id"], {
        "dry_run": body.dry_run, "result": result,
    })
    return result


@router.get("/retention/runs")
async def list_retention_runs(user=Depends(get_current_user), org=Depends(get_current_org)):
    return svc.list_retention_runs(org["org_id"])


# ---------- PHI / LEGAL HOLD ----------

@router.post("/phi/{sample_id}")
async def tag_phi(
    sample_id: str,
    body: PHITag,
    user=Depends(get_current_user),
    org=Depends(require_role("analyst")),
):
    ok = svc.tag_phi(sample_id, org["org_id"], body.categories, user.id)
    if not ok:
        raise HTTPException(500, "Failed to tag")
    return {"ok": True}


@router.post("/legal-hold/{sample_id}")
async def legal_hold(
    sample_id: str,
    body: LegalHold,
    user=Depends(get_current_user),
    org=Depends(require_role("admin")),
):
    ok = svc.set_legal_hold(sample_id, org["org_id"], body.hold, user.id)
    if not ok:
        raise HTTPException(500, "Failed to set legal hold")
    return {"ok": True, "hold": body.hold}


# ---------- AUDIT EXPORT ----------

@router.get("/audit/export")
async def audit_export(
    start_date: str = None,
    end_date: str = None,
    format: str = "csv",
    user=Depends(get_current_user),
    org=Depends(require_role("admin")),
):
    rows = svc.export_audit_log(org["org_id"], start_date, end_date)

    log_action(user.id, "audit_export", "org", org["org_id"], {
        "format": format, "row_count": len(rows),
    })

    if format == "json":
        import json
        return Response(
            content=json.dumps(rows, indent=2, default=str),
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="audit_log.json"'},
        )

    csv_data = svc.audit_to_csv(rows)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="audit_log.csv"'},
    )
