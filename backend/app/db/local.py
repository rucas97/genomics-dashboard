"""
SQLite implementation of the DatabaseBackend interface.
This is what MODE=local uses.
"""
import sqlite3
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Any
from app.config import settings
from app.db.base import DatabaseBackend
from app.db.schema import init_schema
from app.services.local_auth import hash_password, verify_password, create_token, decode_token


def _row_to_dict(row, cursor):
    if row is None:
        return None
    return {col[0]: row[i] for i, col in enumerate(cursor.description)}


def _rows_to_dicts(rows, cursor):
    cols = [col[0] for col in cursor.description]
    return [dict(zip(cols, row)) for row in rows]


class LocalBackend(DatabaseBackend):
    def __init__(self):
        self.db_path = settings.LOCAL_DB_PATH
        self.data_dir = Path(settings.LOCAL_DATA_DIR)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Initialize schema on first use
        init_schema(self.db_path)

        # Ensure an admin user exists
        self._ensure_admin()

    def _conn(self):
        con = sqlite3.connect(self.db_path)
        con.execute("PRAGMA foreign_keys = ON")
        con.row_factory = None
        return con

    def _ensure_admin(self):
        """Create a default admin on first run."""
        con = self._conn()
        cur = con.execute("SELECT COUNT(*) FROM users")
        count = cur.fetchone()[0]
        if count == 0:
            admin_id = str(uuid.uuid4())
            default_pw = "admin"  # user changes on first login
            con.execute(
                "INSERT INTO users (id, email, name, password_hash, role) VALUES (?,?,?,?,?)",
                (admin_id, "admin@local", "Administrator",
                 hash_password(default_pw), "admin"),
            )
            con.execute(
                "INSERT INTO system_settings (key, value) VALUES (?,?)",
                ("first_run", "true"),
            )
            con.commit()
            print("=" * 60)
            print("  First run detected. Admin account created:")
            print("    Email:    admin@local")
            print("    Password: admin")
            print("  Change this immediately after login.")
            print("=" * 60)
        con.close()

    # ---------- USERS ----------
    def get_user_by_id(self, user_id: str) -> dict | None:
        con = self._conn()
        cur = con.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        result = _row_to_dict(row, cur)
        con.close()
        return result

    def get_user_by_email(self, email: str) -> dict | None:
        con = self._conn()
        cur = con.execute("SELECT * FROM users WHERE email = ?", (email.lower(),))
        row = cur.fetchone()
        result = _row_to_dict(row, cur)
        con.close()
        return result

    def create_user(self, email: str, password: str, role: str, name: str = None) -> dict:
        if role not in ("admin", "analyst", "viewer"):
            raise ValueError(f"Invalid role: {role}")
        user_id = str(uuid.uuid4())
        con = self._conn()
        try:
            con.execute(
                "INSERT INTO users (id, email, name, password_hash, role) VALUES (?,?,?,?,?)",
                (user_id, email.lower(), name, hash_password(password), role),
            )
            con.commit()
        except sqlite3.IntegrityError as e:
            con.close()
            raise ValueError(f"Email already exists: {e}")
        con.close()
        return self.get_user_by_id(user_id)

    def list_users(self) -> list[dict]:
        con = self._conn()
        cur = con.execute(
            "SELECT id, email, name, role, is_active, created_at, last_login "
            "FROM users ORDER BY created_at"
        )
        rows = cur.fetchall()
        result = _rows_to_dicts(rows, cur)
        con.close()
        return result

    def update_user_role(self, user_id: str, new_role: str) -> bool:
        if new_role not in ("admin", "analyst", "viewer"):
            return False
        con = self._conn()
        con.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
        con.commit()
        con.close()
        return True

    def delete_user(self, user_id: str) -> bool:
        con = self._conn()
        # Prevent deleting the last admin
        cur = con.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'admin' AND id != ?",
            (user_id,),
        )
        if cur.fetchone()[0] == 0:
            con.close()
            return False
        con.execute("DELETE FROM users WHERE id = ?", (user_id,))
        con.commit()
        con.close()
        return True

    def verify_password(self, email: str, password: str) -> dict | None:
        user = self.get_user_by_email(email)
        if not user:
            return None
        if not user.get("is_active"):
            return None
        if not verify_password(password, user["password_hash"]):
            return None
        # Update last_login
        con = self._conn()
        con.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), user["id"]),
        )
        con.commit()
        con.close()
        return user

    # ---------- SAMPLES ----------
    def list_samples(self, user_id: str) -> list[dict]:
        con = self._conn()
        cur = con.execute(
            "SELECT * FROM samples ORDER BY created_at DESC"
        )
        rows = cur.fetchall()
        result = _rows_to_dicts(rows, cur)
        con.close()
        # Deserialize metadata JSON
        for r in result:
            if r.get("metadata"):
                try:
                    r["metadata"] = json.loads(r["metadata"])
                except Exception:
                    pass
        return result

    def get_sample(self, sample_id: str) -> dict | None:
        con = self._conn()
        cur = con.execute("SELECT * FROM samples WHERE id = ?", (sample_id,))
        row = cur.fetchone()
        result = _row_to_dict(row, cur)
        con.close()
        if result and result.get("metadata"):
            try:
                result["metadata"] = json.loads(result["metadata"])
            except Exception:
                pass
        return result

    def create_sample(self, data: dict) -> dict:
        if "id" not in data:
            data["id"] = str(uuid.uuid4())
        if isinstance(data.get("metadata"), dict):
            data["metadata"] = json.dumps(data["metadata"])
        cols = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        con = self._conn()
        con.execute(
            f"INSERT INTO samples ({cols}) VALUES ({placeholders})",
            tuple(data.values()),
        )
        con.commit()
        con.close()
        return self.get_sample(data["id"])

    def update_sample(self, sample_id: str, patch: dict) -> bool:
        if not patch:
            return True
        if isinstance(patch.get("metadata"), dict):
            patch["metadata"] = json.dumps(patch["metadata"])
        sets = ", ".join([f"{k} = ?" for k in patch.keys()])
        con = self._conn()
        con.execute(
            f"UPDATE samples SET {sets} WHERE id = ?",
            tuple(patch.values()) + (sample_id,),
        )
        con.commit()
        con.close()
        return True

    def delete_sample(self, sample_id: str) -> bool:
        con = self._conn()
        con.execute("DELETE FROM samples WHERE id = ?", (sample_id,))
        con.commit()
        con.close()
        return True

    # ---------- VARIANTS ----------
    def list_variants(self, filters: dict, limit: int = 200, offset: int = 0) -> tuple[list[dict], int]:
        where_clauses = []
        params = []
        for k, v in filters.items():
            if k == "in_sample_ids":
                if not v:
                    return [], 0
                placeholders = ",".join(["?"] * len(v))
                where_clauses.append(f"sample_id IN ({placeholders})")
                params.extend(v)
            elif k == "gene_panel":
                if not v:
                    continue
                placeholders = ",".join(["?"] * len(v))
                where_clauses.append(f"gene IN ({placeholders})")
                params.extend(v)
            elif k == "sample_id":
                where_clauses.append("sample_id = ?")
                params.append(v)
            elif k == "gene":
                where_clauses.append("gene = ?")
                params.append(v)
            elif k == "chrom":
                where_clauses.append("chrom = ?")
                params.append(v)
            elif k == "impact":
                where_clauses.append("impact = ?")
                params.append(v)
            elif k == "clinvar":
                where_clauses.append("clinvar_significance = ?")
                params.append(v)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        con = self._conn()

        cur = con.execute(f"SELECT COUNT(*) FROM variants WHERE {where_sql}", params)
        total = cur.fetchone()[0]

        cur = con.execute(
            f"SELECT * FROM variants WHERE {where_sql} ORDER BY chrom, pos LIMIT ? OFFSET ?",
            params + [limit, offset],
        )
        rows = cur.fetchall()
        result = _rows_to_dicts(rows, cur)
        con.close()
        return result, total

    def insert_variants(self, variants: list[dict]) -> int:
        if not variants:
            return 0
        con = self._conn()
        for v in variants:
            if "id" not in v:
                v["id"] = str(uuid.uuid4())
        cols = list(variants[0].keys())
        col_sql = ", ".join(cols)
        placeholders = ", ".join(["?"] * len(cols))
        values = [tuple(v.get(c) for c in cols) for v in variants]
        con.executemany(
            f"INSERT INTO variants ({col_sql}) VALUES ({placeholders})",
            values,
        )
        con.commit()
        con.close()
        return len(variants)

    def get_variant(self, variant_id: str) -> dict | None:
        con = self._conn()
        cur = con.execute("SELECT * FROM variants WHERE id = ?", (variant_id,))
        row = cur.fetchone()
        result = _row_to_dict(row, cur)
        con.close()
        return result

    def update_variant(self, variant_id: str, patch: dict) -> bool:
        if not patch:
            return True
        sets = ", ".join([f"{k} = ?" for k in patch.keys()])
        con = self._conn()
        con.execute(
            f"UPDATE variants SET {sets} WHERE id = ?",
            tuple(patch.values()) + (variant_id,),
        )
        con.commit()
        con.close()
        return True

    # ---------- QC ----------
    def insert_qc_metrics(self, data: dict) -> dict:
        if "id" not in data:
            data["id"] = str(uuid.uuid4())
        cols = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        con = self._conn()
        con.execute(f"INSERT INTO qc_metrics ({cols}) VALUES ({placeholders})", tuple(data.values()))
        con.commit()
        cur = con.execute("SELECT * FROM qc_metrics WHERE id = ?", (data["id"],))
        row = cur.fetchone()
        result = _row_to_dict(row, cur)
        con.close()
        return result

    def get_qc_for_sample(self, sample_id: str) -> list[dict]:
        con = self._conn()
        cur = con.execute("SELECT * FROM qc_metrics WHERE sample_id = ?", (sample_id,))
        rows = cur.fetchall()
        result = _rows_to_dicts(rows, cur)
        con.close()
        return result

    # ---------- COHORTS ----------
    def list_cohorts(self, user_id: str) -> list[dict]:
        con = self._conn()
        cur = con.execute("SELECT * FROM cohorts ORDER BY created_at DESC")
        rows = cur.fetchall()
        result = _rows_to_dicts(rows, cur)
        con.close()
        for r in result:
            if r.get("sample_ids"):
                try:
                    r["sample_ids"] = json.loads(r["sample_ids"])
                except Exception:
                    pass
        return result

    def get_cohort(self, cohort_id: str) -> dict | None:
        con = self._conn()
        cur = con.execute("SELECT * FROM cohorts WHERE id = ?", (cohort_id,))
        row = cur.fetchone()
        result = _row_to_dict(row, cur)
        con.close()
        if result and result.get("sample_ids"):
            try:
                result["sample_ids"] = json.loads(result["sample_ids"])
            except Exception:
                pass
        return result

    def create_cohort(self, data: dict) -> dict:
        if "id" not in data:
            data["id"] = str(uuid.uuid4())
        if isinstance(data.get("sample_ids"), list):
            data["sample_ids"] = json.dumps(data["sample_ids"])
        cols = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        con = self._conn()
        con.execute(f"INSERT INTO cohorts ({cols}) VALUES ({placeholders})", tuple(data.values()))
        con.commit()
        con.close()
        return self.get_cohort(data["id"])

    def delete_cohort(self, cohort_id: str) -> bool:
        con = self._conn()
        con.execute("DELETE FROM cohorts WHERE id = ?", (cohort_id,))
        con.commit()
        con.close()
        return True

    # ---------- PIPELINES ----------
    def list_pipeline_runs(self, user_id: str) -> list[dict]:
        con = self._conn()
        cur = con.execute("SELECT * FROM pipeline_runs ORDER BY created_at DESC")
        rows = cur.fetchall()
        result = _rows_to_dicts(rows, cur)
        con.close()
        return result

    def create_pipeline_run(self, data: dict) -> dict:
        if "id" not in data:
            data["id"] = str(uuid.uuid4())
        cols = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        con = self._conn()
        con.execute(f"INSERT INTO pipeline_runs ({cols}) VALUES ({placeholders})", tuple(data.values()))
        con.commit()
        con.close()
        return self.get_pipeline_run(data["id"])

    def update_pipeline_run(self, run_id: str, patch: dict) -> bool:
        if not patch:
            return True
        sets = ", ".join([f"{k} = ?" for k in patch.keys()])
        con = self._conn()
        con.execute(f"UPDATE pipeline_runs SET {sets} WHERE id = ?", tuple(patch.values()) + (run_id,))
        con.commit()
        con.close()
        return True

    def get_pipeline_run(self, run_id: str) -> dict | None:
        con = self._conn()
        cur = con.execute("SELECT * FROM pipeline_runs WHERE id = ?", (run_id,))
        row = cur.fetchone()
        result = _row_to_dict(row, cur)
        con.close()
        return result

    def delete_pipeline_run(self, run_id: str) -> bool:
        con = self._conn()
        con.execute("DELETE FROM pipeline_runs WHERE id = ?", (run_id,))
        con.commit()
        con.close()
        return True

    # ---------- REPORTS ----------
    def list_reports(self, user_id: str) -> list[dict]:
        con = self._conn()
        cur = con.execute("SELECT * FROM reports ORDER BY created_at DESC")
        rows = cur.fetchall()
        result = _rows_to_dicts(rows, cur)
        con.close()
        return result

    def create_report(self, data: dict) -> dict:
        if "id" not in data:
            data["id"] = str(uuid.uuid4())
        cols = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        con = self._conn()
        con.execute(f"INSERT INTO reports ({cols}) VALUES ({placeholders})", tuple(data.values()))
        con.commit()
        con.close()
        return {"id": data["id"], **data}

    def delete_report(self, report_id: str) -> bool:
        con = self._conn()
        con.execute("DELETE FROM reports WHERE id = ?", (report_id,))
        con.commit()
        con.close()
        return True

    # ---------- AUDIT ----------
    def log_audit(self, data: dict) -> bool:
        try:
            if "id" not in data:
                data["id"] = str(uuid.uuid4())
            if isinstance(data.get("details"), dict):
                data["details"] = json.dumps(data["details"])
            cols = ", ".join(data.keys())
            placeholders = ", ".join(["?"] * len(data))
            con = self._conn()
            con.execute(f"INSERT INTO audit_log ({cols}) VALUES ({placeholders})", tuple(data.values()))
            con.commit()
            con.close()
            return True
        except Exception as e:
            print(f"Audit insert failed: {e}")
            return False

    def list_audit(self, user_id: str = None, limit: int = 500) -> list[dict]:
        con = self._conn()
        if user_id:
            cur = con.execute(
                "SELECT * FROM audit_log WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit),
            )
        else:
            cur = con.execute("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        result = _rows_to_dicts(rows, cur)
        con.close()
        for r in result:
            if r.get("details"):
                try:
                    r["details"] = json.loads(r["details"])
                except Exception:
                    pass
        return result

    def clear_audit(self, user_id: str = None) -> int:
        con = self._conn()
        if user_id:
            cur = con.execute("DELETE FROM audit_log WHERE user_id = ?", (user_id,))
        else:
            cur = con.execute("DELETE FROM audit_log")
        count = cur.rowcount
        con.commit()
        con.close()
        return count

    # ---------- ACMG ----------
    def get_variant_acmg(self, variant_id: str) -> dict | None:
        con = self._conn()
        cur = con.execute("SELECT * FROM variant_acmg WHERE variant_id = ?", (variant_id,))
        row = cur.fetchone()
        result = _row_to_dict(row, cur)
        con.close()
        if result and result.get("criteria_fired"):
            try:
                result["criteria_fired"] = json.loads(result["criteria_fired"])
            except Exception:
                pass
        return result

    def upsert_variant_acmg(self, data: dict) -> dict:
        if "id" not in data:
            data["id"] = str(uuid.uuid4())
        if isinstance(data.get("criteria_fired"), (list, dict)):
            data["criteria_fired"] = json.dumps(data["criteria_fired"])

        con = self._conn()
        existing = con.execute(
            "SELECT id FROM variant_acmg WHERE variant_id = ?",
            (data["variant_id"],),
        ).fetchone()

        if existing:
            data["id"] = existing[0]
            sets = ", ".join([f"{k} = ?" for k in data.keys() if k != "id"])
            values = [v for k, v in data.items() if k != "id"] + [data["id"]]
            con.execute(f"UPDATE variant_acmg SET {sets} WHERE id = ?", values)
        else:
            cols = ", ".join(data.keys())
            placeholders = ", ".join(["?"] * len(data))
            con.execute(f"INSERT INTO variant_acmg ({cols}) VALUES ({placeholders})", tuple(data.values()))

        con.commit()
        con.close()
        return self.get_variant_acmg(data["variant_id"])

    # ---------- PROVENANCE ----------
    def record_provenance(self, data: dict) -> str:
        if "id" not in data:
            data["id"] = str(uuid.uuid4())
        for k in ("tool_versions", "inputs", "outputs"):
            if isinstance(data.get(k), (list, dict)):
                data[k] = json.dumps(data[k])
        cols = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        con = self._conn()
        con.execute(f"INSERT INTO provenance ({cols}) VALUES ({placeholders})", tuple(data.values()))
        con.commit()
        con.close()
        return data["id"]

    # ---------- CONSENT ----------
    def list_consent(self, sample_id: str = None) -> list[dict]:
        con = self._conn()
        if sample_id:
            cur = con.execute("SELECT * FROM consent_records WHERE sample_id = ?", (sample_id,))
        else:
            cur = con.execute("SELECT * FROM consent_records ORDER BY granted_at DESC")
        rows = cur.fetchall()
        result = _rows_to_dicts(rows, cur)
        con.close()
        return result

    def record_consent(self, data: dict) -> dict:
        if "id" not in data:
            data["id"] = str(uuid.uuid4())
        cols = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        con = self._conn()
        con.execute(f"INSERT INTO consent_records ({cols}) VALUES ({placeholders})", tuple(data.values()))
        con.commit()
        con.close()
        return {**data, "created_at": datetime.utcnow().isoformat()}

    # ---------- STORAGE ----------
    def upload_file(self, path: str, contents: bytes) -> str:
        full_path = self.data_dir / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(contents)
        return path

    def download_file(self, path: str) -> bytes:
        return (self.data_dir / path).read_bytes()

    def delete_file(self, path: str) -> bool:
        try:
            (self.data_dir / path).unlink()
            return True
        except Exception:
            return False
