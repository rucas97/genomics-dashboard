"""
Database abstraction interface.
Every backend (Supabase, SQLite) must implement these methods.
Routers call these methods — never the raw DB client.
"""
from abc import ABC, abstractmethod
from typing import Any


class DatabaseBackend(ABC):
    """Abstract interface. Both cloud and local backends implement this."""

    # ---- Users & auth ----
    @abstractmethod
    def get_user_by_id(self, user_id: str) -> dict | None: ...

    @abstractmethod
    def get_user_by_email(self, email: str) -> dict | None: ...

    @abstractmethod
    def create_user(self, email: str, password: str, role: str, name: str = None) -> dict: ...

    @abstractmethod
    def list_users(self) -> list[dict]: ...

    @abstractmethod
    def update_user_role(self, user_id: str, new_role: str) -> bool: ...

    @abstractmethod
    def delete_user(self, user_id: str) -> bool: ...

    @abstractmethod
    def verify_password(self, email: str, password: str) -> dict | None: ...

    # ---- Samples ----
    @abstractmethod
    def list_samples(self, user_id: str) -> list[dict]: ...

    @abstractmethod
    def get_sample(self, sample_id: str) -> dict | None: ...

    @abstractmethod
    def create_sample(self, data: dict) -> dict: ...

    @abstractmethod
    def update_sample(self, sample_id: str, patch: dict) -> bool: ...

    @abstractmethod
    def delete_sample(self, sample_id: str) -> bool: ...

    # ---- Variants ----
    @abstractmethod
    def list_variants(self, filters: dict, limit: int = 200, offset: int = 0) -> tuple[list[dict], int]: ...

    @abstractmethod
    def insert_variants(self, variants: list[dict]) -> int: ...

    @abstractmethod
    def get_variant(self, variant_id: str) -> dict | None: ...

    @abstractmethod
    def update_variant(self, variant_id: str, patch: dict) -> bool: ...

    # ---- QC metrics ----
    @abstractmethod
    def insert_qc_metrics(self, data: dict) -> dict: ...

    @abstractmethod
    def get_qc_for_sample(self, sample_id: str) -> list[dict]: ...

    # ---- Cohorts ----
    @abstractmethod
    def list_cohorts(self, user_id: str) -> list[dict]: ...

    @abstractmethod
    def get_cohort(self, cohort_id: str) -> dict | None: ...

    @abstractmethod
    def create_cohort(self, data: dict) -> dict: ...

    @abstractmethod
    def delete_cohort(self, cohort_id: str) -> bool: ...

    # ---- Pipeline runs ----
    @abstractmethod
    def list_pipeline_runs(self, user_id: str) -> list[dict]: ...

    @abstractmethod
    def create_pipeline_run(self, data: dict) -> dict: ...

    @abstractmethod
    def update_pipeline_run(self, run_id: str, patch: dict) -> bool: ...

    @abstractmethod
    def get_pipeline_run(self, run_id: str) -> dict | None: ...

    @abstractmethod
    def delete_pipeline_run(self, run_id: str) -> bool: ...

    # ---- Reports ----
    @abstractmethod
    def list_reports(self, user_id: str) -> list[dict]: ...

    @abstractmethod
    def create_report(self, data: dict) -> dict: ...

    @abstractmethod
    def delete_report(self, report_id: str) -> bool: ...

    # ---- Audit log ----
    @abstractmethod
    def log_audit(self, data: dict) -> bool: ...

    @abstractmethod
    def list_audit(self, user_id: str = None, limit: int = 500) -> list[dict]: ...

    @abstractmethod
    def clear_audit(self, user_id: str = None) -> int: ...

    # ---- ACMG ----
    @abstractmethod
    def get_variant_acmg(self, variant_id: str) -> dict | None: ...

    @abstractmethod
    def upsert_variant_acmg(self, data: dict) -> dict: ...

    # ---- Provenance ----
    @abstractmethod
    def record_provenance(self, data: dict) -> str: ...

    # ---- Consent ----
    @abstractmethod
    def list_consent(self, sample_id: str = None) -> list[dict]: ...

    @abstractmethod
    def record_consent(self, data: dict) -> dict: ...

    # ---- Storage ----
    @abstractmethod
    def upload_file(self, path: str, contents: bytes) -> str: ...

    @abstractmethod
    def download_file(self, path: str) -> bytes: ...

    @abstractmethod
    def delete_file(self, path: str) -> bool: ...
