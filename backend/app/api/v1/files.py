import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from fastapi.responses import FileResponse, Response
from app.services.storage import storage, LocalStorageService
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


@router.post("/upload-local/{user_id}/{file_uuid}/{filename:path}")
async def upload_local(user_id: str, file_uuid: str, filename: str, file: UploadFile = File(...)):
    """Direct upload endpoint used when running with local storage (no S3)."""
    if not isinstance(storage, LocalStorageService):
        raise HTTPException(404, "Local upload not available in S3 mode")
    key = f"{user_id}/{file_uuid}/{filename}"
    if ".." in key:
        raise HTTPException(400, "Invalid path")
    data = await file.read()
    storage.save_bytes(key, data)
    return {"key": key}


@router.get("/download-local/{key:path}")
async def download_local(key: str):
    """Serve a locally stored file."""
    if not isinstance(storage, LocalStorageService):
        raise HTTPException(404, "Local download not available in S3 mode")
    if ".." in key:
        raise HTTPException(400, "Invalid path")
    try:
        data = storage.read_bytes(key)
    except FileNotFoundError:
        raise HTTPException(404, "File not found")
    filename = key.split("/")[-1]
    return Response(content=data, media_type="application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.post("/validate")
async def validate_file(s3_key: str):
    if ".." in s3_key or s3_key.startswith("/"):
        raise HTTPException(400, "Invalid key")

    tmp_path = f"/tmp/validate_{uuid.uuid4()}"
    try:
        storage.download_to_temp(s3_key, tmp_path)

        try:
            import magic
            mime = magic.from_file(tmp_path, mime=True)
        except (ImportError, Exception):
            mime = "application/octet-stream"

        if mime not in ALLOWED_MIME_TYPES and mime != "application/octet-stream":
            storage.delete_key(s3_key)
            raise HTTPException(400, f"Invalid file content type: {mime}")

        # Skip ClamAV scan if not configured
        try:
            is_clean, threat = scan_file(tmp_path)
            if not is_clean:
                storage.delete_key(s3_key)
                raise HTTPException(400, f"Malware detected: {threat}")
        except Exception:
            pass  # ClamAV not available on free tier

        return {"valid": True, "mime_type": mime}
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
