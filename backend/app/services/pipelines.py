"""
Minimal pipeline runner.
Real subprocess execution, real logs, real status updates.
Pipelines are Python functions, not Nextflow — swap later if needed.
"""
import os
import subprocess
import sys
from datetime import datetime
from app.supabase_client import supabase
from app.config import settings


PIPELINES = {
    "variant_stats": {
        "name": "Variant Stats",
        "description": "Count variants, SNPs, indels, and genes for a sample.",
    },
    "annotation_refresh": {
        "name": "Annotation Refresh",
        "description": "Re-run MyVariant.info annotation on all variants.",
    },
    "qc_deep": {
        "name": "Deep QC",
        "description": "Compute per-chromosome variant distribution.",
    },
}


def list_pipelines():
    return [{"id": k, **v} for k, v in PIPELINES.items()]


def run_pipeline(run_id: str, pipeline_id: str, sample_id: str):
    """
    Execute a pipeline in a subprocess. Update the run record as we go.
    Runs synchronously inside a background task.
    """
    _update_run(run_id, {"status": "running", "started_at": datetime.utcnow().isoformat()})

    script = _get_script(pipeline_id, sample_id)
    if not script:
        _update_run(run_id, {
            "status": "failed",
            "logs": f"Unknown pipeline: {pipeline_id}",
            "finished_at": datetime.utcnow().isoformat(),
        })
        return

    log_lines = []

    try:
        env = os.environ.copy()
        env["SUPABASE_URL"] = settings.SUPABASE_URL
        env["SUPABASE_SERVICE_KEY"] = settings.SUPABASE_SERVICE_KEY
        env["SUPABASE_ANON_KEY"] = settings.SUPABASE_ANON_KEY

        proc = subprocess.Popen(
            [sys.executable, "-c", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )

        for line in proc.stdout:
            log_lines.append(line.rstrip())
            if len(log_lines) % 5 == 0:
                _update_run(run_id, {"logs": "\n".join(log_lines[-200:])})

        proc.wait()

        status = "completed" if proc.returncode == 0 else "failed"
        _update_run(run_id, {
            "status": status,
            "logs": "\n".join(log_lines[-200:]),
            "finished_at": datetime.utcnow().isoformat(),
        })

    except Exception as e:
        _update_run(run_id, {
            "status": "failed",
            "logs": "\n".join(log_lines) + f"\n\nERROR: {e}",
            "finished_at": datetime.utcnow().isoformat(),
        })


def _update_run(run_id: str, patch: dict):
    try:
        supabase.table("pipeline_runs").update(patch).eq("id", run_id).execute()
    except Exception as e:
        print(f"Failed to update run {run_id}: {e}")


def _get_script(pipeline_id: str, sample_id: str) -> str | None:
    """Return a Python script string that the runner will execute."""
    common = f'''
import os
from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
sb = create_client(url, key)
SAMPLE_ID = "{sample_id}"

def fetch_variants():
    return sb.table("variants").select("*").eq("sample_id", SAMPLE_ID).execute().data or []

print(f"Starting pipeline for sample {{SAMPLE_ID[:8]}}...")
variants = fetch_variants()
print(f"Loaded {{len(variants)}} variants from Supabase.")
'''

    if pipeline_id == "variant_stats":
        return common + '''
snp = sum(1 for v in variants if len(v.get("ref") or "") == 1 and len(v.get("alt") or "") == 1)
indel = len(variants) - snp
genes = set(v.get("gene") for v in variants if v.get("gene"))
print(f"SNPs: {snp}")
print(f"Indels: {indel}")
print(f"Unique genes: {len(genes)}")
print("Gene list:", ", ".join(sorted(genes)) or "(none)")
print("Pipeline completed successfully.")
'''

    if pipeline_id == "annotation_refresh":
        return common + '''
import httpx

MYVARIANT = "https://myvariant.info/v1/query"

missing = [v for v in variants if not v.get("gene")]
print(f"Variants missing gene annotation: {len(missing)}")
updated = 0

for v in missing[:50]:
    try:
        r = httpx.get(
            MYVARIANT,
            params={
                "q": f"chr{v['chrom']}:{v['pos']}-{v['pos']}",
                "assembly": "hg38",
                "size": 1,
                "fields": "dbsnp,clinvar,snpeff",
            },
            timeout=15.0,
        )
        if r.status_code != 200:
            continue
        hits = r.json().get("hits", [])
        if not hits:
            continue
        hit = hits[0]

        gene = None
        cv = hit.get("clinvar") or {}
        if isinstance(cv, dict) and isinstance(cv.get("gene"), dict):
            gene = cv["gene"].get("symbol")

        clinvar_sig = None
        if isinstance(cv, dict):
            rcv = cv.get("rcv")
            if isinstance(rcv, dict):
                clinvar_sig = rcv.get("clinical_significance")
            elif isinstance(rcv, list) and rcv and isinstance(rcv[0], dict):
                clinvar_sig = rcv[0].get("clinical_significance")

        consequence = None
        impact = None
        snpeff = hit.get("snpeff") or {}
        if isinstance(snpeff, dict):
            anns = snpeff.get("ann")
            if isinstance(anns, dict):
                anns = [anns]
            if isinstance(anns, list) and anns:
                best = anns[0]
                consequence = best.get("effect")
                impact = best.get("putative_impact")

        if gene:
            sb.table("variants").update({
                "gene": gene,
                "consequence": consequence,
                "impact": impact,
                "clinvar_significance": clinvar_sig,
            }).eq("id", v["id"]).execute()
            updated += 1
            print(f"  {v['chrom']}:{v['pos']} -> {gene}")
    except Exception as e:
        print(f"  Failed for {v['chrom']}:{v['pos']}: {e}")

print(f"Updated {updated} variants.")
print("Pipeline completed successfully.")
'''

    if pipeline_id == "qc_deep":
        return common + '''
from collections import Counter
chrom_counts = Counter(v.get("chrom") for v in variants)
print("Per-chromosome variant counts:")
for chrom, count in sorted(chrom_counts.items()):
    print(f"  chr{chrom}: {count}")
print(f"Total chromosomes covered: {len(chrom_counts)}")
print("Pipeline completed successfully.")
'''

    return None
