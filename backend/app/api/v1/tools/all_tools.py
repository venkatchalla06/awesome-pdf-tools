"""
All tool endpoints (except merge, which has its own file).
Each endpoint: validates input → creates Job → dispatches Celery task → returns 202.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid
from datetime import datetime, timedelta

from app.db.session import get_db
from app.db.models.job import Job, JobStatus, ToolType
from app.dependencies import get_current_user_optional
from app.schemas.job import JobResponse
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/tools", tags=["tools"])


def make_job(tool: ToolType, input_keys: list, options: dict, user_id=None) -> Job:
    return Job(
        id=uuid.uuid4(),
        user_id=user_id,
        tool=tool,
        status=JobStatus.PENDING,
        input_keys=input_keys,
        options=options,
        expires_at=datetime.utcnow() + timedelta(hours=settings.TEMP_FILE_TTL_HOURS),
    )


# ── Split ──────────────────────────────────────────────────────────────────

class SplitRequest(BaseModel):
    input_key: str
    ranges: Optional[List[dict]] = None        # [{"start":1,"end":3}]
    every_n_pages: Optional[int] = None


@router.post("/split", response_model=JobResponse, status_code=202)
async def split_pdf(
    body: SplitRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    options = {}
    if body.ranges:
        options["ranges"] = body.ranges
    elif body.every_n_pages:
        options["every_n_pages"] = body.every_n_pages

    job = make_job(ToolType.SPLIT, [body.input_key], options,
                   current_user.id if current_user else None)
    db.add(job); await db.commit(); await db.refresh(job)
    from app.workers.tasks.split import split_task
    split_task.apply_async(args=[str(job.id)], task_id=str(job.id))
    return job


# ── Compress ───────────────────────────────────────────────────────────────

class CompressRequest(BaseModel):
    input_key: str
    quality: str = Field("recommended", pattern="^(low|recommended|extreme)$")


@router.post("/compress", response_model=JobResponse, status_code=202)
async def compress_pdf(
    body: CompressRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    job = make_job(ToolType.COMPRESS, [body.input_key], {"quality": body.quality},
                   current_user.id if current_user else None)
    db.add(job); await db.commit(); await db.refresh(job)
    from app.workers.tasks.compress import compress_task
    compress_task.apply_async(args=[str(job.id)], task_id=str(job.id))
    return job


# ── Rotate ─────────────────────────────────────────────────────────────────

class RotateRequest(BaseModel):
    input_key: str
    angle: int = Field(90, description="90 | 180 | 270")
    pages: str = "all"   # "all" or comma-separated "1,2,3"


@router.post("/rotate", response_model=JobResponse, status_code=202)
async def rotate_pdf(
    body: RotateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    if body.angle not in (90, 180, 270):
        raise HTTPException(400, "angle must be 90, 180, or 270")
    pages = (
        [int(p) for p in body.pages.split(",")]
        if body.pages != "all" else "all"
    )
    job = make_job(ToolType.ROTATE, [body.input_key], {"angle": body.angle, "pages": pages},
                   current_user.id if current_user else None)
    db.add(job); await db.commit(); await db.refresh(job)
    from app.workers.tasks.rotate import rotate_task
    rotate_task.apply_async(args=[str(job.id)], task_id=str(job.id))
    return job


# ── Watermark ──────────────────────────────────────────────────────────────

class WatermarkRequest(BaseModel):
    input_key: str
    text: str = "CONFIDENTIAL"
    opacity: float = Field(0.3, ge=0.1, le=1.0)
    color: List[float] = Field([0.7, 0.7, 0.7], description="RGB 0-1")


@router.post("/watermark", response_model=JobResponse, status_code=202)
async def watermark_pdf(
    body: WatermarkRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    job = make_job(
        ToolType.WATERMARK, [body.input_key],
        {"text": body.text, "opacity": body.opacity, "color": body.color},
        current_user.id if current_user else None,
    )
    db.add(job); await db.commit(); await db.refresh(job)
    from app.workers.tasks.watermark import watermark_task
    watermark_task.apply_async(args=[str(job.id)], task_id=str(job.id))
    return job


# ── Protect ────────────────────────────────────────────────────────────────

class ProtectRequest(BaseModel):
    input_key: str
    password: str = Field(..., min_length=4)


@router.post("/protect", response_model=JobResponse, status_code=202)
async def protect_pdf(
    body: ProtectRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    job = make_job(ToolType.PROTECT, [body.input_key], {"password": body.password},
                   current_user.id if current_user else None)
    db.add(job); await db.commit(); await db.refresh(job)
    from app.workers.tasks.protect import protect_task
    protect_task.apply_async(args=[str(job.id)], task_id=str(job.id))
    return job


# ── Unlock ─────────────────────────────────────────────────────────────────

class UnlockRequest(BaseModel):
    input_key: str
    password: str = ""


@router.post("/unlock", response_model=JobResponse, status_code=202)
async def unlock_pdf(
    body: UnlockRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    job = make_job(ToolType.UNLOCK, [body.input_key], {"password": body.password},
                   current_user.id if current_user else None)
    db.add(job); await db.commit(); await db.refresh(job)
    from app.workers.tasks.protect import unlock_task
    unlock_task.apply_async(args=[str(job.id)], task_id=str(job.id))
    return job


# ── Page Numbers ───────────────────────────────────────────────────────────

class PageNumbersRequest(BaseModel):
    input_key: str
    position: str = "bottom-center"
    start_at: int = 1
    format: str = "{n}"


@router.post("/page-numbers", response_model=JobResponse, status_code=202)
async def add_page_numbers(
    body: PageNumbersRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    job = make_job(
        ToolType.PAGE_NUMBERS, [body.input_key],
        {"position": body.position, "start_at": body.start_at, "format": body.format},
        current_user.id if current_user else None,
    )
    db.add(job); await db.commit(); await db.refresh(job)
    from app.workers.tasks.page_numbers import page_numbers_task
    page_numbers_task.apply_async(args=[str(job.id)], task_id=str(job.id))
    return job


# ── OCR ────────────────────────────────────────────────────────────────────

class OCRRequest(BaseModel):
    input_key: str
    language: str = "eng"


@router.post("/ocr", response_model=JobResponse, status_code=202)
async def ocr_pdf(
    body: OCRRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    job = make_job(ToolType.OCR, [body.input_key], {"language": body.language},
                   current_user.id if current_user else None)
    db.add(job); await db.commit(); await db.refresh(job)
    from app.workers.tasks.ocr import ocr_task
    ocr_task.apply_async(args=[str(job.id)], task_id=str(job.id))
    return job


# ── PDF → JPG ──────────────────────────────────────────────────────────────

class PdfToJpgRequest(BaseModel):
    input_key: str
    dpi: int = Field(150, ge=72, le=300)


@router.post("/pdf-to-jpg", response_model=JobResponse, status_code=202)
async def pdf_to_jpg(
    body: PdfToJpgRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    job = make_job(ToolType.PDF_TO_JPG, [body.input_key], {"dpi": body.dpi},
                   current_user.id if current_user else None)
    db.add(job); await db.commit(); await db.refresh(job)
    from app.workers.tasks.convert import pdf_to_jpg_task
    pdf_to_jpg_task.apply_async(args=[str(job.id)], task_id=str(job.id))
    return job


# ── JPG → PDF ──────────────────────────────────────────────────────────────

class JpgToPdfRequest(BaseModel):
    input_keys: List[str]


@router.post("/jpg-to-pdf", response_model=JobResponse, status_code=202)
async def jpg_to_pdf(
    body: JpgToPdfRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    if not body.input_keys:
        raise HTTPException(400, "At least one image required")
    job = make_job(ToolType.JPG_TO_PDF, body.input_keys, {},
                   current_user.id if current_user else None)
    db.add(job); await db.commit(); await db.refresh(job)
    from app.workers.tasks.convert import jpg_to_pdf_task
    jpg_to_pdf_task.apply_async(args=[str(job.id)], task_id=str(job.id))
    return job


# ── PDF → Word ─────────────────────────────────────────────────────────────

class PdfToWordRequest(BaseModel):
    input_key: str


@router.post("/pdf-to-word", response_model=JobResponse, status_code=202)
async def pdf_to_word(
    body: PdfToWordRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    job = make_job(ToolType.PDF_TO_WORD, [body.input_key], {},
                   current_user.id if current_user else None)
    db.add(job); await db.commit(); await db.refresh(job)
    from app.workers.tasks.convert import pdf_to_word_task
    pdf_to_word_task.apply_async(args=[str(job.id)], task_id=str(job.id))
    return job


# ── Word → PDF ─────────────────────────────────────────────────────────────

class WordToPdfRequest(BaseModel):
    input_key: str


@router.post("/word-to-pdf", response_model=JobResponse, status_code=202)
async def word_to_pdf(
    body: WordToPdfRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    job = make_job(ToolType.WORD_TO_PDF, [body.input_key], {},
                   current_user.id if current_user else None)
    db.add(job); await db.commit(); await db.refresh(job)
    from app.workers.tasks.convert import word_to_pdf_task
    word_to_pdf_task.apply_async(args=[str(job.id)], task_id=str(job.id))
    return job


# ── AI Summarize ───────────────────────────────────────────────────────────

class SummarizeRequest(BaseModel):
    input_key: str
    style: str = Field("bullet", pattern="^(bullet|paragraph|executive)$")
    output_language: str = "English"


@router.post("/summarize", response_model=JobResponse, status_code=202)
async def summarize_pdf(
    body: SummarizeRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    job = make_job(
        ToolType.SUMMARIZE, [body.input_key],
        {"style": body.style, "output_language": body.output_language},
        current_user.id if current_user else None,
    )
    db.add(job); await db.commit(); await db.refresh(job)
    from app.workers.tasks.ai_tasks import summarize_task
    summarize_task.apply_async(args=[str(job.id)], task_id=str(job.id))
    return job


# ── AI Translate ───────────────────────────────────────────────────────────

class TranslateRequest(BaseModel):
    input_key: str
    target_language: str = "Spanish"


@router.post("/translate", response_model=JobResponse, status_code=202)
async def translate_pdf(
    body: TranslateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    job = make_job(
        ToolType.TRANSLATE, [body.input_key],
        {"target_language": body.target_language},
        current_user.id if current_user else None,
    )
    db.add(job); await db.commit(); await db.refresh(job)
    from app.workers.tasks.ai_tasks import translate_task
    translate_task.apply_async(args=[str(job.id)], task_id=str(job.id))
    return job


# ── Remove Pages ───────────────────────────────────────────────────────────────

class RemovePagesRequest(BaseModel):
    input_key: str
    pages: str  # e.g. "1,3,5-7"


@router.post("/remove-pages", response_model=JobResponse, status_code=202)
async def remove_pages(
    body: RemovePagesRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    job = make_job(ToolType.REMOVE_PAGES, [body.input_key], {"pages": body.pages},
                   current_user.id if current_user else None)
    db.add(job); await db.commit(); await db.refresh(job)
    from app.workers.tasks.page_ops import remove_pages_task
    remove_pages_task.apply_async(args=[str(job.id)], task_id=str(job.id))
    return job


# ── Extract Pages ──────────────────────────────────────────────────────────────

class ExtractPagesRequest(BaseModel):
    input_key: str
    pages: str  # e.g. "1-5,7"


@router.post("/extract-pages", response_model=JobResponse, status_code=202)
async def extract_pages(
    body: ExtractPagesRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    job = make_job(ToolType.EXTRACT_PAGES, [body.input_key], {"pages": body.pages},
                   current_user.id if current_user else None)
    db.add(job); await db.commit(); await db.refresh(job)
    from app.workers.tasks.page_ops import extract_pages_task
    extract_pages_task.apply_async(args=[str(job.id)], task_id=str(job.id))
    return job


# ── Organize PDF ───────────────────────────────────────────────────────────────

class OrganizeRequest(BaseModel):
    input_key: str
    order: str  # e.g. "3,1,2,4"


@router.post("/organize", response_model=JobResponse, status_code=202)
async def organize_pdf(
    body: OrganizeRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    job = make_job(ToolType.ORGANIZE, [body.input_key], {"order": body.order},
                   current_user.id if current_user else None)
    db.add(job); await db.commit(); await db.refresh(job)
    from app.workers.tasks.page_ops import organize_task
    organize_task.apply_async(args=[str(job.id)], task_id=str(job.id))
    return job


# ── Repair PDF ─────────────────────────────────────────────────────────────────

class RepairRequest(BaseModel):
    input_key: str


@router.post("/repair", response_model=JobResponse, status_code=202)
async def repair_pdf(
    body: RepairRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    job = make_job(ToolType.REPAIR, [body.input_key], {},
                   current_user.id if current_user else None)
    db.add(job); await db.commit(); await db.refresh(job)
    from app.workers.tasks.page_ops import repair_task
    repair_task.apply_async(args=[str(job.id)], task_id=str(job.id))
    return job


# ── Crop PDF ───────────────────────────────────────────────────────────────────

class CropRequest(BaseModel):
    input_key: str
    top: float = Field(0, ge=0, le=45)
    bottom: float = Field(0, ge=0, le=45)
    left: float = Field(0, ge=0, le=45)
    right: float = Field(0, ge=0, le=45)


@router.post("/crop", response_model=JobResponse, status_code=202)
async def crop_pdf(
    body: CropRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    job = make_job(ToolType.CROP, [body.input_key],
                   {"top": body.top, "bottom": body.bottom,
                    "left": body.left, "right": body.right},
                   current_user.id if current_user else None)
    db.add(job); await db.commit(); await db.refresh(job)
    from app.workers.tasks.page_ops import crop_task
    crop_task.apply_async(args=[str(job.id)], task_id=str(job.id))
    return job


# ── Redact PDF ─────────────────────────────────────────────────────────────────

class RedactRequest(BaseModel):
    input_key: str
    terms: str  # comma-separated


@router.post("/redact", response_model=JobResponse, status_code=202)
async def redact_pdf(
    body: RedactRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    job = make_job(ToolType.REDACT, [body.input_key], {"terms": body.terms},
                   current_user.id if current_user else None)
    db.add(job); await db.commit(); await db.refresh(job)
    from app.workers.tasks.page_ops import redact_task
    redact_task.apply_async(args=[str(job.id)], task_id=str(job.id))
    return job


# ── PDF → PDF/A ────────────────────────────────────────────────────────────────

class PdfToPdfARequest(BaseModel):
    input_key: str


@router.post("/pdf-to-pdfa", response_model=JobResponse, status_code=202)
async def pdf_to_pdfa(
    body: PdfToPdfARequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    job = make_job(ToolType.PDF_TO_PDFA, [body.input_key], {},
                   current_user.id if current_user else None)
    db.add(job); await db.commit(); await db.refresh(job)
    from app.workers.tasks.page_ops import pdf_to_pdfa_task
    pdf_to_pdfa_task.apply_async(args=[str(job.id)], task_id=str(job.id))
    return job


# ── PowerPoint → PDF ───────────────────────────────────────────────────────────

class PptxToPdfRequest(BaseModel):
    input_key: str


@router.post("/pptx-to-pdf", response_model=JobResponse, status_code=202)
async def pptx_to_pdf(
    body: PptxToPdfRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    job = make_job(ToolType.PPTX_TO_PDF, [body.input_key], {},
                   current_user.id if current_user else None)
    db.add(job); await db.commit(); await db.refresh(job)
    from app.workers.tasks.convert import pptx_to_pdf_task
    pptx_to_pdf_task.apply_async(args=[str(job.id)], task_id=str(job.id))
    return job


# ── Excel → PDF ────────────────────────────────────────────────────────────────

class XlsxToPdfRequest(BaseModel):
    input_key: str


@router.post("/xlsx-to-pdf", response_model=JobResponse, status_code=202)
async def xlsx_to_pdf(
    body: XlsxToPdfRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    job = make_job(ToolType.XLSX_TO_PDF, [body.input_key], {},
                   current_user.id if current_user else None)
    db.add(job); await db.commit(); await db.refresh(job)
    from app.workers.tasks.convert import xlsx_to_pdf_task
    xlsx_to_pdf_task.apply_async(args=[str(job.id)], task_id=str(job.id))
    return job


# ── PDF → PowerPoint ───────────────────────────────────────────────────────────

class PdfToPptxRequest(BaseModel):
    input_key: str


@router.post("/pdf-to-pptx", response_model=JobResponse, status_code=202)
async def pdf_to_pptx(
    body: PdfToPptxRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    job = make_job(ToolType.PDF_TO_PPTX, [body.input_key], {},
                   current_user.id if current_user else None)
    db.add(job); await db.commit(); await db.refresh(job)
    from app.workers.tasks.convert import pdf_to_pptx_task
    pdf_to_pptx_task.apply_async(args=[str(job.id)], task_id=str(job.id))
    return job


# ── HTML → PDF ─────────────────────────────────────────────────────────────────

class HtmlToPdfRequest(BaseModel):
    input_key: str


@router.post("/html-to-pdf", response_model=JobResponse, status_code=202)
async def html_to_pdf(
    body: HtmlToPdfRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    job = make_job(ToolType.HTML_TO_PDF, [body.input_key], {},
                   current_user.id if current_user else None)
    db.add(job); await db.commit(); await db.refresh(job)
    from app.workers.tasks.convert import html_to_pdf_task
    html_to_pdf_task.apply_async(args=[str(job.id)], task_id=str(job.id))
    return job
