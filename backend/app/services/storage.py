"""MinIO (S3-compatible) helpers."""
import io
from minio import Minio
from minio.error import S3Error

from ..config import settings

_client: Minio | None = None


def get_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=False,
        )
    return _client


def ensure_bucket() -> None:
    client = get_client()
    try:
        if not client.bucket_exists(settings.MINIO_BUCKET):
            client.make_bucket(settings.MINIO_BUCKET)
    except S3Error:
        pass


def upload_file(object_key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    ensure_bucket()
    get_client().put_object(
        settings.MINIO_BUCKET,
        object_key,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )


def download_file(object_key: str) -> bytes:
    response = get_client().get_object(settings.MINIO_BUCKET, object_key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()
