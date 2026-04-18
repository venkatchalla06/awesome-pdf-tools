import os
import tempfile

from app.workers.celery_app import celery_app
from app.workers.base_task import PDFBaseTask, SyncSession
from app.db.models.job import Job, JobStatus
from app.services.storage import storage


@celery_app.task(
    bind=True, base=PDFBaseTask,
    name="app.workers.tasks.ocr.ocr_task",
    max_retries=1, soft_time_limit=600,
    queue="ocr",
)
def ocr_task(self, job_id: str):
    self.update_job(job_id, status=JobStatus.PROCESSING, progress=5)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        input_key = job.input_keys[0]
        options = dict(job.options)

    language = options.get("language", "eng")

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pdf")
        output_path = os.path.join(tmpdir, "ocr_result.pdf")
        storage.download_to_temp(input_key, input_path)
        self.update_job(job_id, progress=15)

        try:
            import ocrmypdf
            ocrmypdf.ocr(
                input_path,
                output_path,
                language=language,
                skip_text=True,
                optimize=1,
                progress_bar=False,
                invalidate_digital_signatures=True,  # strip signatures so OCR can proceed
            )
        except (ImportError, TypeError, AttributeError):
            # Fallback when ocrmypdf/pikepdf have a version incompatibility or
            # the flag doesn't exist — pytesseract has no such restrictions.
            _ocr_fallback(input_path, output_path, language, self, job_id)

        self.update_job(job_id, progress=90)

        output_key = f"results/{job_id}/ocr_result.pdf"
        storage.upload_from_temp(output_path, output_key)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        job.status = JobStatus.COMPLETED
        job.output_key = output_key
        job.progress = 100
        job.options = {**options, "output_filename": "ocr_result.pdf"}
        session.commit()

    return output_key


def _ocr_fallback(input_path: str, output_path: str, language: str, task, job_id: str):
    import fitz
    import pytesseract
    from PIL import Image

    doc = fitz.open(input_path)
    total = len(doc)
    out_doc = fitz.open()

    for i, page in enumerate(doc):
        mat = fitz.Matrix(300 / 72, 300 / 72)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        text = pytesseract.image_to_string(img, lang=language)

        new_page = out_doc.new_page(width=page.rect.width, height=page.rect.height)
        new_page.insert_image(new_page.rect, pixmap=pix)
        # Invisible text overlay for searchability
        new_page.insert_textbox(
            new_page.rect, text,
            fontsize=1, color=(1, 1, 1), fill_opacity=0,
        )
        task.update_job(job_id, progress=15 + int((i + 1) / total * 70))

    doc.close()
    out_doc.save(output_path, garbage=4, deflate=True)
    out_doc.close()
