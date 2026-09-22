from fastapi import APIRouter, UploadFile, File, Depends, BackgroundTasks, HTTPException
from app.supabase_client import supabase
from app.db import sb_select, sb_insert, sb_update
from app.deps import get_current_user
from app.services.audit import log_action
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

    storage_path = f"{user.id}/{sample_id}{ext}"
    contents = await file.read()

    try:
        supabase.storage.from_("genomic-files").upload(
            storage_path, contents, {"content-type": "application/octet-stream"}
        )
    except Exception as e:
        raise HTTPException(500, f"Storage upload failed: {e}")

    sb_insert("samples", {
        "id": sample_id,
        "project_id": project_id,
        "name": filename,
        "file_path": storage_path,
        "file_type": file_type,
        "file_size_bytes": len(contents),
        "status": "processing",
        "created_by": user.id,
    })

    log_action(user.id, "upload", "sample", sample_id, {"filename": filename})

    if file_type == "vcf" and not filename.endswith(".gz"):
        background.add_task(_process_vcf, sample_id, storage_path)

    return {"sample_id": sample_id, "status": "processing"}


def _process_vcf(sample_id: str, storage_path: str):
    tmp_path = None
    try:
        data = supabase.storage.from_("genomic-files").download(storage_path)
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
