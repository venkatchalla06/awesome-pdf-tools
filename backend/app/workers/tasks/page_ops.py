"""
Page manipulation tasks: remove, extract, organize, crop, repair, redact, pdf_to_pdfa.
"""
import os
import re
import subprocess
import tempfile

import fitz
import pikepdf

from app.workers.celery_app import celery_app
from app.workers.base_task import PDFBaseTask, SyncSession
from app.db.models.job import Job, JobStatus
from app.services.storage import storage


def parse_page_list(spec: str, total: int) -> list[int]:
    """Parse '1,3,5-7' into 0-indexed page list. Returns sorted unique list."""
    pages = set()
    for part in spec.split(","):
        part = part.strip()
        m = re.match(r"^(\d+)-(\d+)$", part)
        if m:
            start, end = int(m.group(1)), int(m.group(2))
            for p in range(start, end + 1):
                if 1 <= p <= total:
                    pages.add(p - 1)
        elif part.isdigit():
            p = int(part)
            if 1 <= p <= total:
                pages.add(p - 1)
    return sorted(pages)


# ── Remove Pages ──────────────────────────────────────────────────────────────

@celery_app.task(
    bind=True, base=PDFBaseTask,
    name="app.workers.tasks.page_ops.remove_pages_task",
    max_retries=2, soft_time_limit=120,
)
def remove_pages_task(self, job_id: str):
    self.update_job(job_id, status=JobStatus.PROCESSING, progress=10)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        input_key = job.input_keys[0]
        options = dict(job.options)

    pages_spec = options.get("pages", "")

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pdf")
        output_path = os.path.join(tmpdir, "result.pdf")
        storage.download_to_temp(input_key, input_path)

        doc = fitz.open(input_path)
        total = len(doc)
        to_remove = set(parse_page_list(pages_spec, total))
        if not to_remove:
            raise ValueError("No valid pages specified")
        if len(to_remove) >= total:
            raise ValueError("Cannot remove all pages")

        for idx in sorted(to_remove, reverse=True):
            doc.delete_page(idx)

        self.update_job(job_id, progress=70)
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()

        output_key = f"results/{job_id}/result.pdf"
        storage.upload_from_temp(output_path, output_key)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        job.status = JobStatus.COMPLETED
        job.output_key = output_key
        job.progress = 100
        job.options = {**options, "output_filename": "result.pdf"}
        session.commit()

    return output_key


# ── Extract Pages ─────────────────────────────────────────────────────────────

@celery_app.task(
    bind=True, base=PDFBaseTask,
    name="app.workers.tasks.page_ops.extract_pages_task",
    max_retries=2, soft_time_limit=120,
)
def extract_pages_task(self, job_id: str):
    self.update_job(job_id, status=JobStatus.PROCESSING, progress=10)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        input_key = job.input_keys[0]
        options = dict(job.options)

    pages_spec = options.get("pages", "")

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pdf")
        output_path = os.path.join(tmpdir, "extracted.pdf")
        storage.download_to_temp(input_key, input_path)

        src = fitz.open(input_path)
        total = len(src)
        to_keep = parse_page_list(pages_spec, total)
        if not to_keep:
            raise ValueError("No valid pages specified")

        out = fitz.open()
        for idx in to_keep:
            out.insert_pdf(src, from_page=idx, to_page=idx)

        self.update_job(job_id, progress=70)
        out.save(output_path, garbage=4, deflate=True)
        out.close()
        src.close()

        output_key = f"results/{job_id}/extracted.pdf"
        storage.upload_from_temp(output_path, output_key)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        job.status = JobStatus.COMPLETED
        job.output_key = output_key
        job.progress = 100
        job.options = {**options, "output_filename": "extracted.pdf"}
        session.commit()

    return output_key


# ── Organize (Reorder) Pages ──────────────────────────────────────────────────

@celery_app.task(
    bind=True, base=PDFBaseTask,
    name="app.workers.tasks.page_ops.organize_task",
    max_retries=2, soft_time_limit=120,
)
def organize_task(self, job_id: str):
    self.update_job(job_id, status=JobStatus.PROCESSING, progress=10)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        input_key = job.input_keys[0]
        options = dict(job.options)

    order_spec = options.get("order", "")

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pdf")
        output_path = os.path.join(tmpdir, "organized.pdf")
        storage.download_to_temp(input_key, input_path)

        src = fitz.open(input_path)
        total = len(src)
        order = parse_page_list(order_spec, total)
        if not order:
            raise ValueError("No valid page order specified")

        out = fitz.open()
        for idx in order:
            out.insert_pdf(src, from_page=idx, to_page=idx)

        self.update_job(job_id, progress=70)
        out.save(output_path, garbage=4, deflate=True)
        out.close()
        src.close()

        output_key = f"results/{job_id}/organized.pdf"
        storage.upload_from_temp(output_path, output_key)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        job.status = JobStatus.COMPLETED
        job.output_key = output_key
        job.progress = 100
        job.options = {**options, "output_filename": "organized.pdf"}
        session.commit()

    return output_key


# ── Crop PDF ──────────────────────────────────────────────────────────────────

@celery_app.task(
    bind=True, base=PDFBaseTask,
    name="app.workers.tasks.page_ops.crop_task",
    max_retries=2, soft_time_limit=120,
)
def crop_task(self, job_id: str):
    self.update_job(job_id, status=JobStatus.PROCESSING, progress=10)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        input_key = job.input_keys[0]
        options = dict(job.options)

    # margins in % (0-50)
    top    = float(options.get("top", 0)) / 100
    bottom = float(options.get("bottom", 0)) / 100
    left   = float(options.get("left", 0)) / 100
    right  = float(options.get("right", 0)) / 100

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pdf")
        output_path = os.path.join(tmpdir, "cropped.pdf")
        storage.download_to_temp(input_key, input_path)

        doc = fitz.open(input_path)
        for page in doc:
            r = page.rect
            w, h = r.width, r.height
            new_rect = fitz.Rect(
                r.x0 + left * w,
                r.y0 + top * h,
                r.x1 - right * w,
                r.y1 - bottom * h,
            )
            page.set_cropbox(new_rect)

        self.update_job(job_id, progress=70)
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()

        output_key = f"results/{job_id}/cropped.pdf"
        storage.upload_from_temp(output_path, output_key)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        job.status = JobStatus.COMPLETED
        job.output_key = output_key
        job.progress = 100
        job.options = {**options, "output_filename": "cropped.pdf"}
        session.commit()

    return output_key


# ── Repair PDF ────────────────────────────────────────────────────────────────

@celery_app.task(
    bind=True, base=PDFBaseTask,
    name="app.workers.tasks.page_ops.repair_task",
    max_retries=2, soft_time_limit=120,
)
def repair_task(self, job_id: str):
    self.update_job(job_id, status=JobStatus.PROCESSING, progress=20)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        input_key = job.input_keys[0]
        options = dict(job.options)

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pdf")
        output_path = os.path.join(tmpdir, "repaired.pdf")
        storage.download_to_temp(input_key, input_path)

        self.update_job(job_id, progress=40)
        with pikepdf.open(input_path, suppress_warnings=True) as pdf:
            pdf.save(output_path)

        output_key = f"results/{job_id}/repaired.pdf"
        storage.upload_from_temp(output_path, output_key)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        job.status = JobStatus.COMPLETED
        job.output_key = output_key
        job.progress = 100
        job.options = {**options, "output_filename": "repaired.pdf"}
        session.commit()

    return output_key


# ── Redact PDF ────────────────────────────────────────────────────────────────

@celery_app.task(
    bind=True, base=PDFBaseTask,
    name="app.workers.tasks.page_ops.redact_task",
    max_retries=2, soft_time_limit=180,
)
def redact_task(self, job_id: str):
    self.update_job(job_id, status=JobStatus.PROCESSING, progress=10)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        input_key = job.input_keys[0]
        options = dict(job.options)

    terms_raw = options.get("terms", "")
    terms = [t.strip() for t in terms_raw.split(",") if t.strip()]
    if not terms:
        raise ValueError("No redaction terms provided")

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pdf")
        output_path = os.path.join(tmpdir, "redacted.pdf")
        storage.download_to_temp(input_key, input_path)

        doc = fitz.open(input_path)
        total = len(doc)
        for i, page in enumerate(doc):
            for term in terms:
                areas = page.search_for(term, quads=False)
                for area in areas:
                    page.add_redact_annot(area, fill=(0, 0, 0))
            page.apply_redactions()
            self.update_job(job_id, progress=10 + int((i + 1) / total * 80))

        doc.save(output_path, garbage=4, deflate=True)
        doc.close()

        output_key = f"results/{job_id}/redacted.pdf"
        storage.upload_from_temp(output_path, output_key)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        job.status = JobStatus.COMPLETED
        job.output_key = output_key
        job.progress = 100
        job.options = {**options, "output_filename": "redacted.pdf"}
        session.commit()

    return output_key


# ── PDF → PDF/A ───────────────────────────────────────────────────────────────

@celery_app.task(
    bind=True, base=PDFBaseTask,
    name="app.workers.tasks.page_ops.pdf_to_pdfa_task",
    max_retries=1, soft_time_limit=300,
)
def pdf_to_pdfa_task(self, job_id: str):
    self.update_job(job_id, status=JobStatus.PROCESSING, progress=10)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        input_key = job.input_keys[0]
        options = dict(job.options)

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pdf")
        output_path = os.path.join(tmpdir, "pdfa.pdf")
        storage.download_to_temp(input_key, input_path)

        self.update_job(job_id, progress=30)

        cmd = [
            "gs",
            "-dBATCH", "-dNOPAUSE", "-dNOOUTERSAVE",
            "-dCompatibilityLevel=1.4",
            "-dPDFA=2",
            "-dPDFACompatibilityPolicy=1",
            "-sDEVICE=pdfwrite",
            "-sColorConversionStrategy=sRGB",
            f"-sOutputFile={output_path}",
            input_path,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=240)
        if result.returncode != 0:
            raise RuntimeError(f"Ghostscript failed: {result.stderr.decode()[:300]}")

        output_key = f"results/{job_id}/pdfa.pdf"
        storage.upload_from_temp(output_path, output_key)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        job.status = JobStatus.COMPLETED
        job.output_key = output_key
        job.progress = 100
        job.options = {**options, "output_filename": "pdfa.pdf"}
        session.commit()

    return output_key
