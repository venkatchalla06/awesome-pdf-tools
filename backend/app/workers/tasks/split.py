import os
import tempfile
import zipfile

import fitz

from app.workers.celery_app import celery_app
from app.workers.base_task import PDFBaseTask, SyncSession
from app.db.models.job import Job, JobStatus
from app.services.storage import storage


def parse_ranges(total_pages: int, options: dict) -> list[tuple[int, int]]:
    if "ranges" in options:
        # User-defined: [{"start": 1, "end": 3}, ...] 1-indexed
        return [(r["start"] - 1, r["end"] - 1) for r in options["ranges"]]
    elif "every_n_pages" in options:
        n = int(options["every_n_pages"])
        return [(i, min(i + n - 1, total_pages - 1)) for i in range(0, total_pages, n)]
    else:
        return [(i, i) for i in range(total_pages)]


@celery_app.task(
    bind=True, base=PDFBaseTask,
    name="app.workers.tasks.split.split_task",
    max_retries=2, soft_time_limit=120,
)
def split_task(self, job_id: str):
    self.update_job(job_id, status=JobStatus.PROCESSING, progress=5)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        input_key = job.input_keys[0]
        options = dict(job.options)

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pdf")
        storage.download_to_temp(input_key, input_path)

        source = fitz.open(input_path)
        total = len(source)
        ranges = parse_ranges(total, options)

        split_files = []
        for idx, (start, end) in enumerate(ranges):
            out_doc = fitz.open()
            out_doc.insert_pdf(source, from_page=start, to_page=end)
            out_path = os.path.join(tmpdir, f"part_{idx + 1}.pdf")
            out_doc.save(out_path, garbage=4, deflate=True)
            out_doc.close()
            split_files.append(out_path)
            self.update_job(job_id, progress=10 + int((idx + 1) / len(ranges) * 70))

        source.close()

        if len(split_files) > 1:
            zip_path = os.path.join(tmpdir, "split_result.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in split_files:
                    zf.write(f, os.path.basename(f))
            output_key = f"results/{job_id}/split_result.zip"
            storage.upload_from_temp(zip_path, output_key, content_type="application/zip")
            output_filename = "split_result.zip"
        else:
            output_key = f"results/{job_id}/part_1.pdf"
            storage.upload_from_temp(split_files[0], output_key)
            output_filename = "part_1.pdf"

    with SyncSession() as session:
        job = session.get(Job, job_id)
        job.status = JobStatus.COMPLETED
        job.output_key = output_key
        job.progress = 100
        job.options = {**options, "output_filename": output_filename}
        session.commit()

    return output_key
