import os
import tempfile

import fitz  # PyMuPDF

from app.workers.celery_app import celery_app
from app.workers.base_task import PDFBaseTask, SyncSession
from app.db.models.job import Job, JobStatus
from app.services.storage import storage


@celery_app.task(
    bind=True,
    base=PDFBaseTask,
    name="app.workers.tasks.merge.merge_task",
    max_retries=2,
    soft_time_limit=120,
)
def merge_task(self, job_id: str):
    self.update_job(job_id, status=JobStatus.PROCESSING, progress=5)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        input_keys = job.input_keys
        output_filename = job.options.get("output_filename", "merged.pdf")

    with tempfile.TemporaryDirectory() as tmpdir:
        local_paths = []
        for i, key in enumerate(input_keys):
            path = os.path.join(tmpdir, f"input_{i}.pdf")
            storage.download_to_temp(key, path)
            local_paths.append(path)
            self.update_job(job_id, progress=5 + int((i + 1) / len(input_keys) * 55))

        merged = fitz.open()
        for path in local_paths:
            with fitz.open(path) as doc:
                merged.insert_pdf(doc)

        output_path = os.path.join(tmpdir, "merged.pdf")
        merged.save(output_path, garbage=4, deflate=True)
        merged.close()

        self.update_job(job_id, progress=80)

        output_key = f"results/{job_id}/{output_filename}"
        storage.upload_from_temp(output_path, output_key)

    self.update_job(job_id, status=JobStatus.COMPLETED, output_key=output_key, progress=100)
    return output_key
