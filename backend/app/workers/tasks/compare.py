"""
Visual document comparison task — Draftable-style.
Renders each PDF page as an image and overlays word-level highlights:
  - Red semi-transparent boxes over deleted/changed words (left panel)
  - Green semi-transparent boxes over inserted/changed words (right panel)
Produces a self-contained HTML file with:
  - Side-by-side synchronized-scroll page panels
  - Sticky toolbar: prev/next change, summary badges, export button
  - Supports PDF, DOCX, DOC, PPTX (non-PDF converted via LibreOffice)
"""
import base64
import difflib
import html as html_escape_mod
import os
import re
import tempfile
from typing import NamedTuple

import fitz

from app.workers.celery_app import celery_app
from app.workers.base_task import PDFBaseTask, SyncSession
from app.db.models.job import Job, JobStatus
from app.services.storage import storage

RENDER_DPI = 120  # balance between quality and file size


# ── Helpers ────────────────────────────────────────────────────────────────────

def _to_pdf(path: str, tmpdir: str) -> str:
    from app.workers.tasks.convert import libreoffice_convert
    return libreoffice_convert(path, tmpdir, fmt="pdf")


def _ensure_pdf(path: str, tmpdir: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in (".doc", ".docx", ".pptx", ".ppt", ".odt", ".odp"):
        return _to_pdf(path, tmpdir)
    return path


class PageData(NamedTuple):
    img_b64: str
    width: int
    height: int
    words: list   # [(x0,y0,x1,y1,word), ...]


def _extract_page_data(pdf_path: str) -> list[PageData]:
    scale = RENDER_DPI / 72.0
    mat = fitz.Matrix(scale, scale)
    doc = fitz.open(pdf_path)
    pages = []
    for page in doc:
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_b64 = base64.b64encode(pix.tobytes("png")).decode()
        raw_words = page.get_text("words")  # (x0,y0,x1,y1,word,block,line,wn)
        words = [(w[0], w[1], w[2], w[3], w[4]) for w in raw_words]
        pages.append(PageData(img_b64, pix.width, pix.height, words))
    doc.close()
    return pages


# ── Diff engine ────────────────────────────────────────────────────────────────

def _diff_pages(page_a: PageData, page_b: PageData, ignore_ws: bool):
    """
    Returns (del_boxes, ins_boxes, n_changes) where each box is
    {"x","y","w","h"} in rendered pixels.
    """
    scale_a = RENDER_DPI / 72.0
    scale_b = RENDER_DPI / 72.0

    def normalise(w):
        return re.sub(r'\s+', '', w).lower() if ignore_ws else w.lower()

    words_a = [w[4] for w in page_a.words]
    words_b = [w[4] for w in page_b.words]

    sm = difflib.SequenceMatcher(
        None,
        [normalise(w) for w in words_a],
        [normalise(w) for w in words_b],
        autojunk=False,
    )

    del_idx: set[int] = set()
    ins_idx: set[int] = set()
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("delete", "replace"):
            del_idx.update(range(i1, i2))
        if tag in ("insert", "replace"):
            ins_idx.update(range(j1, j2))

    def boxes(words, indices, scale):
        result = []
        for i in sorted(indices):
            x0, y0, x1, y1, _ = words[i]
            result.append({
                "x": round(x0 * scale),
                "y": round(y0 * scale),
                "w": max(4, round((x1 - x0) * scale)),
                "h": max(4, round((y1 - y0) * scale)),
            })
        return result

    del_boxes = boxes(page_a.words, del_idx, scale_a)
    ins_boxes = boxes(page_b.words, ins_idx, scale_b)
    return del_boxes, ins_boxes, len(del_idx) + len(ins_idx)


# ── HTML builder ───────────────────────────────────────────────────────────────

def _box_html(boxes: list[dict], cls: str) -> str:
    return "".join(
        f'<div class="hl {cls}" style="left:{b["x"]}px;top:{b["y"]}px;'
        f'width:{b["w"]}px;height:{b["h"]}px"></div>'
        for b in boxes
    )


def _build_viewer(
    pages_a: list[PageData],
    pages_b: list[PageData],
    name_a: str,
    name_b: str,
    ignore_ws: bool,
) -> tuple[str, int, int, int]:

    total_del = total_ins = pages_changed = 0
    page_blocks: list[str] = []

    max_pages = max(len(pages_a), len(pages_b))

    empty_page = PageData("", 794, 1123, [])  # A4 fallback

    for i in range(max_pages):
        pa = pages_a[i] if i < len(pages_a) else empty_page
        pb = pages_b[i] if i < len(pages_b) else empty_page

        del_boxes, ins_boxes, n_ch = _diff_pages(pa, pb, ignore_ws)
        total_del += len(del_boxes)
        total_ins += len(ins_boxes)
        if n_ch > 0:
            pages_changed += 1

        left_boxes_html = _box_html(del_boxes, "del")
        right_boxes_html = _box_html(ins_boxes, "ins")

        left_img = (
            f'<img src="data:image/png;base64,{pa.img_b64}" '
            f'style="width:{pa.width}px;height:{pa.height}px;display:block">'
        ) if pa.img_b64 else (
            f'<div style="width:{pa.width}px;height:{pa.height}px;'
            f'background:#f8f9fa;display:flex;align-items:center;justify-content:center;'
            f'font-size:13px;color:#9aa0a6">(no page)</div>'
        )

        right_img = (
            f'<img src="data:image/png;base64,{pb.img_b64}" '
            f'style="width:{pb.width}px;height:{pb.height}px;display:block">'
        ) if pb.img_b64 else (
            f'<div style="width:{pb.width}px;height:{pb.height}px;'
            f'background:#f8f9fa;display:flex;align-items:center;justify-content:center;'
            f'font-size:13px;color:#9aa0a6">(no page)</div>'
        )

        changed_cls = " changed" if n_ch > 0 else ""
        page_blocks.append(f"""
<div class="page-pair{changed_cls}" id="page-{i+1}">
  <div class="page-label">Page {i+1}{' <span class="change-dot"></span>' if n_ch > 0 else ''}</div>
  <div class="panels">
    <div class="panel left-panel">
      <div class="page-canvas" style="width:{pa.width}px;height:{pa.height}px">
        {left_img}
        {left_boxes_html}
      </div>
    </div>
    <div class="gutter"></div>
    <div class="panel right-panel">
      <div class="page-canvas" style="width:{pb.width}px;height:{pb.height}px">
        {right_img}
        {right_boxes_html}
      </div>
    </div>
  </div>
</div>""")

    name_a_esc = html_escape_mod.escape(name_a)
    name_b_esc = html_escape_mod.escape(name_b)

    no_diff_html = """
<div class="no-changes">
  <svg fill="none" viewBox="0 0 24 24" width="48" height="48">
    <path stroke="#1e8e3e" stroke-width="2" stroke-linecap="round" d="M5 13l4 4L19 7"/>
  </svg>
  <p class="nc-title">Documents are identical</p>
  <p class="nc-sub">No differences were found between the two documents.</p>
</div>""" if total_del + total_ins == 0 else ""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{name_a_esc} vs {name_b_esc}</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html,body{{height:100%;overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;background:#f0f2f5;color:#202124}}

/* ── Toolbar ── */
#toolbar{{position:fixed;top:0;left:0;right:0;z-index:200;height:52px;
  background:#1a1f36;display:flex;align-items:center;gap:10px;padding:0 16px;
  box-shadow:0 2px 8px rgba(0,0,0,.35)}}
#toolbar .title{{font-size:14px;font-weight:600;color:#fff;flex:1;overflow:hidden;
  white-space:nowrap;text-overflow:ellipsis}}
.tbtn{{background:rgba(255,255,255,.12);border:none;color:#fff;height:32px;padding:0 14px;
  border-radius:16px;font-size:13px;cursor:pointer;display:flex;align-items:center;gap:6px;
  white-space:nowrap;transition:background .15s}}
.tbtn:hover{{background:rgba(255,255,255,.22)}}
.tbtn:disabled{{opacity:.35;cursor:default}}
.badge{{padding:4px 12px;border-radius:12px;font-size:12px;font-weight:700;white-space:nowrap}}
.badge.del{{background:#fce8e6;color:#c5221f}}
.badge.ins{{background:#e6f4ea;color:#137333}}
.badge.pg{{background:#e8f0fe;color:#1a73e8}}
.sep{{width:1px;height:22px;background:rgba(255,255,255,.18)}}

/* ── Column headers ── */
#col-headers{{position:fixed;top:52px;left:0;right:0;z-index:199;
  display:grid;grid-template-columns:1fr 6px 1fr;background:#fff;
  border-bottom:2px solid #e8eaed;box-shadow:0 1px 4px rgba(0,0,0,.08)}}
.col-hdr{{padding:8px 20px;font-size:12px;font-weight:700;text-align:center;
  letter-spacing:.3px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.col-hdr.lh{{color:#c5221f;background:#fff5f5}}
.col-hdr.rh{{color:#137333;background:#f5fff6}}

/* ── Scroll area ── */
#scroll-area{{position:fixed;top:86px;left:0;right:0;bottom:0;overflow-y:scroll;
  overflow-x:hidden}}

/* ── Page pair ── */
.page-pair{{margin:16px 20px;background:#fff;border-radius:10px;
  overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08)}}
.page-label{{background:#f8f9fa;border-bottom:1px solid #e8eaed;padding:6px 16px;
  font-size:11px;font-weight:700;color:#5f6368;text-transform:uppercase;
  letter-spacing:.5px;display:flex;align-items:center;gap:8px}}
.change-dot{{display:inline-block;width:7px;height:7px;border-radius:50%;
  background:#fbbc04}}
.panels{{display:grid;grid-template-columns:1fr 6px 1fr;align-items:start}}
.panel{{overflow-x:auto;padding:12px 16px}}
.gutter{{background:#e8eaed;align-self:stretch}}

/* ── Page canvas ── */
.page-canvas{{position:relative;display:inline-block;max-width:100%}}
.page-canvas img{{max-width:100%;height:auto;display:block}}

/* ── Highlights ── */
.hl{{position:absolute;pointer-events:none;border-radius:2px}}
.hl.del{{background:rgba(217,48,37,.25);outline:1.5px solid rgba(217,48,37,.6)}}
.hl.ins{{background:rgba(30,142,62,.22);outline:1.5px solid rgba(30,142,62,.55)}}
.hl.current{{outline:3px solid #fbbc04!important;background:rgba(251,188,4,.3)!important;z-index:10}}

/* ── No changes ── */
.no-changes{{text-align:center;padding:80px 24px;color:#5f6368}}
.nc-title{{font-size:20px;font-weight:600;color:#202124;margin-top:16px}}
.nc-sub{{font-size:14px;margin-top:8px}}

/* ── Print ── */
@media print{{
  html,body{{overflow:visible;height:auto}}
  #toolbar,#col-headers{{position:static}}
  #scroll-area{{position:static;overflow:visible}}
  .page-pair{{page-break-inside:avoid;box-shadow:none;border:1px solid #ccc}}
}}
</style>
</head>
<body>

<div id="toolbar">
  <span class="title">&#128196; {name_a_esc} &nbsp;&#8644;&nbsp; {name_b_esc}</span>
  <span class="badge del">&#8722; {total_del} deletion{'s' if total_del != 1 else ''}</span>
  <span class="badge ins">+ {total_ins} insertion{'s' if total_ins != 1 else ''}</span>
  <span class="badge pg">&#128196; {pages_changed} page{'s' if pages_changed != 1 else ''} changed</span>
  <div class="sep"></div>
  <button class="tbtn" id="btn-prev" onclick="navigate(-1)" disabled>&#8592; Prev</button>
  <span style="font-size:13px;color:rgba(255,255,255,.8)" id="nav-lbl">0 / 0</span>
  <button class="tbtn" id="btn-next" onclick="navigate(1)">Next &#8594;</button>
  <div class="sep"></div>
  <button class="tbtn" onclick="window.print()">&#128438; Export PDF</button>
</div>

<div id="col-headers">
  <div class="col-hdr lh">{name_a_esc}</div>
  <div></div>
  <div class="col-hdr rh">{name_b_esc}</div>
</div>

<div id="scroll-area">
{"".join(page_blocks)}
{no_diff_html}
<div style="height:40px"></div>
</div>

<script>
// scale highlight boxes to match CSS-scaled images
function scaleBoxes() {{
  document.querySelectorAll('.page-canvas').forEach(function(canvas) {{
    var img = canvas.querySelector('img');
    if (!img) return;
    var natW = img.naturalWidth || img.width || 1;
    var dispW = img.getBoundingClientRect().width || img.clientWidth || natW;
    var ratio = dispW / natW;
    if (Math.abs(ratio - 1) < 0.01) return;
    canvas.querySelectorAll('.hl').forEach(function(hl) {{
      hl.style.left   = (parseFloat(hl.style.left)   * ratio) + 'px';
      hl.style.top    = (parseFloat(hl.style.top)    * ratio) + 'px';
      hl.style.width  = (parseFloat(hl.style.width)  * ratio) + 'px';
      hl.style.height = (parseFloat(hl.style.height) * ratio) + 'px';
    }});
  }});
}}
window.addEventListener('load', scaleBoxes);
window.addEventListener('resize', scaleBoxes);

// change navigation
var changes = [];
var cur = -1;
function collectChanges() {{
  changes = Array.from(document.querySelectorAll('.hl'));
  var lbl = document.getElementById('nav-lbl');
  lbl.textContent = changes.length ? '0 / ' + changes.length : 'No changes';
  document.getElementById('btn-next').disabled = !changes.length;
}}
window.addEventListener('load', function() {{
  collectChanges();
  if (changes.length) navigate(1);
}});
function navigate(dir) {{
  if (!changes.length) return;
  if (cur >= 0) changes[cur].classList.remove('current');
  cur = Math.max(0, Math.min(changes.length - 1, cur + dir));
  changes[cur].classList.add('current');
  changes[cur].scrollIntoView({{behavior:'smooth',block:'center'}});
  document.getElementById('nav-lbl').textContent = (cur+1) + ' / ' + changes.length;
  document.getElementById('btn-prev').disabled = cur === 0;
  document.getElementById('btn-next').disabled = cur === changes.length - 1;
}}
</script>
</body>
</html>"""

    return html, total_del, total_ins, pages_changed


# ── Celery task ────────────────────────────────────────────────────────────────

@celery_app.task(
    bind=True, base=PDFBaseTask,
    name="app.workers.tasks.compare.compare_docs_task",
    max_retries=1, soft_time_limit=600,
)
def compare_docs_task(self, job_id: str):
    self.update_job(job_id, status=JobStatus.PROCESSING, progress=5)

    with SyncSession() as session:
        job = session.get(Job, job_id)
        input_keys = job.input_keys
        options = dict(job.options)

    if len(input_keys) < 2:
        raise ValueError("Two input files are required for comparison")

    key_a, key_b = input_keys[0], input_keys[1]
    name_a = options.get("name_a", "Document A")
    name_b = options.get("name_b", "Document B")
    ignore_ws = bool(options.get("ignore_whitespace", False))

    with tempfile.TemporaryDirectory() as tmpdir:
        ext_a = os.path.splitext(key_a)[1].lower() or ".pdf"
        ext_b = os.path.splitext(key_b)[1].lower() or ".pdf"

        path_a = os.path.join(tmpdir, f"doc_a{ext_a}")
        path_b = os.path.join(tmpdir, f"doc_b{ext_b}")

        storage.download_to_temp(key_a, path_a)
        self.update_job(job_id, progress=15)
        storage.download_to_temp(key_b, path_b)
        self.update_job(job_id, progress=25)

        pdf_a = _ensure_pdf(path_a, tmpdir)
        self.update_job(job_id, progress=35)
        pdf_b = _ensure_pdf(path_b, tmpdir)
        self.update_job(job_id, progress=45)

        pages_a = _extract_page_data(pdf_a)
        self.update_job(job_id, progress=60)
        pages_b = _extract_page_data(pdf_b)
        self.update_job(job_id, progress=75)

        html, dels, ins, pages_changed = _build_viewer(
            pages_a, pages_b, name_a, name_b, ignore_ws
        )
        self.update_job(job_id, progress=90)

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
            "deletions": dels,
            "insertions": ins,
            "pages_changed": pages_changed,
        }
        session.commit()

    return output_key
