"""
Pipeline runner. Runs in-process (no subprocess) so it can use the DB abstraction
in both cloud and local modes.

Each pipeline is a Python function that takes (db, sample_id, log_fn) and does its work,
calling log_fn to emit output that gets saved to the run record.
"""
import time
from datetime import datetime, timezone
from app.db import get_db
from app.netgate import safe_get, OfflineModeError


PIPELINES = {
    "variant_stats": {
        "name": "Variant Stats",
        "description": "Count variants, SNPs, indels, and genes for a sample.",
    },
    "annotation_refresh": {
        "name": "Annotation Refresh",
        "description": "Re-run MyVariant.info annotation on variants missing gene info.",
    },
    "qc_deep": {
        "name": "Deep QC",
        "description": "Per-chromosome variant distribution.",
    },
}


def list_pipelines():
    return [{"id": k, **v} for k, v in PIPELINES.items()]


def run_pipeline(run_id: str, pipeline_id: str, sample_id: str):
    """Background task. Updates the run record as it works."""
    db = get_db()
    logs = []

    def log(line: str):
        logs.append(line)
        print(f"[PIPELINE {run_id[:8]}] {line}")
        # Persist every few lines
        if len(logs) % 3 == 0:
            db.update_pipeline_run(run_id, {"logs": "\n".join(logs[-200:])})

    try:
        db.update_pipeline_run(run_id, {
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
        })

        handler = _PIPELINES.get(pipeline_id)
        if not handler:
            log(f"Unknown pipeline: {pipeline_id}")
            db.update_pipeline_run(run_id, {
                "status": "failed",
                "logs": "\n".join(logs),
                "finished_at": datetime.now(timezone.utc).isoformat(),
            })
            return

        log(f"Starting {PIPELINES[pipeline_id]['name']} for sample {sample_id[:8]}...")
        handler(db, sample_id, log)

        log("Pipeline completed successfully.")
        db.update_pipeline_run(run_id, {
            "status": "completed",
            "logs": "\n".join(logs[-200:]),
            "finished_at": datetime.now(timezone.utc).isoformat(),
        })

    except OfflineModeError as e:
        log(f"OFFLINE: {e}")
        db.update_pipeline_run(run_id, {
            "status": "failed",
            "logs": "\n".join(logs),
            "finished_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        log(f"ERROR: {e}")
        import traceback
        log(traceback.format_exc()[-500:])
        db.update_pipeline_run(run_id, {
            "status": "failed",
            "logs": "\n".join(logs),
            "finished_at": datetime.now(timezone.utc).isoformat(),
        })


# ---------- Individual pipeline handlers ----------

def _variant_stats(db, sample_id, log):
    variants, _ = db.list_variants({"sample_id": sample_id}, limit=1000000, offset=0)
    log(f"Loaded {len(variants)} variants from database.")

    snp = sum(1 for v in variants if len(v.get("ref") or "") == 1 and len(v.get("alt") or "") == 1)
    indel = len(variants) - snp
    genes = sorted({v.get("gene") for v in variants if v.get("gene")})

    log(f"SNPs: {snp}")
    log(f"Indels: {indel}")
    log(f"Unique genes: {len(genes)}")
    if genes:
        log("Gene list: " + ", ".join(genes))


def _annotation_refresh(db, sample_id, log):
    from app.config import settings
    from app.services.license import get_network_policy
    if get_network_policy() == "blocked":
        log("Network policy is 'blocked' — cannot reach annotation sources.")
        log("Activate a license to enable annotation.")
        return

    variants, _ = db.list_variants({"sample_id": sample_id}, limit=1000000, offset=0)
    missing = [v for v in variants if not v.get("gene")]
    log(f"Variants missing gene annotation: {len(missing)}")

    if not missing:
        log("Nothing to annotate.")
        return

    from app.services.annotate import annotate_with_myvariant
    updated = 0
    for i, v in enumerate(missing[:100]):
        try:
            ann = annotate_with_myvariant(v["chrom"], v["pos"], v["ref"], v["alt"])
            if ann.get("gene"):
                db.update_variant(v["id"], {
                    "gene": ann.get("gene"),
                    "consequence": ann.get("consequence"),
                    "impact": ann.get("impact"),
                    "clinvar_significance": ann.get("clinvar_significance"),
                })
                updated += 1
                log(f"  {v['chrom']}:{v['pos']} -> {ann.get('gene')}")
        except OfflineModeError:
            raise
        except Exception as e:
            log(f"  Failed {v['chrom']}:{v['pos']}: {e}")

    log(f"Updated {updated} variants.")


def _qc_deep(db, sample_id, log):
    variants, _ = db.list_variants({"sample_id": sample_id}, limit=1000000, offset=0)
    from collections import Counter
    chrom_counts = Counter(v.get("chrom") for v in variants if v.get("chrom"))
    log("Per-chromosome variant counts:")
    for chrom, count in sorted(chrom_counts.items()):
        log(f"  chr{chrom}: {count}")
    log(f"Total chromosomes covered: {len(chrom_counts)}")


_PIPELINES = {
    "variant_stats": _variant_stats,
    "annotation_refresh": _annotation_refresh,
    "qc_deep": _qc_deep,
}
