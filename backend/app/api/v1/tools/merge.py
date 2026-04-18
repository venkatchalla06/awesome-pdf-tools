from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid
from datetime import datetime, timedelta

from app.db.session import get_db
from app.db.models.job import Job, JobStatus, ToolType
from app.dependencies import get_current_user_optional
from app.config import get_settings
from app.schemas.job import JobResponse

settings = get_settings()
router = APIRouter(prefix="/tools", tags=["tools"])


class MergeRequest(BaseModel):
    input_keys: List[str]
    output_filename: str = "merged.pdf"


@router.post("/merge", response_model=JobResponse, status_code=202)
async def merge_pdfs(
    body: MergeRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    if len(body.input_keys) < 2:
        raise HTTPException(400, "At least 2 files required")
    if len(body.input_keys) > 20:
        raise HTTPException(400, "Maximum 20 files per merge")

    job = Job(
        id=uuid.uuid4(),
        user_id=current_user.id if current_user else None,
        tool=ToolType.MERGE,
        status=JobStatus.PENDING,
        input_keys=body.input_keys,
        options={"output_filename": body.output_filename},
        expires_at=datetime.utcnow() + timedelta(hours=settings.TEMP_FILE_TTL_HOURS),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    from app.workers.tasks.merge import merge_task
    merge_task.apply_async(args=[str(job.id)], task_id=str(job.id))

    return job
