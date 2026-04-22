"""
Text extraction from supported document formats.
PDF: pdfplumber (primary) → PyMuPDF (fallback)
DOCX/DOC: python-docx
XLSX: openpyxl
HTML: html.parser
MD: markdown → html.parser
TXT: raw read
"""
import re
import unicodedata
from pathlib import Path


def extract_text(filepath: str, ext: str) -> str:
    ext = ext.lower()
    if ext == ".pdf":
        return _extract_pdf(filepath)
    elif ext in (".docx", ".doc"):
        return _extract_docx(filepath)
    elif ext == ".xlsx":
        return _extract_xlsx(filepath)
    elif ext in (".html", ".htm"):
        return _extract_html(filepath)
    elif ext == ".md":
        return _extract_md(filepath)
    else:
        return _extract_txt(filepath)


def _extract_pdf(path: str) -> str:
    try:
        import pdfplumber
        pages = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages.append(text)
        return _normalize("\n".join(pages))
    except Exception:
        return _pdf_fallback(path)


def _pdf_fallback(path: str) -> str:
    import fitz  # PyMuPDF
    doc = fitz.open(path)
    pages = [page.get_text() for page in doc]
    doc.close()
    return _normalize("\n".join(pages))


def _extract_docx(path: str) -> str:
    from docx import Document
    doc = Document(path)
    paragraphs = [p.text for p in doc.paragraphs]
    return _normalize("\n".join(paragraphs))


def _extract_xlsx(path: str) -> str:
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    lines = []
    for sheet in wb.worksheets:
        lines.append(f"[Sheet: {sheet.title}]")
        for row in sheet.iter_rows(values_only=True):
            cells = [str(c) if c is not None else "" for c in row]
            lines.append("\t".join(cells))
    return _normalize("\n".join(lines))


def _extract_html(path: str) -> str:
    from html.parser import HTMLParser

    class TextParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.parts = []
            self._skip = False

        def handle_starttag(self, tag, attrs):
            if tag in ("script", "style"):
                self._skip = True

        def handle_endtag(self, tag):
            if tag in ("script", "style"):
                self._skip = False

        def handle_data(self, data):
            if not self._skip:
                self.parts.append(data)

    with open(path, encoding="utf-8", errors="replace") as f:
        raw = f.read()
    p = TextParser()
    p.feed(raw)
    return _normalize(" ".join(p.parts))


def _extract_md(path: str) -> str:
    import markdown
    from html.parser import HTMLParser

    class StripHTML(HTMLParser):
        def __init__(self):
            super().__init__()
            self.text = []

        def handle_data(self, data):
            self.text.append(data)

    with open(path, encoding="utf-8", errors="replace") as f:
        raw = f.read()
    html = markdown.markdown(raw)
    p = StripHTML()
    p.feed(html)
    return _normalize(" ".join(p.text))


def _extract_txt(path: str) -> str:
    with open(path, encoding="utf-8", errors="replace") as f:
        return _normalize(f.read())


def _normalize(text: str) -> str:
    # Unify Unicode
    text = unicodedata.normalize("NFC", text)
    # Collapse horizontal whitespace but preserve newlines
    text = re.sub(r"[ \t]+", " ", text)
    # Collapse more than 2 consecutive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
