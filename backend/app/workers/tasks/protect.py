import os
import tempfile

import fitz

from app.workers.celery_app import celery_app
from app.workers.base_task import PDFBaseTask, SyncSession
from app.db.models.job import Job, JobStatus
from app.services.storage import storage


@celery_app.task(
    bind=True, base=PDFBaseTask,
    name="app.workers.tasks.protect.protect_task",
    max_retries=2, soft_time_limit=120,
)
def protect_task(self, job_id: str):
    self.update_job(job_id, status=JobStatus.PROCESSING, progress=10)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        input_key = job.input_keys[0]
        options = dict(job.options)

    password = options.get("password", "")
    if not password:
        raise ValueError("Password is required for protect operation")

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pdf")
        output_path = os.path.join(tmpdir, "protected.pdf")
        storage.download_to_temp(input_key, input_path)

        doc = fitz.open(input_path)
        # owner_pw allows full access; user_pw restricts printing/copying
        doc.save(
            output_path,
            encryption=fitz.PDF_ENCRYPT_AES_256,
            user_pw=password,
            owner_pw=password + "_owner",
            permissions=fitz.PDF_PERM_PRINT,
        )
        doc.close()

        output_key = f"results/{job_id}/protected.pdf"
        storage.upload_from_temp(output_path, output_key)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        job.status = JobStatus.COMPLETED
        job.output_key = output_key
        job.progress = 100
        job.options = {**options, "output_filename": "protected.pdf", "password": ""}  # don't store password
        session.commit()

    return output_key


@celery_app.task(
    bind=True, base=PDFBaseTask,
    name="app.workers.tasks.protect.unlock_task",
    max_retries=2, soft_time_limit=120,
)
def unlock_task(self, job_id: str):
    self.update_job(job_id, status=JobStatus.PROCESSING, progress=10)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        input_key = job.input_keys[0]
        options = dict(job.options)

    password = options.get("password", "")

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pdf")
        output_path = os.path.join(tmpdir, "unlocked.pdf")
        storage.download_to_temp(input_key, input_path)

        doc = fitz.open(input_path)
        if doc.is_encrypted:
            if not doc.authenticate(password):
                raise ValueError("Wrong password")

        doc.save(output_path, encryption=fitz.PDF_ENCRYPT_NONE, garbage=4, deflate=True)
        doc.close()

        output_key = f"results/{job_id}/unlocked.pdf"
        storage.upload_from_temp(output_path, output_key)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        job.status = JobStatus.COMPLETED
        job.output_key = output_key
        job.progress = 100
        job.options = {**options, "output_filename": "unlocked.pdf", "password": ""}
        session.commit()

    return output_key
