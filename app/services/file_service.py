import os
import uuid
import aiofiles
from fastapi import UploadFile
from app.core.config import settings

UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

class FileService:
    async def save_file(self, upload_file: UploadFile) -> str:
        ext = os.path.splitext(upload_file.filename or "")[-1]
        unique_name = f"{uuid.uuid4()}{ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_name)

        async with aiofiles.open(file_path, "wb") as f:
            content = await upload_file.read()
            await f.write(content)

        return file_path

    async def get_file_path(self, file_id: str) -> str | None:
        # Simple local lookup: file_id is the filename stored at upload time
        file_path = os.path.join(UPLOAD_DIR, file_id)
        return file_path if os.path.exists(file_path) else None
