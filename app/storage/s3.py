import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from app.core.config import settings
from app.core.logging import log
from app.core.exceptions import StorageException


def get_s3_client():
    """Returns a MinIO/S3 client"""
    return boto3.client(
        "s3",
        endpoint_url          = settings.S3_ENDPOINT,
        aws_access_key_id     = settings.S3_ACCESS_KEY,
        aws_secret_access_key = settings.S3_SECRET_KEY,
        config                = Config(signature_version="s3v4"),
        region_name           = "us-east-1",
    )


def ensure_bucket_exists():
    """Creates the bucket if it doesn't exist — called at startup"""
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=settings.S3_BUCKET)
        log.info("bucket_exists", bucket=settings.S3_BUCKET)
    except ClientError:
        client.create_bucket(Bucket=settings.S3_BUCKET)
        log.info("bucket_created", bucket=settings.S3_BUCKET)


def upload_file(file_bytes: bytes, s3_key: str, content_type: str = "application/pdf") -> str:
    """
    Uploads file to MinIO.
    Returns the s3_key so we can store it in DB.
    """
    client = get_s3_client()
    try:
        client.put_object(
            Bucket      = settings.S3_BUCKET,
            Key         = s3_key,
            Body        = file_bytes,
            ContentType = content_type,
        )
        log.info("file_uploaded", s3_key=s3_key, size_bytes=len(file_bytes))
        return s3_key

    except ClientError as e:
        log.error("upload_failed", s3_key=s3_key, error=str(e))
        raise StorageException(f"Failed to upload file: {str(e)}")


def download_file(s3_key: str) -> bytes:
    """Downloads file from MinIO — used by workers to process PDF"""
    client = get_s3_client()
    try:
        response = client.get_object(Bucket=settings.S3_BUCKET, Key=s3_key)
        file_bytes = response["Body"].read()
        log.info("file_downloaded", s3_key=s3_key, size_bytes=len(file_bytes))
        return file_bytes

    except ClientError as e:
        log.error("download_failed", s3_key=s3_key, error=str(e))
        raise StorageException(f"Failed to download file: {str(e)}")


def delete_file(s3_key: str):
    """Deletes file from MinIO"""
    client = get_s3_client()
    try:
        client.delete_object(Bucket=settings.S3_BUCKET, Key=s3_key)
        log.info("file_deleted", s3_key=s3_key)

    except ClientError as e:
        log.error("delete_failed", s3_key=s3_key, error=str(e))
        raise StorageException(f"Failed to delete file: {str(e)}")