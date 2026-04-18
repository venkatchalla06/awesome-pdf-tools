from datetime import datetime

from app.workers.celery_app import celery_app
from app.workers.base_task import SyncSession
from app.db.models.job import Job, JobStatus
from app.services.storage import storage


@celery_app.task(name="app.workers.tasks.cleanup.delete_expired")
def delete_expired():
    deleted_jobs = 0
    deleted_s3 = 0

    with SyncSession() as session:
        jobs = (
            session.query(Job)
            .filter(Job.expires_at < datetime.utcnow(), Job.status == JobStatus.COMPLETED)
            .all()
        )
        for job in jobs:
            for key in (job.input_keys or []):
                try:
                    storage.delete_key(key)
                    deleted_s3 += 1
                except Exception:
                    pass
            if job.output_key:
                try:
                    storage.delete_key(job.output_key)
                    deleted_s3 += 1
                except Exception:
                    pass
            job.status = JobStatus.EXPIRED
            deleted_jobs += 1
        session.commit()

    # Also sweep S3 for orphaned uploads
    deleted_s3 += storage.delete_expired_files()

    return {"expired_jobs": deleted_jobs, "deleted_s3_keys": deleted_s3}
