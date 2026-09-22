"""
Reproducibility provenance: record every pipeline run, tool version, and input hash.
"""
import hashlib
import json
import platform
import sys
from datetime import datetime
from app.supabase_client import supabase


PIPELINE_VERSION = "0.1.0"


def _container_hash() -> str:
    """Stable hash of the runtime environment."""
    parts = [
        f"python={sys.version.split()[0]}",
        f"platform={platform.platform()}",
    ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _hash_inputs(data) -> str:
    """Deterministic hash of input data."""
    if isinstance(data, dict):
        data = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(str(data).encode()).hexdigest()[:16]


def record_provenance(
    resource_type: str,
    resource_id: str,
    reference_genome: str = "GRCh38",
    annotation_db_version: str = None,
    command: str = None,
    inputs: dict = None,
    outputs: dict = None,
) -> str:
    """Record a provenance entry. Returns the provenance ID."""
    tool_versions = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "pipeline": PIPELINE_VERSION,
        "vep": "REST (Ensembl)",
        "myvariant": "myvariant.info",
        "clinvar": "NCBI E-utilities",
    }

    entry = {
        "resource_type": resource_type,
        "resource_id": resource_id,
        "reference_genome": reference_genome,
        "pipeline_version": PIPELINE_VERSION,
        "tool_versions": tool_versions,
        "annotation_db_version": annotation_db_version,
        "container_hash": _container_hash(),
        "command": command,
        "inputs": inputs or {},
        "outputs": outputs or {},
    }

    try:
        resp = supabase.table("provenance").insert(entry).execute()
        return resp.data[0]["id"] if resp.data else ""
    except Exception as e:
        print(f"Failed to record provenance: {e}")
        return ""


def compute_provenance_hash(entry: dict) -> str:
    """Compute a deterministic hash of a provenance entry."""
    return _hash_inputs(entry)


def get_provenance(resource_type: str, resource_id: str) -> list[dict]:
    """Fetch all provenance entries for a resource."""
    try:
        resp = supabase.table("provenance") \
            .select("*") \
            .eq("resource_type", resource_type) \
            .eq("resource_id", resource_id) \
            .order("created_at", desc=True) \
            .execute()
        return resp.data or []
    except Exception as e:
        print(f"Failed to fetch provenance: {e}")
        return []
