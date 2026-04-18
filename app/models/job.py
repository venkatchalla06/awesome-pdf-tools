from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base
import enum

class JobStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class JobType(enum.Enum):
    MERGE = "merge"
    SPLIT = "split"
    COMPRESS = "compress"
    CONVERT_PDF_TO_WORD = "pdf_to_word"
    CONVERT_PDF_TO_PPT = "pdf_to_ppt"
    CONVERT_WORD_TO_PDF = "word_to_pdf"
    CONVERT_PDF_TO_JPG = "pdf_to_jpg"
    CONVERT_JPG_TO_PDF = "jpg_to_pdf"
    ROTATE = "rotate"
    WATERMARK = "watermark"
    UNLOCK = "unlock"
    PROTECT = "protect"
    OCR = "ocr"
    EDIT = "edit"
    PAGE_NUMBER = "page_number"
    SUMMARIZE = "summarize"
    TRANSLATE = "translate"

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False)
    job_type = Column(Enum(JobType), nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING)
    parameters = Column(Text)  # JSON string for job-specific parameters
    result_path = Column(String)
    error_message = Column(Text)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    file = relationship("File", back_populates="jobs")