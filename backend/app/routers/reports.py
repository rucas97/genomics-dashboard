from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import Response
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
from pathlib import Path

router = APIRouter(prefix="/reports", tags=["reports"])


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

    # Enrich variants with ACMG
    for v in variants:
        a = db.get_variant_acmg(v["id"])
        v["acmg_classification"] = a["classification"] if a else None
        v["acmg_summary"] = a["evidence_summary"] if a else None

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

    top_genes = sorted(gene_counts.items(), key=lambda x: -x[1])[:15]
    stats = {
        "n_variants": len(variants),
        "classification": counts,
        "top_genes": [
            {"gene": g, "count": c,
             "sample_count": len(gene_samples.get(g, set())),
             "sample_pct": round(100 * len(gene_samples.get(g, set())) / len(sample_ids), 1)}
            for g, c in top_genes
        ],
    }

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

    # Local mode: read the PDF from disk
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

    # Cloud mode: signed URL
    from app.supabase_client import supabase
    signed = supabase.storage.from_("genomic-files").create_signed_url(file_path, 3600)
    return {"url": signed.get("signedURL") or signed.get("signed_url")}
