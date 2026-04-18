import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, Enum, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class ToolType(str, enum.Enum):
    MERGE = "merge"
    SPLIT = "split"
    COMPRESS = "compress"
    PDF_TO_WORD = "pdf_to_word"
    WORD_TO_PDF = "word_to_pdf"
    PDF_TO_JPG = "pdf_to_jpg"
    JPG_TO_PDF = "jpg_to_pdf"
    ROTATE = "rotate"
    WATERMARK = "watermark"
    UNLOCK = "unlock"
    PROTECT = "protect"
    OCR = "ocr"
    PAGE_NUMBERS = "page_numbers"
    SUMMARIZE = "summarize"
    TRANSLATE = "translate"
    REMOVE_PAGES = "remove_pages"
    EXTRACT_PAGES = "extract_pages"
    REPAIR = "repair"
    CROP = "crop"
    PPTX_TO_PDF = "pptx_to_pdf"
    XLSX_TO_PDF = "xlsx_to_pdf"
    HTML_TO_PDF = "html_to_pdf"
    REDACT = "redact"
    PDF_TO_PDFA = "pdf_to_pdfa"
    ORGANIZE = "organize"
    PDF_TO_PPTX = "pdf_to_pptx"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    tool = Column(Enum(ToolType), nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False)

    input_keys = Column(JSONB, default=list)
    output_key = Column(String, nullable=True)
    options = Column(JSONB, default=dict)

    error_message = Column(String, nullable=True)
    progress = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="jobs")
