from pydantic import BaseModel
from typing import List, Dict, Any

class UploadedFile(BaseModel):
    filename: str
    file_path: str
    file_size: int

class FileUploadResponse(BaseModel):
    message: str
    files: List[UploadedFile]
    total_files: int
