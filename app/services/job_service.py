import os
import json
import tempfile
from typing import Optional
from app.schemas.job import JobCreate, JobResponse
from app.services.pdf_processor import PDFProcessor

UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory job store (replace with DB-backed store when DB is configured)
_jobs: dict = {}
_next_id = 1

processor = PDFProcessor()


class JobService:
    async def create_job(self, job_data: JobCreate):
        global _next_id
        job = {
            "id": _next_id,
            "file_id": job_data.file_id,
            "job_type": job_data.job_type,
            "status": "pending",
            "parameters": job_data.parameters or {},
            "result_path": None,
            "error_message": None,
            "started_at": None,
            "completed_at": None,
            "created_at": None,
        }
        _jobs[_next_id] = job
        _next_id += 1
        return _JobObj(job)

    async def get_job(self, job_id: int):
        job = _jobs.get(job_id)
        return _JobObj(job) if job else None

    async def process_job(self, job_id: int):
        job = _jobs.get(job_id)
        if not job:
            return

        job["status"] = "processing"
        try:
            input_path = os.path.join(UPLOAD_DIR, str(job["file_id"]))
            output_path = os.path.join(UPLOAD_DIR, f"result_{job_id}")
            params = job.get("parameters", {})

            jtype = job["job_type"]
            if jtype == "pdf_to_ppt":
                output_path += ".pptx"
                processor.pdf_to_powerpoint(input_path, output_path)
            elif jtype == "merge":
                files = params.get("files", [input_path])
                output_path += ".pdf"
                processor.merge_pdfs(files, output_path)
            elif jtype == "split":
                out_dir = output_path + "_split"
                os.makedirs(out_dir, exist_ok=True)
                processor.split_pdf(input_path, out_dir, params.get("pages"))
                output_path = out_dir
            elif jtype == "compress":
                output_path += ".pdf"
                processor.compress_pdf(input_path, output_path, params.get("quality", "medium"))
            elif jtype == "watermark":
                output_path += ".pdf"
                processor.add_watermark(input_path, output_path, params.get("text", "WATERMARK"))
            elif jtype == "page_number":
                output_path += ".pdf"
                processor.add_page_numbers(input_path, output_path)
            elif jtype == "ocr":
                output_path += ".pdf"
                processor.ocr_pdf(input_path, output_path)
            else:
                raise ValueError(f"Unsupported job type: {jtype}")

            job["status"] = "completed"
            job["result_path"] = output_path
        except Exception as exc:
            job["status"] = "failed"
            job["error_message"] = str(exc)


class _JobObj:
    """Thin wrapper so endpoint code can access job fields as attributes."""
    def __init__(self, data: dict):
        self.__dict__.update(data)
