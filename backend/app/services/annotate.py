"""
Variant annotation via MyVariant.info.
Aggregates ClinVar, dbSNP, and SnpEff data in one call.
Free, no API key needed. Assembly: hg38 (GRCh38).
"""
import httpx
import time
from typing import Optional

MYVARIANT_QUERY = "https://myvariant.info/v1/query"
TIMEOUT = httpx.Timeout(20.0, connect=8.0)


def annotate_variant(chrom: str, pos: int, ref: str, alt: str, rsid: str = None) -> dict:
    """
    Query MyVariant.info for one variant.
    Returns: gene, consequence, impact, clinvar_significance
    """
    result = {
        "gene": None,
        "consequence": None,
        "impact": None,
        "clinvar_significance": None,
    }

    try:
        r = httpx.get(
            MYVARIANT_QUERY,
            params={
                "q": f"chr{chrom}:{pos}-{pos}",
                "assembly": "hg38",
                "size": 1,
                "fields": "dbsnp,clinvar,snpeff",
            },
            headers={"Accept": "application/json"},
            timeout=TIMEOUT,
        )

        if r.status_code != 200:
            print(f"MyVariant HTTP {r.status_code} for {chrom}:{pos}")
            return result

        data = r.json()
        hits = data.get("hits", [])
        if not hits:
            print(f"MyVariant no hits for {chrom}:{pos}")
            return result

        hit = hits[0]

        # ---- Gene (from ClinVar first, then dbSNP) ----
        clinvar = hit.get("clinvar") or {}
        if isinstance(clinvar, dict):
            gene_obj = clinvar.get("gene")
            if isinstance(gene_obj, dict):
                result["gene"] = gene_obj.get("symbol")

        if not result["gene"]:
            dbsnp = hit.get("dbsnp") or {}
            gene_field = dbsnp.get("gene") if isinstance(dbsnp, dict) else None
            if isinstance(gene_field, dict):
                result["gene"] = gene_field.get("symbol")
            elif isinstance(gene_field, list) and gene_field:
                first = gene_field[0]
                if isinstance(first, dict):
                    result["gene"] = first.get("symbol")

        # ---- ClinVar significance ----
        if isinstance(clinvar, dict):
            rcv = clinvar.get("rcv")
            if isinstance(rcv, dict):
                result["clinvar_significance"] = rcv.get("clinical_significance")
            elif isinstance(rcv, list) and rcv:
                first = rcv[0]
                if isinstance(first, dict):
                    result["clinvar_significance"] = first.get("clinical_significance")

        # ---- Consequence + impact (from SnpEff) ----
        snpeff = hit.get("snpeff") or {}
        if isinstance(snpeff, dict):
            anns = snpeff.get("ann")
            if isinstance(anns, dict):
                anns = [anns]
            if isinstance(anns, list) and anns:
                # Pick highest impact
                rank = {"HIGH": 4, "MODERATE": 3, "LOW": 2, "MODIFIER": 1}
                best = max(
                    anns,
                    key=lambda a: rank.get(a.get("putative_impact", "MODIFIER"), 0),
                )
                result["consequence"] = best.get("effect")
                result["impact"] = best.get("putative_impact")

    except Exception as e:
        print(f"MyVariant failed for {chrom}:{pos} {ref}>{alt}: {e}")

    return result


def annotate_batch(variants: list[dict]) -> list[dict]:
    """Annotate a batch. Sleep 0.1s between calls to be polite."""
    annotated = []
    for i, v in enumerate(variants):
        try:
            ann = annotate_variant(v["chrom"], v["pos"], v["ref"], v["alt"], v.get("rsid"))
            v.update(ann)
        except Exception as e:
            print(f"Annotation failed for variant {i}: {e}")
        annotated.append(v)
        time.sleep(0.1)
    return annotated
