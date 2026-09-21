import vcfpy
from app.supabase_client import supabase

def parse_and_store_vcf(sample_id: str, file_path: str, max_variants: int = 100000):
    reader = vcfpy.Reader.from_path(file_path)
    batch = []
    count = 0

    for rec in reader:
        gene = consequence = impact = clinvar = None

        ann = rec.INFO.get("ANN")
        if ann and isinstance(ann, list) and len(ann) > 0:
            parts = str(ann[0]).split("|")
            if len(parts) > 3:
                consequence = parts[1] or None
                impact = parts[2] or None
                gene = parts[3] or None

        clnsig = rec.INFO.get("CLNSIG")
        if clnsig:
            clinvar = str(clnsig[0]) if isinstance(clnsig, list) else str(clnsig)

        gnomad = rec.INFO.get("gnomAD_AF") or rec.INFO.get("AF")
        if isinstance(gnomad, list):
            gnomad = gnomad[0]

        rsid = rec.ID if rec.ID and rec.ID != "." else None

        try:
            gnomad_val = float(gnomad) if gnomad is not None else None
        except (ValueError, TypeError):
            gnomad_val = None

        try:
            qual_val = float(rec.QUAL) if rec.QUAL is not None else None
        except (ValueError, TypeError):
            qual_val = None

        batch.append({
            "sample_id": sample_id,
            "chrom": str(rec.CHROM),
            "pos": int(rec.POS),
            "ref": rec.REF,
            "alt": ",".join(str(a.value) for a in rec.ALT) if rec.ALT else None,
            "qual": qual_val,
            "filter": ",".join(rec.FILTER) if rec.FILTER else None,
            "gene": gene,
            "consequence": consequence,
            "impact": impact,
            "clinvar_significance": clinvar,
            "gnomad_af": gnomad_val,
            "rsid": rsid,
        })

        if len(batch) >= 1000:
            supabase.table("variants").insert(batch).execute()
            batch = []

        count += 1
        if count >= max_variants:
            break

    if batch:
        supabase.table("variants").insert(batch).execute()

    return count
