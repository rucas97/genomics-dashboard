from fastapi import APIRouter, UploadFile, File, Depends, BackgroundTasks, HTTPException
from app.supabase_client import supabase
from app.db import sb_select, sb_insert, sb_update
from app.deps import get_current_user
from app.services.audit import log_action
from app.services.storage import upload_file, download_file
from app.services.preprocess import extract_variants_from_vcf
from app.services.vcf_parser import parse_and_store_vcf
from app.services.qc_calc import compute_qc_from_variants
import uuid, tempfile, os, gzip, shutil

router = APIRouter(prefix="/samples", tags=["samples"])


@router.get("/")
async def list_samples(user=Depends(get_current_user)):
    resp = sb_select("samples", order="created_at", desc=True)
    return resp.data


def _detect_file_type(filename: str) -> str:
    """Detect type from name, handling .gz compression."""
    name = filename.lower()
    if name.endswith(".gz"):
        name = name[:-3]
    if name.endswith(".vcf"):
        return "vcf"
    if name.endswith(".fastq") or name.endswith(".fq"):
        return "fastq"
    if name.endswith(".bam"):
        return "bam"
    if name.endswith(".csv"):
        return "csv"
    return "unknown"


@router.post("/upload")
async def upload_sample(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    project_id: str = None,
    user=Depends(get_current_user),
):
    sample_id = str(uuid.uuid4())
    filename = file.filename or "upload"
    file_type = _detect_file_type(filename)

    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)

    provider, storage_path = upload_file(user.id, sample_id, filename, contents)

    sb_insert("samples", {
        "id": sample_id,
        "project_id": project_id,
        "name": filename,
        "file_path": storage_path,
        "file_type": file_type,
        "file_size_bytes": len(contents),
        "status": "processing",
        "metadata": {"storage_provider": provider, "size_mb": round(size_mb, 2)},
        "created_by": user.id,
    })

    log_action(user.id, "upload", "sample", sample_id, {
        "filename": filename,
        "size_mb": round(size_mb, 2),
        "provider": provider,
    })

    if file_type == "vcf":
        background.add_task(_process_vcf, sample_id, provider, storage_path)

    return {"sample_id": sample_id, "status": "processing", "provider": provider}


def _process_vcf(sample_id: str, provider: str, storage_path: str):
    tmp_path = None
    tmp_uncompressed = None
    try:
        data = download_file(provider, storage_path)
        is_gz = storage_path.lower().endswith(".gz")

        # Decompress if needed
        if is_gz:
            with tempfile.NamedTemporaryFile(suffix=".vcf.gz", delete=False) as f:
                f.write(data)
                tmp_path = f.name
            tmp_uncompressed = tmp_path[:-3]  # strip .gz
            with gzip.open(tmp_path, "rb") as fin, open(tmp_uncompressed, "wb") as fout:
                shutil.copyfileobj(fin, fout)
            plain_path = tmp_uncompressed
            plain_size = os.path.getsize(plain_path)
        else:
            with tempfile.NamedTemporaryFile(suffix=".vcf", delete=False) as f:
                f.write(data)
                tmp_path = f.name
            plain_path = tmp_path
            plain_size = len(data)

        size_mb = plain_size / (1024 * 1024)

        # Large files → DuckDB on local uncompressed file
        if size_mb > 10:
            print(f"Large VCF detected ({size_mb:.1f} MB) — using DuckDB")
            variants = _extract_with_duckdb_local(plain_path)
            if not variants:
                raise Exception("DuckDB returned 0 variants")
            _insert_variants(sample_id, variants)
        else:
            parse_and_store_vcf(sample_id, plain_path)

        compute_qc_from_variants(sample_id)
        sb_update("samples", {"status": "ready"}, {"id": sample_id})
        print(f"Sample {sample_id} processed successfully")

    except Exception as e:
        print(f"VCF processing failed for {sample_id}: {e}")
        try:
            sb_update("samples", {"status": "failed"}, {"id": sample_id})
        except Exception:
            pass
    finally:
        for p in (tmp_path, tmp_uncompressed):
            if p and os.path.exists(p):
                try:
                    os.unlink(p)
                except Exception:
                    pass


def _extract_with_duckdb_local(vcf_path: str) -> list[dict]:
    """Parse VCF with DuckDB from a local file. Fast for large files."""
    import duckdb
    con = duckdb.connect()

    # DuckDB reads VCF as TSV; comment lines start with #
    # Use header=false, skip comment lines, all columns as varchar
    query = f"""
        SELECT * FROM read_csv(
            '{vcf_path.replace(chr(92), "/")}',
            delim='\t',
            header=false,
            skip=0,
            quote='',
            escape='',
            all_varchar=true,
            ignore_errors=true
        )
        WHERE column0 NOT LIKE '#%'
        LIMIT 100000
    """

    try:
        result = con.execute(query).fetchall()
    except Exception as e:
        print(f"DuckDB query failed: {e}")
        # Fallback: read line-by-line
        return _parse_vcf_plain(vcf_path)

    variants = []
    for row in result:
        if len(row) < 8:
            continue
        try:
            chrom = str(row[0])
            pos = int(row[1])
            rsid = row[2] if row[2] and row[2] != "." else None
            ref = row[3]
            alt = row[4]
            qual_raw = row[5]
            filt = row[6] if row[6] and row[6] != "." else None
            info = row[7] or ""
        except (ValueError, IndexError):
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
            qual_val = float(qual_raw) if qual_raw and qual_raw != "." else None
        except (ValueError, TypeError):
            qual_val = None

        variants.append({
            "chrom": chrom,
            "pos": pos,
            "rsid": rsid,
            "ref": ref,
            "alt": alt,
            "qual": qual_val,
            "filter": filt,
            "gene": gene,
            "consequence": consequence,
            "impact": impact,
            "clinvar_significance": clinvar,
        })

    return variants


def _parse_vcf_plain(path: str) -> list[dict]:
    """Plain Python VCF parser, used as fallback."""
    variants = []
    count = 0
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 8:
                continue
            try:
                variants.append({
                    "chrom": parts[0],
                    "pos": int(parts[1]),
                    "rsid": parts[2] if parts[2] != "." else None,
                    "ref": parts[3],
                    "alt": parts[4],
                    "qual": float(parts[5]) if parts[5] not in (".", "") else None,
                    "filter": parts[6] if parts[6] != "." else None,
                    "gene": None,
                    "consequence": None,
                    "impact": None,
                    "clinvar_significance": None,
                })
                count += 1
                if count >= 100000:
                    break
            except (ValueError, IndexError):
                continue
    return variants


def _insert_variants(sample_id: str, variants: list[dict]):
    batch = []
    for v in variants:
        v["sample_id"] = sample_id
        batch.append(v)
        if len(batch) >= 1000:
            try:
                sb_insert("variants", batch)
            except Exception as e:
                print(f"Batch insert failed: {e}")
            batch = []
    if batch:
        try:
            sb_insert("variants", batch)
        except Exception as e:
            print(f"Final batch insert failed: {e}")


@router.get("/{sample_id}")
async def get_sample(sample_id: str, user=Depends(get_current_user)):
    sample = sb_select("samples", filters={"id": sample_id})
    if not sample.data:
        raise HTTPException(404, "Sample not found")
    qc = sb_select("qc_metrics", filters={"sample_id": sample_id})
    log_action(user.id, "view", "sample", sample_id)
    return {"sample": sample.data[0], "qc": qc.data}


@router.delete("/{sample_id}")
async def delete_sample(sample_id: str, user=Depends(get_current_user)):
    from app.db import sb_delete
    sb_delete("samples", {"id": sample_id})
    log_action(user.id, "delete", "sample", sample_id)
    return {"ok": True}
