"""
Supabase-backed implementation. This is what MODE=cloud uses.
Wraps the existing supabase client — no behavior change.
"""
from app.supabase_client import supabase
from app.db.base import DatabaseBackend


class CloudBackend(DatabaseBackend):
    def get_user_by_id(self, user_id: str) -> dict | None:
        r = supabase.table("profiles").select("*").eq("id", user_id).execute()
        return r.data[0] if r.data else None

    def get_user_by_email(self, email: str) -> dict | None:
        r = supabase.table("profiles").select("*").eq("email", email).execute()
        return r.data[0] if r.data else None

    def create_user(self, email, password, role, name=None):
        # Cloud mode: users are created by Supabase Auth, not us
        raise NotImplementedError("User creation handled by Supabase Auth in cloud mode")

    def list_users(self) -> list[dict]:
        r = supabase.table("profiles").select("*").execute()
        return r.data or []

    def update_user_role(self, user_id: str, new_role: str) -> bool:
        supabase.table("profiles").update({"role": new_role}).eq("id", user_id).execute()
        return True

    def delete_user(self, user_id: str) -> bool:
        supabase.table("profiles").delete().eq("id", user_id).execute()
        return True

    def verify_password(self, email, password):
        raise NotImplementedError("Password auth handled by Supabase in cloud mode")

    def list_samples(self, user_id: str) -> list[dict]:
        r = supabase.table("samples").select("*").order("created_at", desc=True).execute()
        return r.data or []

    def get_sample(self, sample_id: str) -> dict | None:
        r = supabase.table("samples").select("*").eq("id", sample_id).execute()
        return r.data[0] if r.data else None

    def create_sample(self, data: dict) -> dict:
        r = supabase.table("samples").insert(data).execute()
        return r.data[0] if r.data else {}

    def update_sample(self, sample_id: str, patch: dict) -> bool:
        supabase.table("samples").update(patch).eq("id", sample_id).execute()
        return True

    def delete_sample(self, sample_id: str) -> bool:
        supabase.table("samples").delete().eq("id", sample_id).execute()
        return True

    def list_variants(self, filters, limit=200, offset=0):
        q = supabase.table("variants").select("*", count="exact")
        for k, v in filters.items():
            if k == "in_sample_ids":
                q = q.in_("sample_id", v)
            elif k == "gene_panel":
                q = q.in_("gene", v)
            elif v is not None:
                q = q.eq(k, v)
        r = q.range(offset, offset + limit - 1).execute()
        return r.data or [], r.count or 0

    def insert_variants(self, variants: list[dict]) -> int:
        if not variants:
            return 0
        supabase.table("variants").insert(variants).execute()
        return len(variants)

    def get_variant(self, variant_id: str) -> dict | None:
        r = supabase.table("variants").select("*").eq("id", variant_id).execute()
        return r.data[0] if r.data else None

    def update_variant(self, variant_id: str, patch: dict) -> bool:
        supabase.table("variants").update(patch).eq("id", variant_id).execute()
        return True

    def insert_qc_metrics(self, data: dict) -> dict:
        r = supabase.table("qc_metrics").insert(data).execute()
        return r.data[0] if r.data else {}

    def get_qc_for_sample(self, sample_id: str) -> list[dict]:
        r = supabase.table("qc_metrics").select("*").eq("sample_id", sample_id).execute()
        return r.data or []

    def list_cohorts(self, user_id: str) -> list[dict]:
        r = supabase.table("cohorts").select("*").order("created_at", desc=True).execute()
        return r.data or []

    def get_cohort(self, cohort_id: str) -> dict | None:
        r = supabase.table("cohorts").select("*").eq("id", cohort_id).execute()
        return r.data[0] if r.data else None

    def create_cohort(self, data: dict) -> dict:
        r = supabase.table("cohorts").insert(data).execute()
        return r.data[0] if r.data else {}

    def delete_cohort(self, cohort_id: str) -> bool:
        supabase.table("cohorts").delete().eq("id", cohort_id).execute()
        return True

    def list_pipeline_runs(self, user_id: str) -> list[dict]:
        r = supabase.table("pipeline_runs").select("*").order("created_at", desc=True).execute()
        return r.data or []

    def create_pipeline_run(self, data: dict) -> dict:
        r = supabase.table("pipeline_runs").insert(data).execute()
        return r.data[0] if r.data else {}

    def delete_pipeline_run(self, run_id: str) -> bool:
        supabase.table("pipeline_runs").delete().eq("id", run_id).execute()
        return True

    def update_pipeline_run(self, run_id: str, patch: dict) -> bool:
        supabase.table("pipeline_runs").update(patch).eq("id", run_id).execute()
        return True

    def get_pipeline_run(self, run_id: str) -> dict | None:
        r = supabase.table("pipeline_runs").select("*").eq("id", run_id).execute()
        return r.data[0] if r.data else None

    def list_reports(self, user_id: str) -> list[dict]:
        r = supabase.table("reports").select("*").order("created_at", desc=True).execute()
        return r.data or []

    def create_report(self, data: dict) -> dict:
        r = supabase.table("reports").insert(data).execute()
        return r.data[0] if r.data else {}

    def delete_report(self, report_id: str) -> bool:
        supabase.table("reports").delete().eq("id", report_id).execute()
        return True

    def log_audit(self, data: dict) -> bool:
        try:
            supabase.table("audit_log").insert(data).execute()
            return True
        except Exception as e:
            print(f"Audit insert failed: {e}")
            return False

    def list_audit(self, user_id=None, limit=500) -> list[dict]:
        q = supabase.table("audit_log").select("*")
        if user_id:
            q = q.eq("user_id", user_id)
        r = q.order("created_at", desc=True).limit(limit).execute()
        return r.data or []

    def clear_audit(self, user_id: str = None) -> int:
        q = supabase.table("audit_log").delete()
        if user_id:
            q = q.eq("user_id", user_id)
        r = q.execute()
        return len(r.data or [])

    def get_variant_acmg(self, variant_id: str) -> dict | None:
        r = supabase.table("variant_acmg").select("*").eq("variant_id", variant_id).execute()
        return r.data[0] if r.data else None

    def upsert_variant_acmg(self, data: dict) -> dict:
        r = supabase.table("variant_acmg").upsert(data, on_conflict="variant_id").execute()
        return r.data[0] if r.data else {}

    def record_provenance(self, data: dict) -> str:
        r = supabase.table("provenance").insert(data).execute()
        return r.data[0]["id"] if r.data else ""

    def list_consent(self, sample_id=None) -> list[dict]:
        q = supabase.table("consent_records").select("*")
        if sample_id:
            q = q.eq("sample_id", sample_id)
        r = q.execute()
        return r.data or []

    def record_consent(self, data: dict) -> dict:
        r = supabase.table("consent_records").insert(data).execute()
        return r.data[0] if r.data else {}

    def upload_file(self, path: str, contents: bytes) -> str:
        from app.services.storage import upload_file as cloud_upload
        # Cloud path uses the existing service
        supabase.storage.from_("genomic-files").upload(
            path, contents, {"content-type": "application/octet-stream"}
        )
        return path

    def download_file(self, path: str) -> bytes:
        return supabase.storage.from_("genomic-files").download(path)

    def delete_file(self, path: str) -> bool:
        try:
            supabase.storage.from_("genomic-files").remove([path])
            return True
        except Exception:
            return False
