from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.db.session import get_db
from app.db.models.job import Job, JobStatus
from app.services.storage import storage
from app.schemas.job import JobStatusResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.get("/{job_id}/download-url")
async def get_download_url(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(400, f"Job not completed: {job.status}")
    if not job.output_key:
        raise HTTPException(500, "Output file missing")

    filename = job.options.get("output_filename", "result.pdf")
    url = storage.generate_download_url(job.output_key, filename, ttl_seconds=300)
    return {"download_url": url, "expires_in": 300}
