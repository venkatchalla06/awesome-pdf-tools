"""
Document comparison API — DocCompare Pro integrated into PDFKit.

POST /api/v1/compare          — upload two files, diff, store in Redis
GET  /api/v1/compare/{id}     — full diff result
PUT  /api/v1/compare/{id}/notes
GET  /api/v1/compare/{id}/notes
GET  /api/v1/compare/{id}/export/csv
GET  /api/v1/compare/{id}/export/docx
"""
import os
import io
import csv
import uuid
import json
import asyncio
import tempfile

import aiofiles
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from typing import Dict

from app.services.differ import multi_granularity_compare
from app.services.extractor import extract_text
from app.services.exporter import export_docx
from app.services.redis_compare import get_redis, RESULT_TTL, UPLOAD_DIR, MAX_FILE_SIZE

router = APIRouter(prefix="/compare", tags=["compare"])

ALLOWED_EXT = {".pdf", ".docx", ".doc", ".txt", ".xlsx", ".html", ".htm", ".md"}

os.makedirs(UPLOAD_DIR, exist_ok=True)


def _ext(filename: str) -> str:
    return os.path.splitext(filename or "")[-1].lower()


def _delete(path: str):
    try:
        os.unlink(path)
    except Exception:
        pass


async def _save_temp(data: bytes, suffix: str) -> str:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    fd, path = tempfile.mkstemp(suffix=suffix, dir=UPLOAD_DIR)
    os.close(fd)
    async with aiofiles.open(path, "wb") as f:
        await f.write(data)
    return path


@router.post("", summary="Compare two documents")
async def compare_documents(
    background_tasks: BackgroundTasks,
    file_a: UploadFile = File(...),
    file_b: UploadFile = File(...),
):
    data_a = await file_a.read()
    data_b = await file_b.read()

    if len(data_a) > MAX_FILE_SIZE or len(data_b) > MAX_FILE_SIZE:
        raise HTTPException(400, "File exceeds 50 MB limit")

    ext_a = _ext(file_a.filename)
    ext_b = _ext(file_b.filename)
    if ext_a not in ALLOWED_EXT or ext_b not in ALLOWED_EXT:
        raise HTTPException(400, f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXT)}")

    path_a = await _save_temp(data_a, ext_a)
    path_b = await _save_temp(data_b, ext_b)

    try:
        loop = asyncio.get_event_loop()
        text_a = await loop.run_in_executor(None, extract_text, path_a, ext_a)
        text_b = await loop.run_in_executor(None, extract_text, path_b, ext_b)
    finally:
        background_tasks.add_task(_delete, path_a)
        background_tasks.add_task(_delete, path_b)

    diff = await asyncio.get_event_loop().run_in_executor(
        None, multi_granularity_compare, text_a, text_b
    )

    cid = str(uuid.uuid4())
    payload = {
        "id": cid,
        "status": "completed",
        "file_a_name": file_a.filename or "original",
        "file_b_name": file_b.filename or "revised",
        "original_spans": diff["original_spans"],
        "revised_spans": diff["revised_spans"],
        "summary": diff["summary"],
    }

    redis = await get_redis()
    await redis.setex(f"comparison:{cid}", RESULT_TTL, json.dumps(payload))

    return JSONResponse({"id": cid, "status": "completed", "summary": diff["summary"]})


async def _load(cid: str) -> dict:
    redis = await get_redis()
    raw = await redis.get(f"comparison:{cid}")
    if not raw:
        raise HTTPException(404, "Comparison not found or expired")
    return json.loads(raw)


async def _load_notes(cid: str) -> dict:
    redis = await get_redis()
    raw = await redis.get(f"notes:{cid}")
    return json.loads(raw) if raw else {}


@router.get("/{cid}", summary="Get full comparison result")
async def get_result(cid: str):
    data = await _load(cid)
    data["notes"] = await _load_notes(cid)
    return JSONResponse(data)


class NotesPayload(BaseModel):
    notes: Dict[str, dict]


@router.put("/{cid}/notes")
async def save_notes(cid: str, payload: NotesPayload):
    await _load(cid)
    redis = await get_redis()
    await redis.setex(f"notes:{cid}", RESULT_TTL, json.dumps(payload.notes))
    return {"status": "saved"}


@router.get("/{cid}/notes")
async def get_notes(cid: str):
    await _load(cid)
    return JSONResponse(await _load_notes(cid))


@router.get("/{cid}/export/csv")
async def export_csv(cid: str):
    data = await _load(cid)
    notes = await _load_notes(cid)
    CHANGE_TYPES = {"insert", "delete", "replace", "move_from", "move_to"}

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Change #", "Type", "Side", "Preview (80 chars)", "Context", "Note", "Tag"])
    n = 0
    for idx, span in enumerate(data["original_spans"]):
        if span["type"] in CHANGE_TYPES and span["text"].strip():
            n += 1
            nd = notes.get(str(idx), {})
            w.writerow([n, span["type"], "original", span["text"][:80].replace("\n", " "),
                        span.get("context", "")[:80], nd.get("note", ""), nd.get("tag", "")])
    for idx, span in enumerate(data["revised_spans"]):
        if span["type"] in CHANGE_TYPES and span["text"].strip():
            n += 1
            nd = notes.get(f"r{idx}", {})
            w.writerow([n, span["type"], "revised", span["text"][:80].replace("\n", " "),
                        span.get("context", "")[:80], nd.get("note", ""), nd.get("tag", "")])

    return Response(content=buf.getvalue().encode("utf-8-sig"), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="changes_{cid[:8]}.csv"'})


@router.get("/{cid}/export/docx")
async def export_docx_endpoint(cid: str):
    data = await _load(cid)
    docx_bytes = export_docx(data["original_spans"], data["revised_spans"])
    return Response(content=docx_bytes,
                    media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f'attachment; filename="redline_{cid[:8]}.docx"'})
