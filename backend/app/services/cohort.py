"""
Cohort analysis: PCA across samples using variant presence/absence.
"""
import math
from app.supabase_client import supabase
from sklearn.decomposition import PCA
import numpy as np


def safe_float(v):
    """Convert NaN/inf to 0.0 so JSON is valid."""
    try:
        f = float(v)
        return f if math.isfinite(f) else 0.0
    except (TypeError, ValueError):
        return 0.0


def build_variant_matrix(sample_ids: list[str], max_variants: int = 5000) -> tuple:
    """
    Build a variant presence matrix across samples.
    Returns (matrix, sample_ids, variant_keys, errors)
    matrix shape: (n_samples, n_variants), values 0 or 1
    """
    errors = []

    sample_variant_sets = {}
    for sid in sample_ids:
        try:
            resp = supabase.table("variants").select("chrom,pos,ref,alt").eq("sample_id", sid).execute()
            rows = resp.data or []
            keys = {f"{r['chrom']}:{r['pos']}:{r['ref']}>{r['alt']}" for r in rows}
            sample_variant_sets[sid] = keys
        except Exception as e:
            errors.append(f"Failed to load variants for {sid}: {e}")
            sample_variant_sets[sid] = set()

    all_variants = set()
    for keys in sample_variant_sets.values():
        all_variants.update(keys)
    all_variants = sorted(all_variants)[:max_variants]

    if not all_variants:
        return None, sample_ids, [], errors

    matrix = np.zeros((len(sample_ids), len(all_variants)), dtype=float)
    for i, sid in enumerate(sample_ids):
        for j, vk in enumerate(all_variants):
            if vk in sample_variant_sets[sid]:
                matrix[i, j] = 1.0

    return matrix, sample_ids, all_variants, errors


def compute_pca(sample_ids: list[str], n_components: int = 2) -> dict:
    """
    Run PCA on the variant matrix. Returns coordinates per sample.
    All returned floats are sanitized (no NaN/inf).
    """
    matrix, sids, variant_keys, errors = build_variant_matrix(sample_ids)

    if matrix is None:
        return {"error": "No variants found across these samples", "errors": errors}

    if matrix.shape[0] < 2:
        return {"error": "Need at least 2 samples for PCA", "errors": errors}

    if matrix.shape[1] < 2:
        return {"error": "Need at least 2 distinct variants for PCA", "errors": errors}

    k = min(n_components, matrix.shape[0], matrix.shape[1])

    try:
        pca = PCA(n_components=k)
        coords = pca.fit_transform(matrix)
        explained = pca.explained_variance_ratio_.tolist()
    except Exception as e:
        return {"error": f"PCA failed: {e}", "errors": errors}

    # Sanitize NaN/inf -> 0.0
    coords = [[safe_float(x) for x in row] for row in coords]
    explained = [safe_float(x) for x in explained]

    # Sample names for the frontend
    sample_names = {}
    for sid in sids:
        try:
            resp = supabase.table("samples").select("name").eq("id", sid).execute()
            if resp.data:
                sample_names[sid] = resp.data[0]["name"]
        except Exception:
            sample_names[sid] = sid[:8]

    points = []
    for i, sid in enumerate(sids):
        points.append({
            "sample_id": sid,
            "name": sample_names.get(sid, sid[:8]),
            "x": coords[i][0] if len(coords[i]) > 0 else 0.0,
            "y": coords[i][1] if len(coords[i]) > 1 else 0.0,
        })

    return {
        "points": points,
        "explained_variance": explained,
        "n_variants": len(variant_keys),
        "n_samples": len(sids),
        "errors": errors,
    }
