"""
Comparison engine — difflib-based word-level diff with move detection.
Returns structured spans for the frontend renderer.

Change types:
  equal   — unchanged text
  insert  — text added in revised
  delete  — text removed from original
  replace — text modified (word-level)
  move    — paragraph relocated (detected separately, not counted as insert+delete)
"""
import difflib
import re
from dataclasses import dataclass, asdict
from typing import List


@dataclass
class Span:
    type: str          # "equal"|"insert"|"delete"|"replace"|"move_from"|"move_to"
    text: str
    offset: int
    length: int
    context: str = ""
    move_id: int = -1  # links move_from ↔ move_to pairs


@dataclass
class DiffResult:
    original_spans: List[dict]
    revised_spans: List[dict]
    summary: dict


# ── helpers ──────────────────────────────────────────────────────────────────

def _word_split(text: str) -> List[str]:
    return re.split(r"(\s+)", text)


def _para_split(text: str) -> List[str]:
    return [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]


def _context(tokens: List[str], idx: int, window: int = 5) -> str:
    start = max(0, idx - window)
    end = min(len(tokens), idx + window + 1)
    return "".join(tokens[start:end]).strip()[:120]


# ── move detection ────────────────────────────────────────────────────────────

def _find_moved_paragraphs(text_a: str, text_b: str):
    """
    Return sets of paragraph texts that appear in both docs but at different positions.
    A paragraph is 'moved' if it exists verbatim in both but the surrounding context differs.
    """
    paras_a = _para_split(text_a)
    paras_b = _para_split(text_b)

    # Only consider paragraphs that are at least 30 chars (avoid false positives on short lines)
    set_a = {p for p in paras_a if len(p) >= 30}
    set_b = {p for p in paras_b if len(p) >= 30}
    common = set_a & set_b

    # A paragraph is truly moved if its ORDER changed
    moved = set()
    idx_a = {p: i for i, p in enumerate(paras_a) if p in common}
    idx_b = {p: i for i, p in enumerate(paras_b) if p in common}

    for p in common:
        if p in idx_a and p in idx_b:
            # Order ratio — if relative position differs significantly it's a move
            ratio_a = idx_a[p] / max(len(paras_a), 1)
            ratio_b = idx_b[p] / max(len(paras_b), 1)
            if abs(ratio_a - ratio_b) > 0.15:
                moved.add(p)

    return moved


# ── core diff ─────────────────────────────────────────────────────────────────

def compare(text_a: str, text_b: str, granularity: str = "word") -> DiffResult:
    moved_paras = _find_moved_paragraphs(text_a, text_b)

    if granularity == "char":
        seq_a, seq_b = list(text_a), list(text_b)
    elif granularity == "sentence":
        seq_a = re.split(r"(?<=[.!?])\s+", text_a)
        seq_b = re.split(r"(?<=[.!?])\s+", text_b)
    elif granularity == "paragraph":
        seq_a = text_a.split("\n\n")
        seq_b = text_b.split("\n\n")
    else:
        seq_a = _word_split(text_a)
        seq_b = _word_split(text_b)

    matcher = difflib.SequenceMatcher(None, seq_a, seq_b, autojunk=False)
    opcodes = matcher.get_opcodes()

    orig_spans: List[dict] = []
    rev_spans:  List[dict] = []
    summary = {"additions": 0, "deletions": 0, "modifications": 0, "moves": 0, "total": 0}

    orig_offset = 0
    rev_offset  = 0
    move_counter = 0

    for tag, i1, i2, j1, j2 in opcodes:
        orig_chunk = "".join(seq_a[i1:i2])
        rev_chunk  = "".join(seq_b[j1:j2])

        # Check if either chunk belongs to a moved paragraph
        orig_is_move = any(mp in orig_chunk for mp in moved_paras) if moved_paras else False
        rev_is_move  = any(mp in rev_chunk  for mp in moved_paras) if moved_paras else False

        if tag == "equal":
            orig_spans.append(asdict(Span("equal", orig_chunk, orig_offset, len(orig_chunk))))
            rev_spans.append(asdict(Span("equal", rev_chunk,  rev_offset,  len(rev_chunk))))

        elif tag == "insert":
            orig_spans.append(asdict(Span("equal", "", orig_offset, 0)))
            if rev_is_move:
                move_id = move_counter; move_counter += 1
                rev_spans.append(asdict(Span("move_to", rev_chunk, rev_offset, len(rev_chunk),
                                             _context(seq_b, j1), move_id)))
                summary["moves"] += 1
            else:
                rev_spans.append(asdict(Span("insert", rev_chunk, rev_offset, len(rev_chunk),
                                             _context(seq_b, j1))))
                summary["additions"] += 1
            summary["total"] += 1

        elif tag == "delete":
            if orig_is_move:
                move_id = move_counter; move_counter += 1
                orig_spans.append(asdict(Span("move_from", orig_chunk, orig_offset, len(orig_chunk),
                                              _context(seq_a, i1), move_id)))
                summary["moves"] += 1
            else:
                orig_spans.append(asdict(Span("delete", orig_chunk, orig_offset, len(orig_chunk),
                                              _context(seq_a, i1))))
                summary["deletions"] += 1
            rev_spans.append(asdict(Span("equal", "", rev_offset, 0)))
            summary["total"] += 1

        elif tag == "replace":
            orig_spans.append(asdict(Span("replace", orig_chunk, orig_offset, len(orig_chunk),
                                          _context(seq_a, i1))))
            rev_spans.append(asdict(Span("replace", rev_chunk, rev_offset, len(rev_chunk),
                                         _context(seq_b, j1))))
            summary["modifications"] += 1
            summary["total"] += 1

        orig_offset += len(orig_chunk)
        rev_offset  += len(rev_chunk)

    return DiffResult(original_spans=orig_spans, revised_spans=rev_spans, summary=summary)


def multi_granularity_compare(text_a: str, text_b: str) -> dict:
    result = compare(text_a, text_b, granularity="word")
    return {
        "original_spans": result.original_spans,
        "revised_spans":  result.revised_spans,
        "summary":        result.summary,
    }
