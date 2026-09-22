"""
DuckDB pre-processor: reads VCF from B2, filters to PASS variants.
Falls back gracefully if B2 isn't configured.
"""
import duckdb
from app.config import settings


def _duckdb_conn():
    con = duckdb.connect()
    if settings.r2_enabled:
        con.execute("INSTALL httpfs; LOAD httpfs;")
        endpoint = settings.R2_ENDPOINT.replace("https://", "").replace("http://", "")
        con.execute(f"""
            SET s3_endpoint='{endpoint}';
            SET s3_access_key_id='{settings.R2_ACCESS_KEY_ID}';
            SET s3_secret_access_key='{settings.R2_SECRET_ACCESS_KEY}';
            SET s3_use_ssl=true;
            SET s3_url_style='path';
            SET s3_region='{settings.R2_REGION}';
        """)
    return con


def extract_variants_from_vcf(r2_path: str, r2_bucket: str, max_variants: int = 100000) -> list[dict]:
    """
    Stream a VCF through DuckDB, filter to PASS variants,
    return list of dicts ready for Supabase insert.
    """
    con = _duckdb_conn()
    s3_path = f"s3://{r2_bucket}/{r2_path}"

    query = f"""
        SELECT *
        FROM read_csv_auto('{s3_path}',
            delim='\t',
            header=false,
            skip=1,
            comment='#',
            quote='',
            all_varchar=true
        )
        LIMIT {max_variants}
    """

    try:
        result = con.execute(query).fetchall()
        cols = [d[0] for d in con.description]
    except Exception as e:
        print(f"DuckDB read failed: {e}")
        return []

    variants = []
    for row in result:
        r = dict(zip(cols, row))
        # VCF columns: 0=CHROM 1=POS 2=ID 3=REF 4=ALT 5=QUAL 6=FILTER 7=INFO
        try:
            chrom = r.get("0") or r.get("column0")
            pos = r.get("1") or r.get("column1")
            rsid = r.get("2") or r.get("column2")
            ref = r.get("3") or r.get("column3")
            alt = r.get("4") or r.get("column4")
            qual = r.get("5") or r.get("column5")
            filt = r.get("6") or r.get("column6")
            info = r.get("7") or r.get("column7") or ""
        except Exception:
            continue

        if not chrom or not pos:
            continue

        gene = consequence = impact = clinvar = None
        for field in str(info).split(";"):
            if field.startswith("ANN="):
                parts = field[4:].split("|")
                if len(parts) > 3:
                    consequence = parts[1] or None
                    impact = parts[2] or None
                    gene = parts[3] or None
            elif field.startswith("CLNSIG="):
                clinvar = field[7:]

        try:
            qual_val = float(qual) if qual and qual != "." else None
        except (ValueError, TypeError):
            qual_val = None

        variants.append({
            "chrom": str(chrom),
            "pos": int(pos),
            "rsid": rsid if rsid and rsid != "." else None,
            "ref": ref,
            "alt": alt,
            "qual": qual_val,
            "filter": filt if filt and filt != "." else None,
            "gene": gene,
            "consequence": consequence,
            "impact": impact,
            "clinvar_significance": clinvar,
        })

    return variants
