import os
import tempfile

import fitz

from app.workers.celery_app import celery_app
from app.workers.base_task import PDFBaseTask, SyncSession
from app.db.models.job import Job, JobStatus
from app.services.storage import storage


def add_text_watermark(doc: fitz.Document, text: str, opacity: float, color: tuple) -> None:
    for page in doc:
        rect = page.rect
        cx = (rect.x0 + rect.x1) / 2
        cy = (rect.y0 + rect.y1) / 2
        center = fitz.Point(cx, cy)
        tw = fitz.TextWriter(rect, opacity=opacity, color=color)
        font = fitz.Font("helv")
        text_len = sum(font.glyph_advance(ord(c)) for c in text) * 60
        pos = fitz.Point(cx - text_len / 2, cy + 20)
        tw.append(pos=pos, text=text, font=font, fontsize=60)
        tw.write_text(page, morph=(center, fitz.Matrix(45)))


@celery_app.task(
    bind=True, base=PDFBaseTask,
    name="app.workers.tasks.watermark.watermark_task",
    max_retries=2, soft_time_limit=120,
)
def watermark_task(self, job_id: str):
    self.update_job(job_id, status=JobStatus.PROCESSING, progress=10)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        input_key = job.input_keys[0]
        options = dict(job.options)

    text = options.get("text", "CONFIDENTIAL")
    opacity = float(options.get("opacity", 0.3))
    # color as [r, g, b] 0-1
    color = tuple(options.get("color", [0.7, 0.7, 0.7]))

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pdf")
        output_path = os.path.join(tmpdir, "watermarked.pdf")
        storage.download_to_temp(input_key, input_path)

        doc = fitz.open(input_path)
        add_text_watermark(doc, text, opacity, color)
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()

        output_key = f"results/{job_id}/watermarked.pdf"
        storage.upload_from_temp(output_path, output_key)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        job.status = JobStatus.COMPLETED
        job.output_key = output_key
        job.progress = 100
        job.options = {**options, "output_filename": "watermarked.pdf"}
        session.commit()

    return output_key
