"""
Cohort analysis: PCA across samples using variant presence/absence.

Loads variants per-sample (using sample_id singular) instead of relying on
the in_sample_ids filter, which works differently across backends.
"""
import math
from app.db import get_db
from sklearn.decomposition import PCA
import numpy as np


def safe_float(v):
    try:
        f = float(v)
        return f if math.isfinite(f) else 0.0
    except (TypeError, ValueError):
        return 0.0


def build_variant_matrix(sample_ids: list[str], max_variants: int = 5000) -> tuple:
    """Build a variant presence matrix. Loads per-sample for compatibility."""
    errors = []
    db = get_db()
    sample_variant_sets = {}

    for sid in sample_ids:
        try:
            rows, _ = db.list_variants({"sample_id": sid}, limit=max_variants, offset=0)
            keys = {f"{r['chrom']}:{r['pos']}:{r['ref']}>{r['alt']}" for r in rows if r.get('chrom')}
            sample_variant_sets[sid] = keys
            print(f"[PCA] {sid[:8]}... → {len(keys)} variants")
        except Exception as e:
            errors.append(f"Failed to load {sid}: {e}")
            sample_variant_sets[sid] = set()
            print(f"[PCA] FAIL {sid[:8]}: {e}")

    all_variants = set()
    for keys in sample_variant_sets.values():
        all_variants.update(keys)

    print(f"[PCA] Union: {len(all_variants)} unique variants")

    if not all_variants:
        return None, sample_ids, [], errors

    all_variants = sorted(all_variants)[:max_variants]

    matrix = np.zeros((len(sample_ids), len(all_variants)), dtype=float)
    for i, sid in enumerate(sample_ids):
        for j, vk in enumerate(all_variants):
            if vk in sample_variant_sets[sid]:
                matrix[i, j] = 1.0

    return matrix, sample_ids, all_variants, errors


def compute_pca(sample_ids: list[str], n_components: int = 2) -> dict:
    print(f"[PCA] Starting with {len(sample_ids)} samples")
    matrix, sids, variant_keys, errors = build_variant_matrix(sample_ids)

    if matrix is None:
        return {
            "error": "No variants found across these samples. "
                     "Make sure each sample has been uploaded and parsed successfully.",
            "errors": errors,
        }

    print(f"[PCA] Matrix: {matrix.shape}")
    if matrix.shape[0] < 2:
        return {"error": "Need at least 2 samples", "errors": errors}
    if matrix.shape[1] < 2:
        return {"error": "Need at least 2 distinct variants across samples", "errors": errors}

    k = min(n_components, matrix.shape[0], matrix.shape[1])
    try:
        pca = PCA(n_components=k)
        coords = pca.fit_transform(matrix)
        explained = pca.explained_variance_ratio_.tolist()
    except Exception as e:
        return {"error": f"PCA failed: {e}", "errors": errors}

    coords = [[safe_float(x) for x in row] for row in coords]
    explained = [safe_float(x) for x in explained]

    sample_names = {}
    for sid in sids:
        try:
            s = db_sample(sid)
            sample_names[sid] = s["name"] if s else sid[:8]
        except Exception:
            sample_names[sid] = sid[:8]

    points = [
        {
            "sample_id": sid,
            "name": sample_names.get(sid, sid[:8]),
            "x": coords[i][0] if len(coords[i]) > 0 else 0.0,
            "y": coords[i][1] if len(coords[i]) > 1 else 0.0,
        }
        for i, sid in enumerate(sids)
    ]

    print(f"[PCA] Returning {len(points)} points")
    return {
        "points": points,
        "explained_variance": explained,
        "n_variants": len(variant_keys),
        "n_samples": len(sids),
        "errors": errors,
    }


def db_sample(sid):
    return get_db().get_sample(sid)
