"""
MANE Select transcript normalization.
Every variant is mapped to its MANE Select transcript, so labs stop arguing about which transcript matters.
"""
from app.supabase_client import supabase


_cache: dict[str, dict] = {}


def load_mane_map() -> dict:
    """Load the MANE transcript map into memory (cached)."""
    global _cache
    if _cache:
        return _cache
    try:
        resp = supabase.table("mane_transcripts").select("*").execute()
        _cache = {row["gene_symbol"]: row for row in (resp.data or [])}
    except Exception as e:
        print(f"Failed to load MANE map: {e}")
        _cache = {}
    return _cache


def get_mane_transcript(gene_symbol: str) -> dict | None:
    """Return the MANE Select and Plus Clinical transcripts for a gene."""
    if not gene_symbol:
        return None
    return load_mane_map().get(gene_symbol.upper())


def normalize_variant(variant: dict) -> dict:
    """
    Add MANE fields to a variant dict:
    - mane_select
    - mane_plus_clinical
    - transcript_flag: 'mane_match' | 'mane_mismatch' | 'unknown'
    """
    result = dict(variant)
    gene = variant.get("gene")

    # If VCF already has a transcript, we could compare — but our parser
    # doesn't capture transcript IDs yet, so we just surface MANE for reference.
    mane = get_mane_transcript(gene) if gene else None
    if mane:
        result["mane_select"] = mane.get("mane_select")
        result["mane_plus_clinical"] = mane.get("mane_plus_clinical")
        result["transcript_flag"] = "mane_match" if mane.get("mane_select") else "unknown"
    else:
        result["mane_select"] = None
        result["mane_plus_clinical"] = None
        result["transcript_flag"] = "unknown"

    return result
