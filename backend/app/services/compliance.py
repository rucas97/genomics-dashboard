"""
Compliance features:
- Session activity tracking
- Data retention enforcement
- Consent management
- Right to erasure (GDPR Art. 17)
- PHI tagging
"""
from datetime import datetime, timedelta
from app.supabase_client import supabase
from app.services.storage import delete_file
from app.services.audit import log_action


# ============== SESSIONS ==============

def record_activity(user_id: str, org_id: str, ip: str = None, ua: str = None):
    """Touch the user's session row so timeout checks work."""
    try:
        existing = supabase.table("user_sessions") \
            .select("id") \
            .eq("user_id", user_id) \
            .eq("org_id", org_id) \
            .order("last_activity", desc=True) \
            .limit(1) \
            .execute()

        if existing.data:
            supabase.table("user_sessions") \
                .update({"last_activity": datetime.utcnow().isoformat()}) \
                .eq("id", existing.data[0]["id"]) \
                .execute()
        else:
            supabase.table("user_sessions").insert({
                "user_id": user_id,
                "org_id": org_id,
                "ip_address": ip,
                "user_agent": ua,
            }).execute()
    except Exception as e:
        print(f"record_activity failed: {e}")


def is_session_expired(user_id: str, org_id: str, timeout_minutes: int = 30) -> bool:
    """Check if the user's last activity exceeds the timeout."""
    try:
        resp = supabase.table("user_sessions") \
            .select("last_activity") \
            .eq("user_id", user_id) \
            .eq("org_id", org_id) \
            .order("last_activity", desc=True) \
            .limit(1) \
            .execute()
        if not resp.data:
            return False
        last = datetime.fromisoformat(resp.data[0]["last_activity"].replace("Z", "+00:00"))
        cutoff = datetime.utcnow().replace(tzinfo=last.tzinfo) - timedelta(minutes=timeout_minutes)
        return last < cutoff
    except Exception as e:
        print(f"is_session_expired failed: {e}")
        return False


def get_org_session_timeout(org_id: str) -> int:
    """Return the org's configured session timeout in minutes."""
    try:
        resp = supabase.table("organizations").select("settings").eq("id", org_id).execute()
        if resp.data and resp.data[0].get("settings"):
            return resp.data[0]["settings"].get("session_timeout_minutes", 30)
    except Exception:
        pass
    return 30


# ============== CONSENT ==============

def record_consent(
    org_id: str,
    sample_id: str,
    subject_id: str,
    consent_type: str,
    granted: bool = True,
    granted_by: str = None,
    expires_at: str = None,
    notes: str = None,
) -> dict | None:
    try:
        resp = supabase.table("consent_records").insert({
            "org_id": org_id,
            "sample_id": sample_id,
            "subject_id": subject_id,
            "consent_type": consent_type,
            "granted": granted,
            "granted_by": granted_by,
            "expires_at": expires_at,
            "notes": notes,
        }).execute()
        return resp.data[0] if resp.data else None
    except Exception as e:
        print(f"record_consent failed: {e}")
        return None


def list_consent(org_id: str, sample_id: str = None) -> list[dict]:
    try:
        q = supabase.table("consent_records").select("*").eq("org_id", org_id)
        if sample_id:
            q = q.eq("sample_id", sample_id)
        return q.order("granted_at", desc=True).execute().data or []
    except Exception as e:
        print(f"list_consent failed: {e}")
        return []


def revoke_consent(consent_id: str, org_id: str, reason: str = None) -> bool:
    try:
        supabase.table("consent_records").update({
            "granted": False,
            "revoked_at": datetime.utcnow().isoformat(),
            "notes": reason,
        }).eq("id", consent_id).eq("org_id", org_id).execute()
        return True
    except Exception as e:
        print(f"revoke_consent failed: {e}")
        return False


# ============== RIGHT TO ERASURE ==============

def erase_sample(sample_id: str, org_id: str, user_id: str) -> dict:
    """
    GDPR Art. 17: full deletion of a sample and all derived data.
    Refuses if a legal hold is active.
    """
    sresp = supabase.table("samples") \
        .select("*") \
        .eq("id", sample_id) \
        .eq("org_id", org_id) \
        .execute()
    if not sresp.data:
        return {"ok": False, "error": "Sample not found"}

    sample = sresp.data[0]
    if sample.get("legal_hold"):
        return {"ok": False, "error": "Legal hold active — cannot erase"}

    # Delete storage file
    try:
        provider = (sample.get("metadata") or {}).get("storage_provider", "supabase")
        if sample.get("file_path"):
            delete_file(provider, sample["file_path"])
    except Exception as e:
        print(f"Storage delete failed (continuing): {e}")

    # Delete derived data
    supabase.table("variants").delete().eq("sample_id", sample_id).execute()
    supabase.table("qc_metrics").delete().eq("sample_id", sample_id).execute()
    supabase.table("consent_records").delete().eq("sample_id", sample_id).execute()
    supabase.table("reports").delete().eq("sample_id", sample_id).execute()
    supabase.table("pipeline_runs").delete().eq("sample_id", sample_id).execute()

    # Delete sample row
    supabase.table("samples").delete().eq("id", sample_id).execute()

    log_action(user_id, "gdpr_erase", "sample", sample_id, {
        "sample_name": sample.get("name"),
        "reason": "right_to_erasure",
    })

    return {"ok": True, "erased": sample.get("name")}


# ============== RETENTION ==============

def apply_retention_policy(org_id: str, dry_run: bool = False) -> dict:
    """
    Delete samples older than their retention_days policy.
    Skips legal holds. Logs the run.
    """
    try:
        resp = supabase.table("samples") \
            .select("id, name, created_at, retention_days, legal_hold, org_id") \
            .eq("org_id", org_id) \
            .execute()
        samples = resp.data or []
    except Exception as e:
        return {"ok": False, "error": f"Failed to fetch samples: {e}"}

    now = datetime.utcnow()
    deleted = 0
    retained = 0
    skipped = 0

    for s in samples:
        if s.get("legal_hold"):
            skipped += 1
            continue

        days = s.get("retention_days") or 365
        try:
            created = datetime.fromisoformat(s["created_at"].replace("Z", "+00:00"))
            age_days = (now.replace(tzinfo=created.tzinfo) - created).days
        except Exception:
            retained += 1
            continue

        if age_days > days:
            if not dry_run:
                # Actually erase via the same path
                erase_sample(s["id"], org_id, "system")
            deleted += 1
        else:
            retained += 1

    # Log the run
    if not dry_run:
        try:
            supabase.table("retention_runs").insert({
                "org_id": org_id,
                "policy_days": 0,
                "samples_deleted": deleted,
                "samples_retained": retained,
                "legal_holds_skipped": skipped,
                "notes": "automated" if not dry_run else "dry_run",
            }).execute()
        except Exception as e:
            print(f"Failed to log retention run: {e}")

    return {
        "ok": True,
        "deleted": deleted,
        "retained": retained,
        "legal_holds_skipped": skipped,
        "dry_run": dry_run,
    }


def list_retention_runs(org_id: str) -> list[dict]:
    try:
        return supabase.table("retention_runs") \
            .select("*") \
            .eq("org_id", org_id) \
            .order("run_at", desc=True) \
            .limit(50) \
            .execute().data or []
    except Exception as e:
        print(f"list_retention_runs failed: {e}")
        return []


# ============== PHI TAGGING ==============

def tag_phi(sample_id: str, org_id: str, categories: list[str], user_id: str) -> bool:
    try:
        supabase.table("samples").update({
            "contains_phi": True,
            "phi_categories": categories,
        }).eq("id", sample_id).eq("org_id", org_id).execute()

        log_action(user_id, "tag_phi", "sample", sample_id, {"categories": categories})
        return True
    except Exception as e:
        print(f"tag_phi failed: {e}")
        return False


def set_legal_hold(sample_id: str, org_id: str, hold: bool, user_id: str) -> bool:
    try:
        supabase.table("samples").update({
            "legal_hold": hold,
        }).eq("id", sample_id).eq("org_id", org_id).execute()

        log_action(user_id, "legal_hold_change", "sample", sample_id, {"hold": hold})
        return True
    except Exception as e:
        print(f"set_legal_hold failed: {e}")
        return False


# ============== AUDIT EXPORT ==============

def export_audit_log(org_id: str, start_date: str = None, end_date: str = None) -> list[dict]:
    """
    Export the full audit log for compliance officers.
    Returns list of rows (caller serializes to CSV/JSON).
    """
    try:
        q = supabase.table("audit_log").select("*").eq("org_id", org_id)
        if start_date:
            q = q.gte("created_at", start_date)
        if end_date:
            q = q.lte("created_at", end_date)
        return q.order("created_at", desc=True).limit(10000).execute().data or []
    except Exception as e:
        print(f"export_audit_log failed: {e}")
        return []


def audit_to_csv(rows: list[dict]) -> str:
    """Convert audit rows to CSV."""
    import csv
    from io import StringIO

    if not rows:
        return "id,user_id,action,resource_type,resource_id,created_at\n"

    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=[
        "id", "user_id", "action", "resource_type",
        "resource_id", "created_at", "details",
    ], extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        r_copy = dict(r)
        if isinstance(r_copy.get("details"), dict):
            import json
            r_copy["details"] = json.dumps(r_copy["details"])
        writer.writerow(r_copy)
    return buf.getvalue()
