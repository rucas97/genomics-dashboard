"""
Variant annotation via public APIs — gated by offline mode.
All outbound calls go through netgate. In offline mode, they raise.
"""
import time
from typing import Optional
from app.netgate import safe_get, OfflineModeError


VEP_URL = "https://rest.ensembl.org/vep/human/region"
MYVARIANT_URL = "https://myvariant.info/v1/variant"
MYVARIANT_QUERY = "https://myvariant.info/v1/query"

TIMEOUT = 20.0
HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}


def annotate_with_vep(chrom: str, pos: int, ref: str, alt: str) -> dict:
    result = {"gene": None, "consequence": None, "impact": None}
    try:
        region = f"{chrom} {pos} {pos + len(ref) - 1} {alt}"
        r = safe_get(
            f"{VEP_URL}/{region}",
            params={"content-type": "application/json"},
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and data:
                tc = data[0].get("transcript_consequences") or []
                if tc:
                    rank = {"HIGH": 4, "MODERATE": 3, "LOW": 2, "MODIFIER": 1}
                    best = max(tc, key=lambda t: rank.get(t.get("impact", "MODIFIER"), 0))
                    result["gene"] = best.get("gene_symbol")
                    csq = best.get("consequence_terms") or []
                    result["consequence"] = csq[0] if csq else None
                    result["impact"] = best.get("impact")
    except OfflineModeError:
        raise
    except Exception as e:
        print(f"VEP failed for {chrom}:{pos} {ref}>{alt}: {e}")
    return result


def annotate_with_myvariant(chrom: str, pos: int, ref: str, alt: str) -> dict:
    result = {"gene": None, "consequence": None, "clinvar_significance": None}
    try:
        r = safe_get(
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

        if isinstance(clinvar, dict):
            rcv = clinvar.get("rcv")
            if isinstance(rcv, dict):
                result["clinvar_significance"] = rcv.get("clinical_significance")
            elif isinstance(rcv, list) and rcv:
                first = rcv[0]
                if isinstance(first, dict):
                    result["clinvar_significance"] = first.get("clinical_significance")

        snpeff = hit.get("snpeff") or {}
        if isinstance(snpeff, dict):
            anns = snpeff.get("ann")
            if isinstance(anns, dict):
                anns = [anns]
            if isinstance(anns, list) and anns:
                rank = {"HIGH": 4, "MODERATE": 3, "LOW": 2, "MODIFIER": 1}
                best = max(anns, key=lambda a: rank.get(a.get("putative_impact", "MODIFIER"), 0))
                result["consequence"] = best.get("effect")
                result["impact"] = best.get("putative_impact")
    except OfflineModeError:
        raise
    except Exception as e:
        print(f"MyVariant failed for {chrom}:{pos} {ref}>{alt}: {e}")
    return result


def annotate_variant(chrom: str, pos: int, ref: str, alt: str, rsid: str = None) -> dict:
    vep = annotate_with_vep(chrom, pos, ref, alt)
    if vep.get("gene"):
        return vep
    mv = annotate_with_myvariant(chrom, pos, ref, alt)
    merged = {**vep}
    for k, v in mv.items():
        if v and not merged.get(k):
            merged[k] = v
    return merged


def annotate_batch(variants: list[dict]) -> list[dict]:
    """Annotate a batch. In offline mode this raises on the first call."""
    annotated = []
    for i, v in enumerate(variants):
        try:
            ann = annotate_variant(v["chrom"], v["pos"], v["ref"], v["alt"], v.get("rsid"))
            v.update(ann)
        except OfflineModeError:
            # Re-raise so the caller knows the whole batch is blocked
            raise
        except Exception as e:
            print(f"Annotation failed for variant {i}: {e}")
        annotated.append(v)
        time.sleep(0.1)
    return annotated
