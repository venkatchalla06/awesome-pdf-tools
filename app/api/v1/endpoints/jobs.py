from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any
from app.schemas.job import JobCreate, JobResponse
from app.services.job_service import JobService

router = APIRouter()
job_service = JobService()

@router.post("/", response_model=JobResponse)
async def create_job(job_data: JobCreate, background_tasks: BackgroundTasks):
    """Create a new PDF processing job"""
    job = await job_service.create_job(job_data)
    
    # Start processing in background
    background_tasks.add_task(job_service.process_job, job.id)
    
    return JobResponse.from_orm(job)

@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: int):
    """Get job status"""
    job = await job_service.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobResponse.from_orm(job)

@router.get("/{job_id}/result")
async def get_job_result(job_id: int):
    """Get job result file"""
    job = await job_service.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job not completed")
    
    if not job.result_path:
        raise HTTPException(status_code=404, detail="Result file not found")
    
    return {
        "download_url": f"/api/v1/files/{job.id}/content",
        "file_path": job.result_path
    }