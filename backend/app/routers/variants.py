from fastapi import APIRouter, Depends, Query
from app.db import get_db
from app.deps import get_current_user, get_current_org
from app.user import CurrentUser

router = APIRouter(prefix="/variants", tags=["variants"])


@router.get("/")
async def list_variants(
    sample_id: str = None,
    cohort_id: str = None,
    gene: str = None,
    genes: str = None,
    chrom: str = None,
    clinvar: str = None,
    clinvar_class: str = None,
    acmg_class: str = None,
    impact: str = None,
    prioritised: bool = False,
    limit: int = Query(200, le=2000),
    offset: int = 0,
    user: CurrentUser = Depends(get_current_user),
    org=Depends(get_current_org),
):
    db = get_db()
    filters = {}

    if cohort_id:
        cohort = db.get_cohort(cohort_id)
        if cohort and cohort.get("sample_ids"):
            filters["in_sample_ids"] = cohort["sample_ids"]
        else:
            return {"data": [], "count": 0}

    if sample_id:
        filters["sample_id"] = sample_id
    if gene:
        filters["gene"] = gene
    if genes:
        gene_list = [g.strip() for g in genes.split(",") if g.strip()]
        if gene_list:
            filters["gene_panel"] = gene_list
    if chrom:
        filters["chrom"] = chrom
    if impact:
        filters["impact"] = impact.upper()
    if clinvar:
        filters["clinvar"] = clinvar

    variants, total = db.list_variants(filters, limit=limit, offset=offset)

    # ACMG enrichment
    for v in variants:
        a = db.get_variant_acmg(v["id"])
        v["acmg_classification"] = a["classification"] if a else None
        v["acmg_confidence"] = a["confidence"] if a else None
        v["acmg_summary"] = a["evidence_summary"] if a else None

    # Post-filter for complex cases not in the DB layer
    if clinvar_class:
        cc = clinvar_class.lower()
        def match(v):
            cs = (v.get("clinvar_significance") or "").lower()
            if cc == "pathogenic":
                return "pathogenic" in cs
            if cc == "benign":
                return "benign" in cs
            if cc == "vus":
                return "uncertain" in cs
            return True
        variants = [v for v in variants if match(v)]

    if acmg_class:
        variants = [v for v in variants if (v.get("acmg_classification") or "").lower() == acmg_class.lower()]

    if prioritised:
        def is_priority(v):
            cs = (v.get("clinvar_significance") or "").lower()
            imp = (v.get("impact") or "").upper()
            return "pathogenic" in cs or imp in ("HIGH", "MODERATE")
        variants = [v for v in variants if is_priority(v)]

    return {"data": variants, "count": total}


@router.get("/summary")
async def variant_summary(
    sample_id: str = None,
    cohort_id: str = None,
    user: CurrentUser = Depends(get_current_user),
    org=Depends(get_current_org),
):
    db = get_db()
    filters = {}
    if cohort_id:
        cohort = db.get_cohort(cohort_id)
        if cohort and cohort.get("sample_ids"):
            filters["in_sample_ids"] = cohort["sample_ids"]
    if sample_id:
        filters["sample_id"] = sample_id

    variants, _ = db.list_variants(filters, limit=10000, offset=0)

    counts = {"pathogenic": 0, "vus": 0, "benign": 0, "other": 0}
    high_impact = 0
    genes = {}
    acmg_counts = {}

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

        if (v.get("impact") or "").upper() == "HIGH":
            high_impact += 1

        g = v.get("gene")
        if g:
            genes[g] = genes.get(g, 0) + 1

        a = db.get_variant_acmg(v["id"])
        if a:
            c = a.get("classification") or "VUS"
            acmg_counts[c] = acmg_counts.get(c, 0) + 1

    top_genes = sorted(genes.items(), key=lambda x: -x[1])[:10]

    return {
        "total": len(variants),
        "counts": counts,
        "high_impact": high_impact,
        "top_genes": [{"gene": g, "count": c} for g, c in top_genes],
        "acmg_counts": acmg_counts,
    }
