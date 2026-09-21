from app.supabase_client import supabase

def compute_qc_from_variants(sample_id: str):
    resp = supabase.table("variants").select("ref,alt,qual").eq("sample_id", sample_id).execute()
    rows = resp.data or []
    if not rows:
        return None

    snp_count = 0
    indel_count = 0
    quals = []

    for r in rows:
        ref = r.get("ref") or ""
        alt = r.get("alt") or ""
        if len(ref) == 1 and len(alt) == 1:
            snp_count += 1
        else:
            indel_count += 1
        if r.get("qual") is not None:
            quals.append(r["qual"])

    metrics = {
        "sample_id": sample_id,
        "variant_count": len(rows),
        "snp_count": snp_count,
        "indel_count": indel_count,
        "mean_coverage": (sum(quals) / len(quals)) if quals else None,
    }
    supabase.table("qc_metrics").insert(metrics).execute()
    return metrics
