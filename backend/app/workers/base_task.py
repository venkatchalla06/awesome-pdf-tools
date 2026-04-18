from celery import Task
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import get_settings
from app.db.models.job import Job, JobStatus

settings = get_settings()

_sync_url = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2")
sync_engine = create_engine(_sync_url, pool_size=5, max_overflow=10)
SyncSession = sessionmaker(sync_engine)


class PDFBaseTask(Task):
    abstract = True

    def update_job(self, job_id: str, **kwargs):
        with SyncSession() as session:
            job = session.get(Job, job_id)
            if job:
                for k, v in kwargs.items():
                    setattr(job, k, v)
                session.commit()

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        job_id = args[0] if args else task_id
        self.update_job(job_id, status=JobStatus.FAILED, error_message=str(exc)[:500])
