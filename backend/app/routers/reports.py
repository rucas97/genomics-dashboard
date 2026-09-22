from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from app.supabase_client import supabase
from app.db import sb_select, sb_insert
from app.deps import get_current_user
from app.services.audit import log_action
from app.services.reports import (
    generate_sample_report_html,
    generate_cohort_report_html,
    render_pdf,
    upload_report,
)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/")
async def list_reports(user=Depends(get_current_user)):
    resp = sb_select("reports", order="created_at", desc=True)
    return resp.data


@router.post("/sample/{sample_id}")
async def create_sample_report(sample_id: str, background: BackgroundTasks, user=Depends(get_current_user)):
    sresp = supabase.table("samples").select("*").eq("id", sample_id).execute()
    if not sresp.data:
        raise HTTPException(404, "Sample not found")
    sample = sresp.data[0]

    qresp = supabase.table("qc_metrics").select("*").eq("sample_id", sample_id).execute()
    qc = qresp.data[0] if qresp.data else None

    vresp = supabase.table("variants").select("*").eq("sample_id", sample_id).limit(1000).execute()
    variants = vresp.data or []

    try:
        html = generate_sample_report_html(sample, qc, variants)
        pdf = render_pdf(html)
        path = upload_report(user.id, sample["name"], pdf)
    except Exception as e:
        raise HTTPException(500, f"Report generation failed: {e}")

    sb_insert("reports", {
        "project_id": sample.get("project_id"),
        "sample_id": sample_id,
        "title": f"Sample Report · {sample['name']}",
        "type": "sample",
        "file_path": path,
        "created_by": user.id,
    })

    log_action(user.id, "generate_report", "sample", sample_id, {"title": sample["name"]})
    return {"ok": True, "path": path}


@router.post("/cohort/{cohort_id}")
async def create_cohort_report(cohort_id: str, background: BackgroundTasks, user=Depends(get_current_user)):
    cresp = supabase.table("cohorts").select("*").eq("id", cohort_id).execute()
    if not cresp.data:
        raise HTTPException(404, "Cohort not found")
    cohort = cresp.data[0]
    sample_ids = cohort.get("sample_ids") or []
    if not sample_ids:
        raise HTTPException(400, "Cohort has no samples")

    sresp = supabase.table("samples").select("*").in_("id", sample_ids).execute()
    samples = sresp.data or []

    vresp = supabase.table("variants").select("*").in_("sample_id", sample_ids).limit(2000).execute()
    variants = vresp.data or []

    # Build stats inline
    counts = {"pathogenic": 0, "vus": 0, "benign": 0, "other": 0}
    gene_samples, gene_counts = {}, {}
    for v in variants:
        cs = (v.get("clinvar_significance") or "").lower()
        if "pathogenic" in cs or "likely pathogenic" in cs:
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
            {
                "gene": g,
                "count": c,
                "sample_count": len(gene_samples.get(g, set())),
                "sample_pct": round(100 * len(gene_samples.get(g, set())) / len(sample_ids), 1),
            }
            for g, c in top_genes
        ],
    }

    try:
        html = generate_cohort_report_html(cohort, samples, variants, stats)
        pdf = render_pdf(html)
        path = upload_report(user.id, cohort["name"], pdf)
    except Exception as e:
        raise HTTPException(500, f"Report generation failed: {e}")

    sb_insert("reports", {
        "project_id": cohort.get("project_id"),
        "title": f"Cohort Report · {cohort['name']}",
        "type": "cohort",
        "file_path": path,
        "created_by": user.id,
    })

    log_action(user.id, "generate_report", "cohort", cohort_id, {"title": cohort["name"]})
    return {"ok": True, "path": path}


@router.get("/{report_id}/download")
async def download_report(report_id: str, user=Depends(get_current_user)):
    resp = supabase.table("reports").select("*").eq("id", report_id).execute()
    if not resp.data:
        raise HTTPException(404, "Report not found")
    report = resp.data[0]

    # Signed URL valid 1 hour
    signed = supabase.storage.from_("genomic-files").create_signed_url(
        report["file_path"], 3600
    )
    return {"url": signed.get("signedURL") or signed.get("signed_url")}
