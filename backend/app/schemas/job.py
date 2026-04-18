from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from app.db.models.job import JobStatus, ToolType


class JobResponse(BaseModel):
    id: UUID
    tool: ToolType
    status: JobStatus
    progress: int
    error_message: str | None = None
    created_at: datetime
    expires_at: datetime | None = None

    class Config:
        from_attributes = True


class JobStatusResponse(JobResponse):
    output_key: str | None = None
    options: dict = {}
