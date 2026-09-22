from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.supabase_client import supabase
from app.deps import get_current_user
from app.services.audit import log_action
from app.services.cohort import compute_pca

router = APIRouter(prefix="/cohorts", tags=["cohorts"])


class CohortCreate(BaseModel):
    name: str
    description: str | None = None
    sample_ids: list[str]


@router.get("/")
async def list_cohorts(user=Depends(get_current_user)):
    resp = supabase.table("cohorts").select("*").order("created_at", desc=True).execute()
    return resp.data


@router.post("/")
async def create_cohort(body: CohortCreate, user=Depends(get_current_user)):
    if not body.sample_ids:
        raise HTTPException(400, "At least one sample is required")
    if len(body.sample_ids) < 2:
        raise HTTPException(400, "At least 2 samples are required for a cohort")

    resp = supabase.table("cohorts").insert({
        "name": body.name,
        "description": body.description,
        "sample_ids": body.sample_ids,
        "created_by": user.id,
    }).execute()

    if not resp.data:
        raise HTTPException(500, "Failed to create cohort")

    cohort_id = resp.data[0]["id"]
    log_action(user.id, "create", "cohort", cohort_id, {"name": body.name, "n_samples": len(body.sample_ids)})
    return resp.data[0]


@router.get("/{cohort_id}")
async def get_cohort(cohort_id: str, user=Depends(get_current_user)):
    resp = supabase.table("cohorts").select("*").eq("id", cohort_id).execute()
    if not resp.data:
        raise HTTPException(404, "Cohort not found")
    log_action(user.id, "view", "cohort", cohort_id)
    return resp.data[0]


@router.get("/{cohort_id}/pca")
async def cohort_pca(cohort_id: str, user=Depends(get_current_user)):
    resp = supabase.table("cohorts").select("*").eq("id", cohort_id).execute()
    if not resp.data:
        raise HTTPException(404, "Cohort not found")

    cohort = resp.data[0]
    sample_ids = cohort.get("sample_ids") or []
    if len(sample_ids) < 2:
        raise HTTPException(400, "Need at least 2 samples for PCA")

    result = compute_pca(sample_ids)
    log_action(user.id, "run_pca", "cohort", cohort_id, {"n_samples": len(sample_ids)})
    return result


@router.get("/{cohort_id}/stats")
async def cohort_stats(cohort_id: str, user=Depends(get_current_user)):
    """Gene enrichment + classification breakdown for a cohort."""
    resp = supabase.table("cohorts").select("*").eq("id", cohort_id).execute()
    if not resp.data:
        raise HTTPException(404, "Cohort not found")

    cohort = resp.data[0]
    sample_ids = cohort.get("sample_ids") or []
    if not sample_ids:
        raise HTTPException(400, "Cohort has no samples")

    # Pull all variants across the cohort
    vresp = supabase.table("variants").select(
        "sample_id,gene,clinvar_significance,impact,chrom,pos,ref,alt"
    ).in_("sample_id", sample_ids).execute()
    variants = vresp.data or []

    counts = {"pathogenic": 0, "vus": 0, "benign": 0, "other": 0}
    gene_samples = {}
    gene_counts = {}
    variant_samples = {}

    for v in variants:
        cs = (v.get("clinvar_significance") or "").lower()
        if "pathogenic" in cs or "likely pathogenic" in cs or "likely_pathogenic" in cs:
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

        vk = f"{v.get('chrom')}:{v.get('pos')}:{v.get('ref')}>{v.get('alt')}"
        variant_samples.setdefault(vk, set()).add(sid)

    top_genes = sorted(gene_counts.items(), key=lambda x: -x[1])[:15]
    top_genes_out = [
        {
            "gene": g,
            "count": c,
            "sample_count": len(gene_samples.get(g, set())),
            "sample_pct": round(100 * len(gene_samples.get(g, set())) / len(sample_ids), 1),
        }
        for g, c in top_genes
    ]

    shared = []
    variant_gene_map = {}
    for v in variants:
        vk = f"{v.get('chrom')}:{v.get('pos')}:{v.get('ref')}>{v.get('alt')}"
        variant_gene_map[vk] = v.get("gene")

    for vk, sids in variant_samples.items():
        if len(sids) > 1:
            shared.append({
                "variant": vk,
                "gene": variant_gene_map.get(vk),
                "sample_count": len(sids),
                "sample_pct": round(100 * len(sids) / len(sample_ids), 1),
            })
    shared = sorted(shared, key=lambda x: -x["sample_count"])[:25]

    log_action(user.id, "view_stats", "cohort", cohort_id, {"n_samples": len(sample_ids)})

    return {
        "n_samples": len(sample_ids),
        "n_variants": len(variants),
        "classification": counts,
        "top_genes": top_genes_out,
        "shared_variants": shared,
    }


@router.delete("/{cohort_id}")
async def delete_cohort(cohort_id: str, user=Depends(get_current_user)):
    supabase.table("cohorts").delete().eq("id", cohort_id).execute()
    log_action(user.id, "delete", "cohort", cohort_id)
    return {"ok": True}
