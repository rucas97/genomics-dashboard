"""
Storage routing: Backblaze B2 (S3-compatible) for large files,
Supabase Storage as fallback if B2 isn't configured.
"""
import boto3
from botocore.config import Config
from app.config import settings
from app.supabase_client import supabase


_r2_client = None


def _get_r2():
    global _r2_client
    if _r2_client is None and settings.r2_enabled:
        _r2_client = boto3.client(
            "s3",
            endpoint_url=settings.R2_ENDPOINT,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4"),
            region_name=settings.R2_REGION,
        )
    return _r2_client


def upload_file(user_id: str, sample_id: str, filename: str, contents: bytes) -> tuple[str, str]:
    """
    Upload to B2 if configured, else Supabase Storage.
    Returns (storage_provider, storage_path).
    """
    path = f"{user_id}/{sample_id}/{filename}"

    if settings.r2_enabled:
        client = _get_r2()
        client.put_object(
            Bucket=settings.R2_BUCKET,
            Key=path,
            Body=contents,
            ContentType="application/octet-stream",
        )
        return "b2", path

    supabase.storage.from_("genomic-files").upload(
        path, contents, {"content-type": "application/octet-stream"}
    )
    return "supabase", path


def download_file(provider: str, path: str) -> bytes:
    """Download from whichever provider holds the file."""
    if provider == "b2" and settings.r2_enabled:
        client = _get_r2()
        resp = client.get_object(Bucket=settings.R2_BUCKET, Key=path)
        return resp["Body"].read()

    return supabase.storage.from_("genomic-files").download(path)


def delete_file(provider: str, path: str):
    if provider == "b2" and settings.r2_enabled:
        client = _get_r2()
        client.delete_object(Bucket=settings.R2_BUCKET, Key=path)
        return
    supabase.storage.from_("genomic-files").remove([path])


def signed_url(provider: str, path: str, expires: int = 3600) -> str:
    if provider == "b2" and settings.r2_enabled:
        client = _get_r2()
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.R2_BUCKET, "Key": path},
            ExpiresIn=expires,
        )
    signed = supabase.storage.from_("genomic-files").create_signed_url(path, expires)
    return signed.get("signedURL") or signed.get("signed_url")
