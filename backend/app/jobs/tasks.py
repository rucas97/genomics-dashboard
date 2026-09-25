"""
Job functions. Called by the RQ worker, not by the API process.
Each function takes a job_id and updates the jobs table as it works.
"""
import json
import sqlite3
from datetime import datetime, timezone
from app.config import settings
from app.db import get_db


def _update_job(job_id: str, patch: dict):
    """Write job status to the jobs table. Only writes fields that exist."""
    try:
        con = sqlite3.connect(settings.LOCAL_DB_PATH)
        # Only update non-status fields � the runner owns status
        allowed = {"result", "error", "finished_at", "started_at"}
        filtered = {k: v for k, v in patch.items() if k in allowed}
        if not filtered:
            con.close()
            return
        values = []
        for k, v in filtered.items():
            if isinstance(v, (dict, list)):
                v = json.dumps(v)
            values.append(v)
        sets = ", ".join([f"{k} = ?" for k in filtered.keys()])
        values.append(job_id)
        con.execute(f"UPDATE jobs SET {sets} WHERE id = ?", values)
        con.commit()
        con.close()
    except Exception as e:
        print(f"Job status update failed: {e}")


def process_vcf_job(job_id: str, sample_id: str, provider: str, storage_path: str):
    """Parse a VCF and insert variants. Runs in the worker process."""
    import tempfile, os, gzip, shutil
    db = get_db()
    from app.services.storage import download_file
    from app.services.vcf_parser import parse_and_store_vcf
    from app.services.qc_calc import compute_qc_from_variants

    _update_job(job_id, {"status": "running", "started_at": datetime.now(timezone.utc).isoformat()})

    tmp_path = None
    tmp_uncompressed = None
    try:
        data = download_file(provider, storage_path)
        is_gz = storage_path.lower().endswith(".gz")

        if is_gz:
            with tempfile.NamedTemporaryFile(suffix=".vcf.gz", delete=False) as f:
                f.write(data)
                tmp_path = f.name
            tmp_uncompressed = tmp_path[:-3]
            with gzip.open(tmp_path, "rb") as fin, open(tmp_uncompressed, "wb") as fout:
                shutil.copyfileobj(fin, fout)
            plain_path = tmp_uncompressed
            plain_size = os.path.getsize(plain_path)
        else:
            with tempfile.NamedTemporaryFile(suffix=".vcf", delete=False) as f:
                f.write(data)
                tmp_path = f.name
            plain_path = tmp_path
            plain_size = len(data)

        size_mb = plain_size / (1024 * 1024)

        if size_mb > 10:
            from app.services.preprocess import extract_variants_from_vcf
            variants = extract_variants_from_vcf(storage_path, settings.R2_BUCKET) if provider == "b2" else None
            if not variants:
                from app.routers.samples import _extract_with_duckdb_local
                variants = _extract_with_duckdb_local(plain_path)
            _insert_variants(sample_id, variants)
        else:
            parse_and_store_vcf(sample_id, plain_path)

        compute_qc_from_variants(sample_id)
        db.update_sample(sample_id, {"status": "ready"})
        _update_job(job_id, {"status": "completed", "finished_at": datetime.now(timezone.utc).isoformat()})

    except Exception as e:
        print(f"VCF job failed for sample {sample_id}: {e}")
        try:
            db.update_sample(sample_id, {"status": "failed"})
        except Exception:
            pass
        _update_job(job_id, {
            "status": "failed",
            "error": str(e),
            "finished_at": datetime.now(timezone.utc).isoformat(),
        })
    finally:
        for p in (tmp_path, tmp_uncompressed):
            if p and os.path.exists(p):
                try:
                    os.unlink(p)
                except Exception:
                    pass


def _insert_variants(sample_id: str, variants: list[dict]):
    db = get_db()
    batch = []
    for v in variants:
        v["sample_id"] = sample_id
        batch.append(v)
        if len(batch) >= 1000:
            try:
                db.insert_variants(batch)
            except Exception as e:
                print(f"Batch insert failed: {e}")
            batch = []
    if batch:
        try:
            db.insert_variants(batch)
        except Exception as e:
            print(f"Final batch insert failed: {e}")


def annotate_job(job_id: str, sample_id: str):
    """Annotate all variants in a sample. Runs in the worker process."""
    db = get_db()
    from app.services.annotate import annotate_batch

    _update_job(job_id, {"status": "running", "started_at": datetime.now(timezone.utc).isoformat()})

    try:
        variants, _ = db.list_variants({"sample_id": sample_id}, limit=1000000, offset=0)
        to_annotate = [v for v in variants if not v.get("gene")]
        if not to_annotate:
            _update_job(job_id, {"status": "completed", "result": {"annotated": 0}})
            return

        annotated = annotate_batch(to_annotate)
        updated = 0
        for v in annotated:
            if v.get("gene") or v.get("clinvar_significance"):
                db.update_variant(v["id"], {
                    "gene": v.get("gene"),
                    "consequence": v.get("consequence"),
                    "impact": v.get("impact"),
                    "clinvar_significance": v.get("clinvar_significance"),
                })
                updated += 1

        _update_job(job_id, {
            "status": "completed",
            "result": {"annotated": updated, "total": len(to_annotate)},
            "finished_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        _update_job(job_id, {
            "status": "failed",
            "error": str(e),
            "finished_at": datetime.now(timezone.utc).isoformat(),
        })


def report_job(job_id: str, user_id: str, kind: str, resource_id: str):
    """Generate a PDF report. Runs in the worker process."""
    db = get_db()
    from app.services.reports import (
        generate_sample_report_html, generate_cohort_report_html,
        render_pdf, upload_report,
    )

    _update_job(job_id, {"status": "running", "started_at": datetime.now(timezone.utc).isoformat()})

    try:
        if kind == "sample":
            sample = db.get_sample(resource_id)
            if not sample:
                raise ValueError("Sample not found")
            qc_list = db.get_qc_for_sample(resource_id)
            qc = qc_list[0] if qc_list else None
            variants, _ = db.list_variants({"sample_id": resource_id}, limit=1000, offset=0)

            for v in variants:
                a = db.get_variant_acmg(v["id"])
                if a:
                    v["acmg_classification"] = a.get("classification")
                    v["acmg_criteria_fired"] = a.get("criteria_fired") or []
                    v["acmg_notes"] = a.get("notes")

            html = generate_sample_report_html(sample, qc, variants)
            pdf = render_pdf(html)
            path = upload_report(user_id, sample["name"], pdf)
            db.create_report({
                "user_id": user_id,
                "sample_id": resource_id,
                "title": f"Sample Report · {sample['name']}",
                "type": "sample",
                "file_path": path,
            })
        elif kind == "cohort":
            cohort = db.get_cohort(resource_id)
            if not cohort:
                raise ValueError("Cohort not found")
            sample_ids = cohort.get("sample_ids") or []
            samples = [db.get_sample(sid) for sid in sample_ids]
            samples = [s for s in samples if s]
            variants, _ = db.list_variants({"in_sample_ids": sample_ids}, limit=2000, offset=0)

            counts = {"pathogenic": 0, "vus": 0, "benign": 0, "other": 0}
            gene_samples, gene_counts = {}, {}
            for v in variants:
                cs = (v.get("clinvar_significance") or "").lower()
                if "pathogenic" in cs:
                    counts["pathogenic"] += 1
                elif "benign" in cs:
                    counts["benign"] += 1
                elif "uncertain" in cs:
                    counts["vus"] += 1
                else:
                    counts["other"] += 1
                g = v.get("gene")
                sid = v.get("sample_id")
                if g:
                    gene_counts[g] = gene_counts.get(g, 0) + 1
                    gene_samples.setdefault(g, set()).add(sid)

            stats = {
                "n_variants": len(variants),
                "classification": counts,
                "top_genes": [
                    {"gene": g, "count": c,
                     "sample_count": len(gene_samples.get(g, set())),
                     "sample_pct": round(100 * len(gene_samples.get(g, set())) / max(len(sample_ids), 1), 1)}
                    for g, c in sorted(gene_counts.items(), key=lambda x: -x[1])[:20]
                ],
                "shared_variants": [],
            }

            html = generate_cohort_report_html(cohort, samples, variants, stats)
            pdf = render_pdf(html)
            path = upload_report(user_id, cohort["name"], pdf)
            db.create_report({
                "user_id": user_id,
                "title": f"Cohort Report · {cohort['name']}",
                "type": "cohort",
                "file_path": path,
            })

        _update_job(job_id, {"status": "completed", "finished_at": datetime.now(timezone.utc).isoformat()})
    except Exception as e:
        _update_job(job_id, {
            "status": "failed",
            "error": str(e),
            "finished_at": datetime.now(timezone.utc).isoformat(),
        })
