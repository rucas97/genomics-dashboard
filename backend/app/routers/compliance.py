from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from app.config import settings
from app.db import get_db
from app.deps import get_current_user, get_current_org, require_role
from app.user import CurrentUser
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


@router.post("/session/touch")
async def touch_session(request: Request, user: CurrentUser = Depends(get_current_user)):
    if settings.is_local:
        return {"ok": True, "mode": "local"}
    org = await get_current_org(user)
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    svc.record_activity(user.id, org["org_id"], ip, ua)
    return {"ok": True}


@router.get("/session/status")
async def session_status(user: CurrentUser = Depends(get_current_user)):
    if settings.is_local:
        return {"timeout_minutes": 0, "expired": False, "mode": "local"}
    org = await get_current_org(user)
    timeout = svc.get_org_session_timeout(org["org_id"])
    expired = svc.is_session_expired(user.id, org["org_id"], timeout)
    return {"timeout_minutes": timeout, "expired": expired}


@router.post("/consent")
async def create_consent(
    body: ConsentCreate,
    user: CurrentUser = Depends(get_current_user),
    org=Depends(require_role("analyst")),
):
    db = get_db()
    record = db.record_consent({
        "sample_id": body.sample_id,
        "subject_id": body.subject_id,
        "consent_type": body.consent_type,
        "granted": body.granted,
        "granted_by": body.granted_by,
        "expires_at": body.expires_at,
        "notes": body.notes,
    })
    log_action(user.id, "record_consent", "sample", body.sample_id, {
        "consent_type": body.consent_type, "granted": body.granted,
    })
    return record


@router.get("/consent")
async def list_consent(
    sample_id: str = None,
    user: CurrentUser = Depends(get_current_user),
):
    db = get_db()
    return db.list_consent(sample_id)


@router.delete("/consent/{consent_id}")
async def revoke_consent(
    consent_id: str,
    reason: str = None,
    user: CurrentUser = Depends(get_current_user),
    org=Depends(require_role("analyst")),
):
    if settings.is_local:
        raise HTTPException(400, "Consent revocation not yet supported in local mode")
    if not svc.revoke_consent(consent_id, org["org_id"], reason):
        raise HTTPException(500, "Failed to revoke")
    log_action(user.id, "revoke_consent", "consent", consent_id, {"reason": reason})
    return {"ok": True}


@router.post("/erase/sample/{sample_id}")
async def erase_sample(
    sample_id: str,
    user: CurrentUser = Depends(get_current_user),
    org=Depends(require_role("admin")),
):
    db = get_db()
    sample = db.get_sample(sample_id)
    if not sample:
        raise HTTPException(404, "Sample not found")
    if sample.get("legal_hold"):
        raise HTTPException(400, "Legal hold active — cannot erase")

    db.delete_sample(sample_id)
    log_action(user.id, "gdpr_erase", "sample", sample_id, {"sample_name": sample.get("name")})
    return {"ok": True, "erased": sample.get("name")}


@router.post("/retention/run")
async def run_retention(
    body: RetentionRequest,
    user: CurrentUser = Depends(get_current_user),
    org=Depends(require_role("admin")),
):
    if settings.is_local:
        return {"ok": True, "deleted": 0, "retained": 0, "legal_holds_skipped": 0, "dry_run": body.dry_run, "note": "not implemented in local mode"}
    result = svc.apply_retention_policy(org["org_id"], dry_run=body.dry_run)
    log_action(user.id, "retention_run", "org", org["org_id"], {"dry_run": body.dry_run, "result": result})
    return result


@router.get("/retention/runs")
async def list_retention_runs(user: CurrentUser = Depends(get_current_user)):
    if settings.is_local:
        return []
    org = await get_current_org(user)
    return svc.list_retention_runs(org["org_id"])


@router.post("/phi/{sample_id}")
async def tag_phi(
    sample_id: str,
    body: PHITag,
    user: CurrentUser = Depends(get_current_user),
    org=Depends(require_role("analyst")),
):
    db = get_db()
    db.update_sample(sample_id, {"contains_phi": 1, "phi_categories": str(body.categories)})
    log_action(user.id, "tag_phi", "sample", sample_id, {"categories": body.categories})
    return {"ok": True}


@router.post("/legal-hold/{sample_id}")
async def legal_hold(
    sample_id: str,
    body: LegalHold,
    user: CurrentUser = Depends(get_current_user),
    org=Depends(require_role("admin")),
):
    db = get_db()
    db.update_sample(sample_id, {"legal_hold": 1 if body.hold else 0})
    log_action(user.id, "legal_hold_change", "sample", sample_id, {"hold": body.hold})
    return {"ok": True, "hold": body.hold}


@router.get("/audit/export")
async def audit_export(
    start_date: str = None,
    end_date: str = None,
    format: str = "csv",
    user: CurrentUser = Depends(get_current_user),
    org=Depends(require_role("admin")),
):
    db = get_db()
    rows = db.list_audit(limit=10000)

    log_action(user.id, "audit_export", "org", user.id, {"format": format, "row_count": len(rows)})

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
