from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import Response
from pathlib import Path
from app.config import settings
from app.db import get_db
from app.deps import get_current_user, get_current_org
from app.user import CurrentUser
from app.services.audit import log_action
from app.services.reports import (
    generate_sample_report_html,
    generate_cohort_report_html,
    render_pdf,
    upload_report,
)

router = APIRouter(prefix="/reports", tags=["reports"])


def _enrich_with_acmg(variants: list[dict]) -> list[dict]:
    from app.services.acmg import classify_variant
    db = get_db()
    for v in variants:
        try:
            a = db.get_variant_acmg(v["id"])
        except Exception:
            a = None

        if a:
            v["acmg_classification"] = a.get("classification")
            v["acmg_criteria_fired"] = a.get("criteria_fired") or []
            v["acmg_notes"] = a.get("notes")
            v["acmg_evidence_summary"] = a.get("evidence_summary")
            v["acmg_confidence"] = a.get("confidence")
        else:
            try:
                result = classify_variant(v)
                v["acmg_classification"] = result["classification"]
                v["acmg_criteria_fired"] = result["criteria_fired"]
                v["acmg_notes"] = None
                v["acmg_evidence_summary"] = result["evidence_summary"]
                v["acmg_confidence"] = result["confidence"]
            except Exception as e:
                print(f"ACMG enrich failed for {v.get('id')}: {e}")
                v["acmg_classification"] = "VUS"
                v["acmg_criteria_fired"] = []
                v["acmg_notes"] = None
    return variants


@router.get("/")
async def list_reports(user: CurrentUser = Depends(get_current_user), org=Depends(get_current_org)):
    db = get_db()
    return db.list_reports(user.id)


@router.post("/sample/{sample_id}")
async def create_sample_report(
    sample_id: str,
    background: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
    org=Depends(get_current_org),
):
    db = get_db()
    sample = db.get_sample(sample_id)
    if not sample:
        raise HTTPException(404, "Sample not found")

    qc_list = db.get_qc_for_sample(sample_id)
    qc = qc_list[0] if qc_list else None

    variants, _ = db.list_variants({"sample_id": sample_id}, limit=1000, offset=0)
    variants = _enrich_with_acmg(variants)

    try:
        html = generate_sample_report_html(sample, qc, variants)
        pdf = render_pdf(html)
        path = upload_report(user.id, sample["name"], pdf)
    except Exception as e:
        print(f"Report generation failed: {e}")
        raise HTTPException(500, f"Report generation failed: {e}")

    db.create_report({
        "user_id": user.id,
        "sample_id": sample_id,
        "title": f"Sample Report · {sample['name']}",
        "type": "sample",
        "file_path": path,
    })

    log_action(user.id, "generate_report", "sample", sample_id, {"title": sample["name"]})
    return {"ok": True, "path": path}


@router.post("/cohort/{cohort_id}")
async def create_cohort_report(
    cohort_id: str,
    background: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
    org=Depends(get_current_org),
):
    db = get_db()
    cohort = db.get_cohort(cohort_id)
    if not cohort:
        raise HTTPException(404, "Cohort not found")

    sample_ids = cohort.get("sample_ids") or []
    if not sample_ids:
        raise HTTPException(400, "Cohort has no samples")

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

    top_genes = sorted(gene_counts.items(), key=lambda x: -x[1])[:20]
    stats = {
        "n_variants": len(variants),
        "classification": counts,
        "top_genes": [
            {"gene": g, "count": c,
             "sample_count": len(gene_samples.get(g, set())),
             "sample_pct": round(100 * len(gene_samples.get(g, set())) / len(sample_ids), 1)}
            for g, c in top_genes
        ],
        "shared_variants": [],
    }

    from collections import defaultdict
    variant_samples = defaultdict(set)
    variant_gene = {}
    for v in variants:
        vk = f"{v.get('chrom')}:{v.get('pos')}:{v.get('ref')}>{v.get('alt')}"
        variant_samples[vk].add(v.get("sample_id"))
        variant_gene[vk] = v.get("gene")

    shared = []
    for vk, sids in variant_samples.items():
        if len(sids) > 1:
            shared.append({
                "variant": vk,
                "gene": variant_gene.get(vk),
                "sample_count": len(sids),
                "sample_pct": round(100 * len(sids) / len(sample_ids), 1),
            })
    shared = sorted(shared, key=lambda x: -x["sample_count"])[:25]
    stats["shared_variants"] = shared

    try:
        html = generate_cohort_report_html(cohort, samples, variants, stats)
        pdf = render_pdf(html)
        path = upload_report(user.id, cohort["name"], pdf)
    except Exception as e:
        print(f"Cohort report generation failed: {e}")
        raise HTTPException(500, f"Report generation failed: {e}")

    db.create_report({
        "user_id": user.id,
        "title": f"Cohort Report · {cohort['name']}",
        "type": "cohort",
        "file_path": path,
    })

    log_action(user.id, "generate_report", "cohort", cohort_id, {"title": cohort["name"]})
    return {"ok": True, "path": path}


@router.get("/{report_id}/download")
async def download_report(report_id: str, user: CurrentUser = Depends(get_current_user)):
    db = get_db()
    reports = db.list_reports(user.id)
    report = next((r for r in reports if r["id"] == report_id), None)
    if not report:
        raise HTTPException(404, "Report not found")

    file_path = report.get("file_path")
    if not file_path:
        raise HTTPException(404, "Report file missing")

    if settings.is_local:
        full = Path(settings.LOCAL_DATA_DIR) / file_path
        if not full.exists():
            raise HTTPException(404, f"Report file not found at {full}")
        pdf_bytes = full.read_bytes()
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{report.get("title", "report")}.pdf"',
            },
        )

    from app.supabase_client import supabase
    signed = supabase.storage.from_("genomic-files").create_signed_url(file_path, 3600)
    return {"url": signed.get("signedURL") or signed.get("signed_url")}


@router.delete("/{report_id}")
async def delete_report(report_id: str, user: CurrentUser = Depends(get_current_user)):
    """Delete a report and its underlying file."""
    db = get_db()
    reports = db.list_reports(user.id)
    report = next((r for r in reports if r["id"] == report_id), None)
    if not report:
        raise HTTPException(404, "Report not found")

    file_path = report.get("file_path")

    if file_path:
        try:
            if settings.is_local:
                full = Path(settings.LOCAL_DATA_DIR) / file_path
                if full.exists():
                    full.unlink()
            else:
                from app.supabase_client import supabase
                supabase.storage.from_("genomic-files").remove([file_path])
        except Exception as e:
            print(f"Failed to delete report file {file_path}: {e}")

    try:
        db.delete_report(report_id)
    except Exception as e:
        raise HTTPException(500, f"Failed to delete report: {e}")

    log_action(user.id, "delete", "report", report_id, {"title": report.get("title")})
    return {"ok": True}


from pydantic import BaseModel as _BulkBase

class BulkReportDeleteRequest(_BulkBase):
    ids: list[str]

@router.post("/bulk-delete")
async def bulk_delete_reports(
    body: BulkReportDeleteRequest,
    user: CurrentUser = Depends(get_current_user),
):
    db = get_db()
    reports = db.list_reports(user.id)
    by_id = {r["id"]: r for r in reports}
    deleted = 0
    for rid in body.ids:
        report = by_id.get(rid)
        if not report:
            continue
        fp = report.get("file_path")
        if fp:
            try:
                if settings.is_local:
                    full = Path(settings.LOCAL_DATA_DIR) / fp
                    if full.exists():
                        full.unlink()
                else:
                    from app.supabase_client import supabase
                    supabase.storage.from_("genomic-files").remove([fp])
            except Exception as e:
                print(f"File delete failed for {fp}: {e}")
        db.delete_report(rid)
        log_action(user.id, "delete", "report", rid, {"bulk": True, "title": report.get("title")})
        deleted += 1
    return {"ok": True, "deleted": deleted}
