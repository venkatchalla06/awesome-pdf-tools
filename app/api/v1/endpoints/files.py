from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import List
import os
from app.core.config import settings
from app.services.file_service import FileService
from app.schemas.file import FileUploadResponse

router = APIRouter()
file_service = FileService()

@router.post("/upload", response_model=FileUploadResponse)
async def upload_files(files: List[UploadFile] = File(...)):
    """Upload multiple files for processing"""
    if len(files) > settings.MAX_FILES_PER_REQUEST:
        raise HTTPException(
            status_code=400, 
            detail=f"Maximum {settings.MAX_FILES_PER_REQUEST} files allowed per request"
        )
    
    uploaded_files = []
    
    for file in files:
        # Validate file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        
        if file_size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File {file.filename} exceeds maximum size of {settings.MAX_FILE_SIZE} bytes"
            )
        
        # Save file
        file_path = await file_service.save_file(file)
        
        uploaded_files.append({
            "filename": file.filename,
            "file_path": file_path,
            "file_size": file_size
        })
    
    return {
        "message": "Files uploaded successfully",
        "files": uploaded_files,
        "total_files": len(uploaded_files)
    }

@router.get("/{file_id}/download")
async def download_file(file_id: str):
    """Download processed file"""
    file_path = await file_service.get_file_path(file_id)
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return {
        "download_url": f"/api/v1/files/{file_id}/content",
        "expires_in": 3600  # 1 hour
    }

@router.get("/{file_id}/content")
async def get_file_content(file_id: str):
    """Serve file content"""
    file_path = await file_service.get_file_path(file_id)
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    filename = os.path.basename(file_path)
    
    from fastapi.responses import FileResponse
    return FileResponse(
        file_path,
        filename=filename,
        media_type="application/pdf"
    )