"""
Pure-Python VCF parser. No external dependencies.
Handles uncompressed .vcf only (gzip handled upstream in samples.py).
"""
from app.db import get_db


def _parse_info(info_str: str) -> dict:
    """Parse the INFO column into a dict."""
    result = {}
    if not info_str or info_str == ".":
        return result
    for field in info_str.split(";"):
        if "=" in field:
            key, _, value = field.partition("=")
            result[key] = value
        else:
            result[field] = True
    return result


def _extract_from_ann(ann: str):
    """ANN format: Allele|Consequence|IMPACT|SYMBOL|Gene|Feature|..."""
    if not ann:
        return None, None, None
    # Take the first annotation
    first = ann.split(",")[0]
    parts = first.split("|")
    if len(parts) < 4:
        return None, None, None
    consequence = parts[1] or None
    impact = parts[2] or None
    gene = parts[3] or None
    return gene, consequence, impact


def parse_and_store_vcf(sample_id: str, file_path: str, max_variants: int = 100000) -> int:
    """Read a VCF file line by line and insert variants into the DB."""
    db = get_db()
    batch = []
    count = 0

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.startswith("#"):
                continue

            parts = line.rstrip("\n").split("\t")
            if len(parts) < 8:
                continue

            try:
                chrom = parts[0]
                pos = int(parts[1])
                rsid = parts[2] if parts[2] != "." else None
                ref = parts[3]
                alt = parts[4]
                qual_str = parts[5]
                filter_val = parts[6] if parts[6] != "." else None
                info_str = parts[7]
            except (ValueError, IndexError):
                continue

            try:
                qual = float(qual_str) if qual_str not in (".", "") else None
            except ValueError:
                qual = None

            info = _parse_info(info_str)

            gene = consequence = impact = None
            ann = info.get("ANN")
            if ann:
                gene, consequence, impact = _extract_from_ann(ann)

            clinvar = info.get("CLNSIG") or None
            if isinstance(clinvar, str) and "|" in clinvar:
                clinvar = clinvar.split("|")[0]

            gnomad_af = None
            for key in ("gnomAD_AF", "AF", "CAF"):
                if key in info and info[key] not in (".", True):
                    try:
                        gnomad_af = float(str(info[key]).split(",")[0])
                        break
                    except (ValueError, TypeError):
                        pass

            batch.append({
                "sample_id": sample_id,
                "chrom": chrom,
                "pos": pos,
                "rsid": rsid,
                "ref": ref,
                "alt": alt,
                "qual": qual,
                "filter": filter_val,
                "gene": gene,
                "consequence": consequence,
                "impact": impact,
                "clinvar_significance": clinvar,
                "gnomad_af": gnomad_af,
            })

            if len(batch) >= 1000:
                db.insert_variants(batch)
                batch = []

            count += 1
            if count >= max_variants:
                break

    if batch:
        db.insert_variants(batch)

    return count
