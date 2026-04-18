import os
import subprocess
import tempfile

from app.workers.celery_app import celery_app
from app.workers.base_task import PDFBaseTask, SyncSession
from app.db.models.job import Job, JobStatus
from app.services.storage import storage

GS_PRESETS = {
    "low": "/printer",
    "recommended": "/ebook",
    "extreme": "/screen",
}


def gs_compress(input_path: str, output_path: str, quality: str) -> None:
    preset = GS_PRESETS.get(quality, "/ebook")
    cmd = [
        "gs", "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.5",
        f"-dPDFSETTINGS={preset}",
        "-dNOPAUSE", "-dQUIET", "-dBATCH",
        "-dColorImageResolution=150",
        "-dGrayImageResolution=150",
        "-dMonoImageResolution=300",
        "-dAutoRotatePages=/None",
        f"-sOutputFile={output_path}",
        input_path,
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=180)
    if result.returncode != 0:
        raise RuntimeError(f"Ghostscript failed: {result.stderr.decode()[:300]}")


@celery_app.task(
    bind=True, base=PDFBaseTask,
    name="app.workers.tasks.compress.compress_task",
    max_retries=2, soft_time_limit=180,
)
def compress_task(self, job_id: str):
    self.update_job(job_id, status=JobStatus.PROCESSING, progress=10)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        input_key = job.input_keys[0]
        quality = job.options.get("quality", "recommended")
        options = dict(job.options)

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pdf")
        output_path = os.path.join(tmpdir, "compressed.pdf")
        storage.download_to_temp(input_key, input_path)
        self.update_job(job_id, progress=30)

        try:
            gs_compress(input_path, output_path, quality)
        except (FileNotFoundError, RuntimeError):
            # Ghostscript not available: fall back to PyMuPDF deflate
            import fitz
            doc = fitz.open(input_path)
            doc.save(output_path, garbage=4, deflate=True, clean=True)
            doc.close()

        self.update_job(job_id, progress=80)

        original_size = os.path.getsize(input_path)
        compressed_size = os.path.getsize(output_path)

        # Use original if compression made it larger
        final_path = output_path if compressed_size < original_size else input_path
        final_size = min(original_size, compressed_size)

        output_key = f"results/{job_id}/compressed.pdf"
        storage.upload_from_temp(final_path, output_key)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        job.status = JobStatus.COMPLETED
        job.output_key = output_key
        job.progress = 100
        job.options = {
            **options,
            "output_filename": "compressed.pdf",
            "original_size_bytes": original_size,
            "compressed_size_bytes": final_size,
            "reduction_pct": round((1 - final_size / original_size) * 100, 1),
        }
        session.commit()

    return output_key
