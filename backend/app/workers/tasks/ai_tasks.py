import os
import tempfile
import json

import fitz
import httpx

from app.workers.celery_app import celery_app
from app.workers.base_task import PDFBaseTask, SyncSession
from app.db.models.job import Job, JobStatus
from app.services.storage import storage
from app.config import get_settings

settings = get_settings()


def extract_pdf_text(pdf_path: str, max_chars: int = 50000) -> str:
    doc = fitz.open(pdf_path)
    texts = []
    for page in doc:
        texts.append(page.get_text())
    doc.close()
    full = "\n\n".join(texts)
    return full[:max_chars]


def call_ollama(prompt: str, model: str = "gemma4:latest") -> str:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    with httpx.Client(timeout=120) as client:
        resp = client.post(f"{settings.OLLAMA_URL}/api/chat", json=payload)
        resp.raise_for_status()
    return resp.json()["message"]["content"]


def call_openai(prompt: str, model: str = "gpt-4o-mini") -> str:
    import openai
    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content


def call_llm(prompt: str) -> str:
    if settings.OPENAI_API_KEY:
        return call_openai(prompt)
    return call_ollama(prompt)


# ── AI Summarize ───────────────────────────────────────────────────────────

@celery_app.task(
    bind=True, base=PDFBaseTask,
    name="app.workers.tasks.ai_tasks.summarize_task",
    max_retries=1, soft_time_limit=300,
)
def summarize_task(self, job_id: str):
    self.update_job(job_id, status=JobStatus.PROCESSING, progress=10)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        input_key = job.input_keys[0]
        options = dict(job.options)

    style = options.get("style", "bullet")  # "bullet" | "paragraph" | "executive"
    language = options.get("output_language", "English")

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pdf")
        storage.download_to_temp(input_key, input_path)
        self.update_job(job_id, progress=20)

        text = extract_pdf_text(input_path)
        if not text.strip():
            raise ValueError("PDF contains no extractable text. Run OCR first.")

        self.update_job(job_id, progress=40)

        style_instruction = {
            "bullet": "Provide a bullet-point summary (5-10 key points).",
            "paragraph": "Write a 2-3 paragraph summary.",
            "executive": "Write an executive summary with: Overview, Key Findings, and Recommendations.",
        }.get(style, "Summarize the document.")

        prompt = (
            f"You are a professional document analyst. {style_instruction}\n"
            f"Language: {language}\n\n"
            f"Document text:\n{text}"
        )

        summary = call_llm(prompt)
        self.update_job(job_id, progress=85)

        # Save summary as .txt
        output_path = os.path.join(tmpdir, "summary.txt")
        with open(output_path, "w") as f:
            f.write(summary)

        output_key = f"results/{job_id}/summary.txt"
        storage.upload_from_temp(output_path, output_key, content_type="text/plain")

    with SyncSession() as session:
        job = session.get(Job, job_id)
        job.status = JobStatus.COMPLETED
        job.output_key = output_key
        job.progress = 100
        job.options = {**options, "output_filename": "summary.txt", "summary_preview": summary[:500]}
        session.commit()

    return output_key


# ── AI Translate ───────────────────────────────────────────────────────────

@celery_app.task(
    bind=True, base=PDFBaseTask,
    name="app.workers.tasks.ai_tasks.translate_task",
    max_retries=1, soft_time_limit=600,
)
def translate_task(self, job_id: str):
    self.update_job(job_id, status=JobStatus.PROCESSING, progress=5)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        input_key = job.input_keys[0]
        options = dict(job.options)

    target_lang = options.get("target_language", "Spanish")

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pdf")
        storage.download_to_temp(input_key, input_path)
        self.update_job(job_id, progress=15)

        # Translate page by page and write a new PDF
        doc = fitz.open(input_path)
        total = len(doc)
        translated_pages = []

        for i, page in enumerate(doc):
            page_text = page.get_text().strip()
            if not page_text:
                translated_pages.append("")
                continue

            prompt = (
                f"Translate the following text to {target_lang}. "
                f"Preserve paragraph structure. Output only the translation.\n\n{page_text[:3000]}"
            )
            translated = call_llm(prompt)
            translated_pages.append(translated)
            self.update_job(job_id, progress=15 + int((i + 1) / total * 65))

        doc.close()

        # Build translated PDF using reportlab
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm

        output_path = os.path.join(tmpdir, "translated.pdf")
        doc_rl = SimpleDocTemplate(output_path, pagesize=A4,
                                   leftMargin=2*cm, rightMargin=2*cm,
                                   topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        story = []
        for i, text in enumerate(translated_pages):
            if text:
                for para in text.split("\n"):
                    if para.strip():
                        story.append(Paragraph(para, styles["Normal"]))
                        story.append(Spacer(1, 6))
            if i < total - 1:
                from reportlab.platypus import PageBreak
                story.append(PageBreak())

        doc_rl.build(story)
        self.update_job(job_id, progress=95)

        output_key = f"results/{job_id}/translated.pdf"
        storage.upload_from_temp(output_path, output_key)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        job.status = JobStatus.COMPLETED
        job.output_key = output_key
        job.progress = 100
        job.options = {**options, "output_filename": "translated.pdf"}
        session.commit()

    return output_key
