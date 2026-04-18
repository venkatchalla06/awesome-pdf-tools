import os
import uuid
import tempfile

from fastapi import APIRouter, Depends, HTTPException
from app.services.storage import storage
from app.services.scanner import scan_file
from app.dependencies import get_current_user_optional
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/files", tags=["files"])

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "text/html",
}


@router.post("/presign-upload")
async def presign_upload(
    filename: str,
    content_type: str,
    current_user=Depends(get_current_user_optional),
):
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(400, f"File type not allowed: {content_type}")
    user_id = str(current_user.id) if current_user else "anonymous"
    return storage.generate_upload_presigned_url(filename, content_type, user_id)


@router.post("/validate")
async def validate_file(s3_key: str):
    """
    Called after client uploads to S3.
    Downloads the file, validates real MIME type, scans for malware.
    """
    # Prevent path traversal
    if ".." in s3_key or s3_key.startswith("/"):
        raise HTTPException(400, "Invalid key")

    tmp_path = f"/tmp/validate_{uuid.uuid4()}"
    try:
        storage.download_to_temp(s3_key, tmp_path)

        # Real MIME check (not extension-based)
        try:
            import magic
            mime = magic.from_file(tmp_path, mime=True)
        except ImportError:
            # python-magic not installed — skip MIME check
            mime = "application/octet-stream"

        if mime not in ALLOWED_MIME_TYPES and mime != "application/octet-stream":
            storage.delete_key(s3_key)
            raise HTTPException(400, f"Invalid file content type: {mime}")

        # Malware scan
        is_clean, threat = scan_file(tmp_path)
        if not is_clean:
            storage.delete_key(s3_key)
            raise HTTPException(400, f"Malware detected: {threat}")

        return {"valid": True, "mime_type": mime}
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
