"""
QC metrics calculation. Uses the DB abstraction.
"""
from app.db import get_db


def compute_qc_from_variants(sample_id: str):
    db = get_db()
    variants, _ = db.list_variants({"sample_id": sample_id}, limit=1000000, offset=0)
    if not variants:
        return None

    snp_count = 0
    indel_count = 0
    quals = []

    for v in variants:
        ref = v.get("ref") or ""
        alt = v.get("alt") or ""
        if len(ref) == 1 and len(alt) == 1:
            snp_count += 1
        else:
            indel_count += 1
        if v.get("qual") is not None:
            quals.append(v["qual"])

    metrics = {
        "sample_id": sample_id,
        "variant_count": len(variants),
        "snp_count": snp_count,
        "indel_count": indel_count,
        "mean_coverage": (sum(quals) / len(quals)) if quals else None,
    }

    db.insert_qc_metrics(metrics)
    return metrics
