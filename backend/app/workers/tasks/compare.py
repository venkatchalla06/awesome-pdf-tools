"""
Rich document comparison task.
Produces a self-contained HTML viewer with:
  - Side-by-side synchronized panels
  - Word-level diff (insertions green, deletions red strikethrough)
  - Prev/Next change navigation
  - Summary bar (insertions / deletions / pages changed)
  - Supports PDF, DOCX, DOC, PPTX
  - Ignore-whitespace option
  - Print-to-PDF button
"""
import difflib
import html as html_escape_mod
import os
import re
import tempfile

import fitz

from app.workers.celery_app import celery_app
from app.workers.base_task import PDFBaseTask, SyncSession
from app.db.models.job import Job, JobStatus
from app.services.storage import storage


# ── Text extraction ────────────────────────────────────────────────────────────

def _to_pdf(path: str, tmpdir: str) -> str:
    """Convert DOC/DOCX/PPTX to PDF via LibreOffice. Returns PDF path."""
    from app.workers.tasks.convert import libreoffice_convert
    return libreoffice_convert(path, tmpdir, fmt="pdf")


def _extract_pages(path: str, tmpdir: str) -> list[str]:
    """Return list of text strings (one per page) for any supported format."""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".doc", ".docx", ".pptx", ".ppt", ".odt", ".odp"):
        path = _to_pdf(path, tmpdir)
    doc = fitz.open(path)
    pages = [page.get_text("text") for page in doc]
    doc.close()
    return pages


# ── Word-level diff ────────────────────────────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    """Split text into word tokens preserving whitespace as separate tokens."""
    return re.findall(r'\S+|\s+', text)


def _word_diff_html(text_a: str, text_b: str,
                    ignore_whitespace: bool = False) -> tuple[str, str, int, int]:
    """
    Compute word-level diff between two page texts.
    Returns (html_left, html_right, insertions, deletions).
    Change spans are wrapped with <mark class="ins|del"> for navigation.
    """
    if ignore_whitespace:
        text_a = re.sub(r'\s+', ' ', text_a).strip()
        text_b = re.sub(r'\s+', ' ', text_b).strip()

    tokens_a = _tokenize(text_a)
    tokens_b = _tokenize(text_b)

    sm = difflib.SequenceMatcher(None, tokens_a, tokens_b, autojunk=False)
    opcodes = sm.get_opcodes()

    left_parts: list[str] = []
    right_parts: list[str] = []
    insertions = 0
    deletions = 0

    for tag, i1, i2, j1, j2 in opcodes:
        chunk_a = "".join(tokens_a[i1:i2])
        chunk_b = "".join(tokens_b[j1:j2])
        esc_a = html_escape_mod.escape(chunk_a)
        esc_b = html_escape_mod.escape(chunk_b)

        if tag == "equal":
            left_parts.append(esc_a)
            right_parts.append(esc_b)
        elif tag == "delete":
            left_parts.append(f'<mark class="del change">{esc_a}</mark>')
            deletions += 1
        elif tag == "insert":
            right_parts.append(f'<mark class="ins change">{esc_b}</mark>')
            insertions += 1
        elif tag == "replace":
            left_parts.append(f'<mark class="del change">{esc_a}</mark>')
            right_parts.append(f'<mark class="ins change">{esc_b}</mark>')
            deletions += 1
            insertions += 1

    return "".join(left_parts), "".join(right_parts), insertions, deletions


# ── HTML viewer builder ────────────────────────────────────────────────────────

_PAGE_TPL = """
<div class="page-row" id="page-{n}">
  <div class="page-label">Page {n}</div>
  <div class="panels">
    <div class="panel left">{left}</div>
    <div class="divider"></div>
    <div class="panel right">{right}</div>
  </div>
</div>"""


def _build_viewer(pages_a: list[str], pages_b: list[str],
                  name_a: str, name_b: str,
                  ignore_whitespace: bool) -> tuple[str, int, int, int]:
    """Build full HTML viewer. Returns (html, total_ins, total_del, pages_changed)."""

    total_ins = total_del = pages_changed = 0
    page_blocks: list[str] = []

    max_pages = max(len(pages_a), len(pages_b))
    for i in range(max_pages):
        text_a = pages_a[i] if i < len(pages_a) else ""
        text_b = pages_b[i] if i < len(pages_b) else ""
        left_html, right_html, ins, dels = _word_diff_html(
            text_a, text_b, ignore_whitespace
        )
        total_ins += ins
        total_del += dels
        if ins + dels > 0:
            pages_changed += 1
        page_blocks.append(_PAGE_TPL.format(
            n=i + 1, left=left_html, right=right_html
        ))

    pages_html = "\n".join(page_blocks)

    viewer = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Comparison: {html_escape_mod.escape(name_a)} vs {html_escape_mod.escape(name_b)}</title>
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
       background: #f0f2f5; color: #202124; }}

/* ── Top bar ── */
.topbar {{ position: sticky; top: 0; z-index: 100; background: #1a73e8;
           color: white; display: flex; align-items: center; gap: 16px;
           padding: 0 24px; height: 52px; box-shadow: 0 2px 8px rgba(0,0,0,.2); }}
.topbar h1 {{ font-size: 15px; font-weight: 600; flex: 1; white-space: nowrap;
              overflow: hidden; text-overflow: ellipsis; }}
.nav-btn {{ background: rgba(255,255,255,.15); border: none; color: white;
            padding: 6px 14px; border-radius: 20px; font-size: 13px; cursor: pointer;
            display: flex; align-items: center; gap-6px; white-space: nowrap;
            transition: background .15s; }}
.nav-btn:hover {{ background: rgba(255,255,255,.25); }}
.nav-btn:disabled {{ opacity: .4; cursor: default; }}
.change-count {{ font-size: 13px; opacity: .9; white-space: nowrap; }}
.print-btn {{ background: rgba(255,255,255,.15); border: 1px solid rgba(255,255,255,.3);
              color: white; padding: 6px 14px; border-radius: 20px; font-size: 13px;
              cursor: pointer; transition: background .15s; }}
.print-btn:hover {{ background: rgba(255,255,255,.25); }}

/* ── Summary strip ── */
.summary {{ background: white; border-bottom: 1px solid #e0e0e0;
            display: flex; align-items: center; gap: 24px; padding: 10px 24px;
            font-size: 13px; }}
.badge {{ padding: 4px 12px; border-radius: 20px; font-weight: 600; }}
.badge.ins {{ background: #e6f4ea; color: #137333; }}
.badge.del {{ background: #fce8e6; color: #c5221f; }}
.badge.pages {{ background: #e8f0fe; color: #1a73e8; }}
.doc-names {{ margin-left: auto; display: flex; gap: 16px; align-items: center; }}
.doc-name {{ font-size: 12px; padding: 3px 10px; border-radius: 4px; }}
.doc-name.left-name {{ background: #fce8e6; color: #c5221f; }}
.doc-name.right-name {{ background: #e6f4ea; color: #137333; }}

/* ── Page blocks ── */
.page-row {{ margin: 16px 24px; background: white; border-radius: 10px;
             box-shadow: 0 1px 4px rgba(0,0,0,.08); overflow: hidden; }}
.page-label {{ background: #f8f9fa; border-bottom: 1px solid #e8eaed;
               padding: 6px 16px; font-size: 11px; color: #5f6368;
               font-weight: 600; letter-spacing: .5px; text-transform: uppercase; }}
.panels {{ display: grid; grid-template-columns: 1fr 3px 1fr; min-height: 60px; }}
.panel {{ padding: 16px; font-size: 13px; line-height: 1.65;
          white-space: pre-wrap; word-break: break-word;
          font-family: "Georgia", serif; }}
.panel.left {{ background: #fffafa; }}
.panel.right {{ background: #f6fff6; }}
.divider {{ background: #e0e0e0; }}

/* ── Column headers ── */
.col-headers {{ display: grid; grid-template-columns: 1fr 3px 1fr;
                margin: 0 24px; background: white;
                border-radius: 10px 10px 0 0; border-bottom: 2px solid #e8eaed;
                margin-bottom: -16px; position: relative; z-index: 1; }}
.col-header {{ padding: 10px 16px; font-size: 12px; font-weight: 700;
               letter-spacing: .3px; text-align: center; }}
.col-header.left {{ color: #c5221f; background: #fff5f5;
                    border-radius: 10px 0 0 0; }}
.col-header.right {{ color: #137333; background: #f5fff6;
                     border-radius: 0 10px 0 0; }}

/* ── Highlights ── */
mark.del {{ background: #fad2cf; color: #c5221f; text-decoration: line-through;
             border-radius: 2px; padding: 0 1px; }}
mark.ins {{ background: #ceead6; color: #137333; border-radius: 2px; padding: 0 1px; }}
mark.current {{ outline: 3px solid #fbbc04; outline-offset: 1px; }}

/* ── No changes ── */
.no-changes {{ text-align: center; padding: 60px 24px; color: #5f6368; }}
.no-changes svg {{ width: 48px; height: 48px; margin: 0 auto 16px; display: block;
                   color: #1e8e3e; }}

/* ── Print ── */
@media print {{
  .topbar, .summary {{ position: static; }}
  .nav-btn, .print-btn {{ display: none; }}
  .page-row {{ box-shadow: none; border: 1px solid #ccc; page-break-inside: avoid; }}
}}
</style>
</head>
<body>

<div class="topbar">
  <h1>&#128196; {html_escape_mod.escape(name_a)} &nbsp;vs&nbsp; {html_escape_mod.escape(name_b)}</h1>
  <button class="nav-btn" id="btn-prev" onclick="navigate(-1)" disabled>&#8592; Prev</button>
  <span class="change-count" id="nav-label">0 / 0</span>
  <button class="nav-btn" id="btn-next" onclick="navigate(1)" disabled>Next &#8594;</button>
  <button class="print-btn" onclick="window.print()">&#128438; Export PDF</button>
</div>

<div class="summary">
  <span class="badge ins">+ {total_ins} insertion{'s' if total_ins != 1 else ''}</span>
  <span class="badge del">&#8722; {total_del} deletion{'s' if total_del != 1 else ''}</span>
  <span class="badge pages">&#128196; {pages_changed} page{'s' if pages_changed != 1 else ''} changed</span>
  <div class="doc-names">
    <span class="doc-name left-name">&#9646; {html_escape_mod.escape(name_a)}</span>
    <span class="doc-name right-name">&#9646; {html_escape_mod.escape(name_b)}</span>
  </div>
</div>

<div class="col-headers">
  <div class="col-header left">{html_escape_mod.escape(name_a)}</div>
  <div></div>
  <div class="col-header right">{html_escape_mod.escape(name_b)}</div>
</div>

{"".join(page_blocks) if total_ins + total_del > 0 else '''
<div class="no-changes">
  <svg fill="none" viewBox="0 0 24 24"><path stroke="currentColor" stroke-width="2"
    stroke-linecap="round" d="M5 13l4 4L19 7"/></svg>
  <p style="font-size:18px;font-weight:600;">No differences found</p>
  <p style="margin-top:8px">The two documents appear to be identical.</p>
</div>
'''}

<script>
const changes = Array.from(document.querySelectorAll('mark.change'));
let cur = -1;
document.getElementById('nav-label').textContent =
  changes.length ? '0 / ' + changes.length : 'No changes';
if (changes.length) {{
  document.getElementById('btn-next').disabled = false;
}}

function navigate(dir) {{
  if (!changes.length) return;
  if (cur >= 0) changes[cur].classList.remove('current');
  cur = Math.max(0, Math.min(changes.length - 1, cur + dir));
  changes[cur].classList.add('current');
  changes[cur].scrollIntoView({{ behavior: 'smooth', block: 'center' }});
  document.getElementById('nav-label').textContent = (cur + 1) + ' / ' + changes.length;
  document.getElementById('btn-prev').disabled = cur === 0;
  document.getElementById('btn-next').disabled = cur === changes.length - 1;
}}
// Auto-jump to first change
if (changes.length) navigate(1);
</script>
</body>
</html>"""

    return viewer, total_ins, total_del, pages_changed


# ── Celery task ────────────────────────────────────────────────────────────────

@celery_app.task(
    bind=True, base=PDFBaseTask,
    name="app.workers.tasks.compare.compare_docs_task",
    max_retries=1, soft_time_limit=300,
)
def compare_docs_task(self, job_id: str):
    self.update_job(job_id, status=JobStatus.PROCESSING, progress=10)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        input_keys = job.input_keys
        options = dict(job.options)

    if len(input_keys) < 2:
        raise ValueError("Two input files are required for comparison")

    key_a, key_b = input_keys[0], input_keys[1]
    name_a = options.get("name_a", "Document A")
    name_b = options.get("name_b", "Document B")
    ignore_whitespace = bool(options.get("ignore_whitespace", False))

    with tempfile.TemporaryDirectory() as tmpdir:
        ext_a = os.path.splitext(key_a)[1].lower() or ".pdf"
        ext_b = os.path.splitext(key_b)[1].lower() or ".pdf"

        path_a = os.path.join(tmpdir, f"doc_a{ext_a}")
        path_b = os.path.join(tmpdir, f"doc_b{ext_b}")

        storage.download_to_temp(key_a, path_a)
        self.update_job(job_id, progress=20)
        storage.download_to_temp(key_b, path_b)
        self.update_job(job_id, progress=35)

        pages_a = _extract_pages(path_a, tmpdir)
        self.update_job(job_id, progress=55)
        pages_b = _extract_pages(path_b, tmpdir)
        self.update_job(job_id, progress=70)

        html, ins, dels, pages_changed = _build_viewer(
            pages_a, pages_b, name_a, name_b, ignore_whitespace
        )
        self.update_job(job_id, progress=88)

        output_path = os.path.join(tmpdir, "comparison.html")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        output_key = f"results/{job_id}/comparison.html"
        storage.upload_from_temp(output_path, output_key, content_type="text/html")

    with SyncSession() as session:
        job = session.get(Job, job_id)
        job.status = JobStatus.COMPLETED
        job.output_key = output_key
        job.progress = 100
        job.options = {
            **options,
            "output_filename": "comparison.html",
            "insertions": ins,
            "deletions": dels,
            "pages_changed": pages_changed,
        }
        session.commit()

    return output_key
