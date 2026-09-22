from fastapi import APIRouter, UploadFile, File, Depends, BackgroundTasks, HTTPException
from app.supabase_client import supabase
from app.db import sb_select, sb_insert, sb_update
from app.deps import get_current_user
from app.services.audit import log_action
from app.services.storage import upload_file, download_file
from app.services.preprocess import extract_variants_from_vcf
from app.services.vcf_parser import parse_and_store_vcf
from app.services.qc_calc import compute_qc_from_variants
import uuid, tempfile, os

router = APIRouter(prefix="/samples", tags=["samples"])


@router.get("/")
async def list_samples(user=Depends(get_current_user)):
    resp = sb_select("samples", order="created_at", desc=True)
    return resp.data


@router.post("/upload")
async def upload_sample(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    project_id: str = None,
    user=Depends(get_current_user),
):
    sample_id = str(uuid.uuid4())
    filename = file.filename or "upload"
    ext = os.path.splitext(filename)[1].lower()
    file_type = {
        ".vcf": "vcf", ".gz": "vcf", ".fastq": "fastq",
        ".fq": "fastq", ".bam": "bam", ".csv": "csv",
    }.get(ext, "unknown")

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

    if file_type == "vcf" and not filename.endswith(".gz"):
        background.add_task(_process_vcf, sample_id, provider, storage_path)

    return {"sample_id": sample_id, "status": "processing", "provider": provider}


def _process_vcf(sample_id: str, provider: str, storage_path: str):
    tmp_path = None
    try:
        data = download_file(provider, storage_path)

        # Large files + B2 → use DuckDB (fast, C++)
        if len(data) > 10 * 1024 * 1024 and provider == "b2":
            from app.config import settings
            variants = extract_variants_from_vcf(storage_path, settings.R2_BUCKET)
            if not variants:
                raise Exception("DuckDB returned 0 variants")
            _insert_variants(sample_id, variants)
        else:
            # Small files → existing vcfpy parser
            with tempfile.NamedTemporaryFile(suffix=".vcf", delete=False) as f:
                f.write(data)
                tmp_path = f.name
            parse_and_store_vcf(sample_id, tmp_path)

        compute_qc_from_variants(sample_id)
        sb_update("samples", {"status": "ready"}, {"id": sample_id})

    except Exception as e:
        print(f"VCF processing failed for {sample_id}: {e}")
        try:
            sb_update("samples", {"status": "failed"}, {"id": sample_id})
        except Exception:
            pass
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _insert_variants(sample_id: str, variants: list[dict]):
    batch = []
    for v in variants:
        v["sample_id"] = sample_id
        batch.append(v)
        if len(batch) >= 1000:
            sb_insert("variants", batch)
            batch = []
    if batch:
        sb_insert("variants", batch)


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
