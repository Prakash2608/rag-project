import httpx
from app.core.config import settings
from app.core.logging import log
from app.core.exceptions import StorageException


# ── Supabase Storage Base URL ─────────────────────────────────────────────────

def _base_url() -> str:
    return f"{settings.SUPABASE_URL}/storage/v1/object"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/octet-stream",
    }


# ── Bucket ────────────────────────────────────────────────────────────────────

def ensure_bucket_exists():
    """
    Checks if the bucket exists in Supabase Storage.
    Bucket is created manually in Supabase dashboard — this just verifies it.
    """
    url = f"{settings.SUPABASE_URL}/storage/v1/bucket/{settings.S3_BUCKET}"
    headers = {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
    }
    try:
        response = httpx.get(url, headers=headers)
        if response.status_code == 200:
            log.info("bucket_exists", bucket=settings.S3_BUCKET)
        else:
            log.warning(
                "bucket_not_found",
                bucket=settings.S3_BUCKET,
                status=response.status_code,
                hint="Create the bucket manually in Supabase Storage dashboard",
            )
    except Exception as e:
        log.error("bucket_check_failed", error=str(e))


# ── Upload ────────────────────────────────────────────────────────────────────

def upload_file(
    file_bytes: bytes,
    s3_key: str,
    content_type: str = "application/pdf",
) -> str:
    """
    Uploads file to Supabase Storage.
    Returns the s3_key so we can store it in DB.
    """
    url = f"{_base_url()}/{settings.S3_BUCKET}/{s3_key}"
    headers = {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
        "Content-Type": content_type,
        "x-upsert": "true",   # overwrite if exists
    }
    try:
        response = httpx.post(url, headers=headers, content=file_bytes)
        response.raise_for_status()
        log.info("file_uploaded", s3_key=s3_key, size_bytes=len(file_bytes))
        return s3_key

    except httpx.HTTPStatusError as e:
        log.error("upload_failed", s3_key=s3_key, error=str(e))
        raise StorageException(f"Failed to upload file: {str(e)}")

    except Exception as e:
        log.error("upload_failed", s3_key=s3_key, error=str(e))
        raise StorageException(f"Failed to upload file: {str(e)}")


# ── Download ──────────────────────────────────────────────────────────────────

def download_file(s3_key: str) -> bytes:
    """Downloads file from Supabase Storage — used by workers to process PDF."""
    url = f"{_base_url()}/{settings.S3_BUCKET}/{s3_key}"
    try:
        response = httpx.get(url, headers=_headers())
        response.raise_for_status()
        file_bytes = response.content
        log.info("file_downloaded", s3_key=s3_key, size_bytes=len(file_bytes))
        return file_bytes

    except httpx.HTTPStatusError as e:
        log.error("download_failed", s3_key=s3_key, error=str(e))
        raise StorageException(f"Failed to download file: {str(e)}")

    except Exception as e:
        log.error("download_failed", s3_key=s3_key, error=str(e))
        raise StorageException(f"Failed to download file: {str(e)}")


# ── Delete ────────────────────────────────────────────────────────────────────

def delete_file(s3_key: str):
    """Deletes file from Supabase Storage."""
    url = f"{_base_url()}/{settings.S3_BUCKET}/{s3_key}"
    try:
        response = httpx.delete(url, headers=_headers())
        response.raise_for_status()
        log.info("file_deleted", s3_key=s3_key)

    except httpx.HTTPStatusError as e:
        log.error("delete_failed", s3_key=s3_key, error=str(e))
        raise StorageException(f"Failed to delete file: {str(e)}")

    except Exception as e:
        log.error("delete_failed", s3_key=s3_key, error=str(e))
        raise StorageException(f"Failed to delete file: {str(e)}")