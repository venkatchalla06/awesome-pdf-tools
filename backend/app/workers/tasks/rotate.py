import os
import tempfile

import fitz

from app.workers.celery_app import celery_app
from app.workers.base_task import PDFBaseTask, SyncSession
from app.db.models.job import Job, JobStatus
from app.services.storage import storage


@celery_app.task(
    bind=True, base=PDFBaseTask,
    name="app.workers.tasks.rotate.rotate_task",
    max_retries=2, soft_time_limit=120,
)
def rotate_task(self, job_id: str):
    self.update_job(job_id, status=JobStatus.PROCESSING, progress=10)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        input_key = job.input_keys[0]
        options = dict(job.options)

    # angle: 90 | 180 | 270; pages: "all" | [1,2,3] (1-indexed)
    angle = int(options.get("angle", 90))
    pages_opt = options.get("pages", "all")

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pdf")
        output_path = os.path.join(tmpdir, "rotated.pdf")
        storage.download_to_temp(input_key, input_path)

        doc = fitz.open(input_path)
        target_pages = (
            range(len(doc)) if pages_opt == "all"
            else [p - 1 for p in pages_opt]
        )
        for i in target_pages:
            page = doc[i]
            page.set_rotation((page.rotation + angle) % 360)

        doc.save(output_path, garbage=4, deflate=True)
        doc.close()

        output_key = f"results/{job_id}/rotated.pdf"
        storage.upload_from_temp(output_path, output_key)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        job.status = JobStatus.COMPLETED
        job.output_key = output_key
        job.progress = 100
        job.options = {**options, "output_filename": "rotated.pdf"}
        session.commit()

    return output_key
