import os
import tempfile

import fitz

from app.workers.celery_app import celery_app
from app.workers.base_task import PDFBaseTask, SyncSession
from app.db.models.job import Job, JobStatus
from app.services.storage import storage

POSITIONS = {
    "bottom-center": lambda w, h: (w / 2 - 20, h - 30),
    "bottom-right":  lambda w, h: (w - 60, h - 30),
    "bottom-left":   lambda w, h: (20, h - 30),
    "top-center":    lambda w, h: (w / 2 - 20, 20),
}


@celery_app.task(
    bind=True, base=PDFBaseTask,
    name="app.workers.tasks.page_numbers.page_numbers_task",
    max_retries=2, soft_time_limit=120,
)
def page_numbers_task(self, job_id: str):
    self.update_job(job_id, status=JobStatus.PROCESSING, progress=10)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        input_key = job.input_keys[0]
        options = dict(job.options)

    position = options.get("position", "bottom-center")
    start_at = int(options.get("start_at", 1))
    fontsize = int(options.get("fontsize", 11))
    format_str = options.get("format", "{n}")  # {n} = page num, {total} = total pages

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pdf")
        output_path = os.path.join(tmpdir, "numbered.pdf")
        storage.download_to_temp(input_key, input_path)

        doc = fitz.open(input_path)
        total = len(doc)
        pos_fn = POSITIONS.get(position, POSITIONS["bottom-center"])

        for i, page in enumerate(doc):
            label = format_str.replace("{n}", str(i + start_at)).replace("{total}", str(total))
            x, y = pos_fn(page.rect.width, page.rect.height)
            page.insert_text(
                fitz.Point(x, y),
                label,
                fontsize=fontsize,
                color=(0, 0, 0),
            )
            self.update_job(job_id, progress=10 + int((i + 1) / total * 80))

        doc.save(output_path, garbage=4, deflate=True)
        doc.close()

        output_key = f"results/{job_id}/numbered.pdf"
        storage.upload_from_temp(output_path, output_key)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        job.status = JobStatus.COMPLETED
        job.output_key = output_key
        job.progress = 100
        job.options = {**options, "output_filename": "numbered.pdf"}
        session.commit()

    return output_key
