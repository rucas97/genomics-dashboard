from fastapi import APIRouter, Depends, Query
from app.supabase_client import supabase
from app.deps import get_current_user

router = APIRouter(prefix="/variants", tags=["variants"])


@router.get("/")
async def list_variants(
    sample_id: str = None,
    cohort_id: str = None,
    gene: str = None,
    genes: str = None,          # comma-separated gene panel
    chrom: str = None,
    clinvar: str = None,        # exact match
    clinvar_class: str = None,  # pathogenicity group: pathogenic | vus | benign
    impact: str = None,         # HIGH | MODERATE | LOW | MODIFIER
    prioritised: bool = False,  # only pathogenic + high/moderate impact
    limit: int = Query(200, le=2000),
    offset: int = 0,
    user=Depends(get_current_user),
):
    q = supabase.table("variants").select("*", count="exact")

    # Cohort support: filter by all samples in a cohort
    if cohort_id:
        cresp = supabase.table("cohorts").select("sample_ids").eq("id", cohort_id).execute()
        if cresp.data and cresp.data[0].get("sample_ids"):
            q = q.in_("sample_id", cresp.data[0]["sample_ids"])

    if sample_id:
        q = q.eq("sample_id", sample_id)
    if gene:
        q = q.eq("gene", gene)
    if genes:
        gene_list = [g.strip() for g in genes.split(",") if g.strip()]
        if gene_list:
            q = q.in_("gene", gene_list)
    if chrom:
        q = q.eq("chrom", chrom)
    if clinvar:
        q = q.eq("clinvar_significance", clinvar)

    if clinvar_class:
        cc = clinvar_class.lower()
        if cc == "pathogenic":
            q = q.or_(
                "clinvar_significance.ilike.*pathogenic*,"
                "clinvar_significance.ilike.*likely_pathogenic*,"
                "clinvar_significance.ilike.*likely pathogenic*"
            )
        elif cc == "benign":
            q = q.or_(
                "clinvar_significance.ilike.*benign*,"
                "clinvar_significance.ilike.*likely_benign*,"
                "clinvar_significance.ilike.*likely benign*"
            )
        elif cc == "vus":
            q = q.ilike("clinvar_significance", "*uncertain*")

    if impact:
        q = q.eq("impact", impact.upper())

    if prioritised:
        # Pathogenic OR high/moderate impact
        q = q.or_(
            "clinvar_significance.ilike.*pathogenic*,"
            "impact.eq.HIGH,"
            "impact.eq.MODERATE"
        )

    resp = q.range(offset, offset + limit - 1).execute()
    return {"data": resp.data, "count": resp.count}


@router.get("/summary")
async def variant_summary(
    sample_id: str = None,
    cohort_id: str = None,
    user=Depends(get_current_user),
):
    """Clinical summary counts: pathogenic / vus / benign / other."""
    q = supabase.table("variants").select("clinvar_significance,impact,gene")
    if cohort_id:
        cresp = supabase.table("cohorts").select("sample_ids").eq("id", cohort_id).execute()
        if cresp.data and cresp.data[0].get("sample_ids"):
            q = q.in_("sample_id", cresp.data[0]["sample_ids"])
    if sample_id:
        q = q.eq("sample_id", sample_id)

    resp = q.execute()
    rows = resp.data or []

    counts = {"pathogenic": 0, "vus": 0, "benign": 0, "other": 0}
    high_impact = 0
    genes = {}

    for r in rows:
        cs = (r.get("clinvar_significance") or "").lower()
        if "pathogenic" in cs or "likely_pathogenic" in cs or "likely pathogenic" in cs:
            counts["pathogenic"] += 1
        elif "benign" in cs:
            counts["benign"] += 1
        elif "uncertain" in cs:
            counts["vus"] += 1
        else:
            counts["other"] += 1

        if (r.get("impact") or "").upper() == "HIGH":
            high_impact += 1

        g = r.get("gene")
        if g:
            genes[g] = genes.get(g, 0) + 1

    top_genes = sorted(genes.items(), key=lambda x: -x[1])[:10]

    return {
        "total": len(rows),
        "counts": counts,
        "high_impact": high_impact,
        "top_genes": [{"gene": g, "count": c} for g, c in top_genes],
    }
