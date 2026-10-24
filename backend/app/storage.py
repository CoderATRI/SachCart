import boto3
from botocore.client import Config
import httpx
from app.config import settings

def get_s3_client():
    endpoint = (
        settings.MINIO_PUBLIC_URL
        if settings.MINIO_PUBLIC_URL.startswith("http")
        else f"http://{settings.MINIO_ENDPOINT}"
    )
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )

def ensure_bucket():
    s3 = get_s3_client()
    try:
        buckets = [b["Name"] for b in s3.list_buckets().get("Buckets", [])]
        if settings.MINIO_BUCKET not in buckets:
            s3.create_bucket(Bucket=settings.MINIO_BUCKET)
    except Exception:
        pass

async def store_evidence_from_url(source_url: str, object_key: str) -> str:
    ensure_bucket()
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(source_url)
        resp.raise_for_status()
        content = resp.content
        content_type = resp.headers.get("content-type", "application/octet-stream")

    s3 = get_s3_client()
    s3.put_object(
        Bucket=settings.MINIO_BUCKET,
        Key=object_key,
        Body=content,
        ContentType=content_type,
    )
    return object_key

def generate_presigned_url(object_key: str, expires_in: int = 600) -> str:
    s3 = get_s3_client()
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.MINIO_BUCKET, "Key": object_key},
        ExpiresIn=expires_in,
    )
