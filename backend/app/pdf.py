import re
from collections import Counter

import pymupdf


class PdfError(ValueError):
    pass


def _page_text(page) -> str:
    # Native block order follows the document's reading flow, so two-column pages stay intact (sort=True would interleave columns).
    blocks = [b for b in page.get_text("blocks") if b[6] == 0]
    return "\n".join(b[4].strip() for b in blocks)


def _strip_running_lines(pages: list[str]) -> list[str]:
    """Remove short lines (headers, footers, page numbers) repeated across many pages."""
    if len(pages) < 3:
        return pages
    norm = lambda l: re.sub(r"\d+", "#", l.strip())
    counts = Counter(norm(l) for p in pages for l in set(p.splitlines()) if 0 < len(l.strip()) < 80)
    limit = max(3, len(pages) // 2)
    repeated = {k for k, v in counts.items() if v >= limit}
    return ["\n".join(l for l in p.splitlines() if norm(l) not in repeated) for p in pages]


def extract_text(data: bytes) -> dict:
    """Extract per-page text from PDF bytes. Raises PdfError on invalid/empty PDFs."""
    if not data.startswith(b"%PDF"):
        raise PdfError("File is not a valid PDF.")
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise PdfError("Could not read the PDF.") from exc
    with doc:
        if doc.needs_pass:
            raise PdfError("PDF is password protected.")
        pages = [_page_text(page) for page in doc]
        title = (doc.metadata or {}).get("title") or ""
    text = "\n".join(_strip_running_lines(pages)).strip()
    if len(text) < 200:
        raise PdfError("No extractable text found (scanned PDFs are not supported yet).")
    return {"title": title, "page_count": len(pages), "text": text}
