from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class JobCreate(BaseModel):
    file_id: int
    job_type: str
    parameters: Optional[Dict[str, Any]] = None

class JobResponse(BaseModel):
    id: int
    file_id: int
    job_type: str
    status: str
    result_path: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
