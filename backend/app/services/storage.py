import os
import uuid
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from app.config import get_settings

settings = get_settings()

LOCAL_UPLOAD_DIR = Path(os.getenv("LOCAL_UPLOAD_DIR", "/tmp/pdfkit/uploads"))


class LocalStorageService:
    """File storage backed by local /tmp — no S3/MinIO required."""

    def __init__(self):
        LOCAL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self._api_base = os.getenv("API_BASE_URL", "http://localhost:8000")

    def _key_to_path(self, key: str) -> Path:
        safe = key.lstrip("/").replace("..", "")
        return LOCAL_UPLOAD_DIR / safe

    def generate_upload_presigned_url(self, filename: str, content_type: str, user_id: str) -> dict:
        key = f"{user_id}/{uuid.uuid4()}/{filename}"
        upload_url = f"{self._api_base}/api/v1/files/upload-local/{key}"
        return {"url": upload_url, "fields": {}, "key": key}

    def generate_download_url(self, key: str, filename: str, ttl_seconds: int = 300) -> str:
        return f"{self._api_base}/api/v1/files/download-local/{key}"

    def download_to_temp(self, key: str, local_path: str) -> None:
        src = self._key_to_path(key)
        if not src.exists():
            raise FileNotFoundError(f"File not found: {key}")
        shutil.copy2(src, local_path)

    def upload_from_temp(self, local_path: str, key: str, content_type: str = "application/pdf") -> str:
        dest = self._key_to_path(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_path, dest)
        return key

    def save_bytes(self, key: str, data: bytes) -> None:
        dest = self._key_to_path(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)

    def read_bytes(self, key: str) -> bytes:
        return self._key_to_path(key).read_bytes()

    def delete_key(self, key: str) -> None:
        path = self._key_to_path(key)
        if path.exists():
            path.unlink()

    def delete_expired_files(self) -> int:
        cutoff = datetime.utcnow() - timedelta(hours=settings.TEMP_FILE_TTL_HOURS)
        deleted = 0
        for f in LOCAL_UPLOAD_DIR.rglob("*"):
            if f.is_file():
                mtime = datetime.utcfromtimestamp(f.stat().st_mtime)
                if mtime < cutoff:
                    f.unlink()
                    deleted += 1
        return deleted


class S3StorageService:
    """Original S3/MinIO backed storage."""

    def __init__(self):
        import boto3
        self._boto3 = boto3

        def _make_client(endpoint_url):
            kwargs = dict(
                region_name=settings.S3_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
            if endpoint_url:
                kwargs["endpoint_url"] = endpoint_url
            return boto3.client("s3", **kwargs)

        self.client = _make_client(settings.S3_ENDPOINT_URL)
        public_url = settings.S3_PUBLIC_URL or settings.S3_ENDPOINT_URL
        self._public_client = _make_client(public_url)
        self.bucket = settings.S3_BUCKET

    def generate_upload_presigned_url(self, filename: str, content_type: str, user_id: str) -> dict:
        key = f"uploads/{user_id}/{uuid.uuid4()}/{filename}"
        data = self._public_client.generate_presigned_post(
            self.bucket, key,
            Fields={"Content-Type": content_type},
            Conditions=[
                {"Content-Type": content_type},
                ["content-length-range", 1, settings.MAX_FILE_SIZE_MB * 1024 * 1024],
            ],
            ExpiresIn=3600,
        )
        return {"url": data["url"], "fields": data["fields"], "key": key}

    def generate_download_url(self, key: str, filename: str, ttl_seconds: int = 300) -> str:
        return self._public_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket, "Key": key,
                "ResponseContentDisposition": f'attachment; filename="{filename}"',
            },
            ExpiresIn=ttl_seconds,
        )

    def download_to_temp(self, key: str, local_path: str) -> None:
        self.client.download_file(self.bucket, key, local_path)

    def upload_from_temp(self, local_path: str, key: str, content_type: str = "application/pdf") -> str:
        self.client.upload_file(local_path, self.bucket, key, ExtraArgs={"ContentType": content_type})
        return key

    def delete_key(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def delete_expired_files(self) -> int:
        paginator = self.client.get_paginator("list_objects_v2")
        cutoff = datetime.utcnow() - timedelta(hours=settings.TEMP_FILE_TTL_HOURS)
        deleted = 0
        for page in paginator.paginate(Bucket=self.bucket, Prefix="uploads/"):
            for obj in page.get("Contents", []):
                if obj["LastModified"].replace(tzinfo=None) < cutoff:
                    self.client.delete_object(Bucket=self.bucket, Key=obj["Key"])
                    deleted += 1
        return deleted


# Use local storage when S3_ENDPOINT_URL is not configured
_use_local = not settings.S3_ENDPOINT_URL or os.getenv("STORAGE_MODE", "") == "local"
storage: LocalStorageService | S3StorageService = LocalStorageService() if _use_local else S3StorageService()
