import boto3
from datetime import datetime, timedelta
import uuid
from app.config import get_settings

settings = get_settings()


def _make_client(endpoint_url: str | None):
    kwargs = dict(
        region_name=settings.S3_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
    if endpoint_url:
        kwargs["endpoint_url"] = endpoint_url
    return boto3.client("s3", **kwargs)


class StorageService:
    def __init__(self):
        # Internal client: used by workers to download/upload files
        self.client = _make_client(settings.S3_ENDPOINT_URL)
        # Public client: used to generate presigned URLs the browser can reach
        public_url = settings.S3_PUBLIC_URL or settings.S3_ENDPOINT_URL
        self._public_client = _make_client(public_url)
        self.bucket = settings.S3_BUCKET

    def generate_upload_presigned_url(self, filename: str, content_type: str, user_id: str) -> dict:
        key = f"uploads/{user_id}/{uuid.uuid4()}/{filename}"
        # Sign with public client so the URL hostname matches what the browser hits
        data = self._public_client.generate_presigned_post(
            self.bucket,
            key,
            Fields={"Content-Type": content_type},
            Conditions=[
                {"Content-Type": content_type},
                ["content-length-range", 1, settings.MAX_FILE_SIZE_MB * 1024 * 1024],
            ],
            ExpiresIn=3600,
        )
        return {"url": data["url"], "fields": data["fields"], "key": key}

    def generate_download_url(self, key: str, filename: str, ttl_seconds: int = 300) -> str:
        # Download URLs also go to the public client so browsers can fetch them
        return self._public_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket,
                "Key": key,
                "ResponseContentDisposition": f'attachment; filename="{filename}"',
            },
            ExpiresIn=ttl_seconds,
        )

    def download_to_temp(self, key: str, local_path: str) -> None:
        self.client.download_file(self.bucket, key, local_path)

    def upload_from_temp(self, local_path: str, key: str, content_type: str = "application/pdf") -> str:
        self.client.upload_file(
            local_path,
            self.bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )
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


storage = StorageService()
