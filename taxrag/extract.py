"""Turn PDFs into clean text blocks, keeping tables intact.

The common failure in document RAG is not the model, it's extraction: a table gets
flattened into a jumble of numbers and the row/column meaning is lost. So we pull
tables out separately and write every row as "Header: value" pairs. Each row then
makes sense on its own, even if it ends up in a different chunk from the header.
"""

from dataclasses import dataclass
from pathlib import Path

import pdfplumber


@dataclass
class Block:
    source: str      # file name
    page: int        # 1-based page number
    kind: str        # "text" or "table"
    text: str


def _clean(cell) -> str:
    return " ".join(str(cell or "").split())


def table_to_lines(rows: list[list]) -> list[str]:
    """['Date','Amount'] + ['01/07','$5'] -> 'Date: 01/07 | Amount: $5'"""
    rows = [[_clean(c) for c in row] for row in rows if row and any(row)]
    if len(rows) < 2:
        return [" | ".join(r) for r in rows]
    header, body = rows[0], rows[1:]
    lines = []
    for row in body:
        pairs = [f"{h}: {v}" for h, v in zip(header, row) if v]
        lines.append(" | ".join(pairs))
    return lines


def extract_pdf(path: Path) -> list[Block]:
    blocks: list[Block] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            tables = page.find_tables()
            # Remove table areas from the page so table text isn't extracted twice.
            text_page = page
            for t in tables:
                text_page = text_page.outside_bbox(t.bbox)
            text = text_page.extract_text() or ""
            if text.strip():
                blocks.append(Block(path.name, page.page_number, "text", text.strip()))
            elif not tables:
                # Probably a scanned page. We flag it instead of silently skipping it.
                print(f"  WARNING: no text on {path.name} page {page.page_number} (scanned? needs OCR)")
            for t in tables:
                lines = table_to_lines(t.extract())
                if lines:
                    blocks.append(Block(path.name, page.page_number, "table", "\n".join(lines)))
    return blocks


def extract_folder(folder: Path) -> list[Block]:
    blocks: list[Block] = []
    for pdf in sorted(folder.glob("*.pdf")):
        found = extract_pdf(pdf)
        print(f"  {pdf.name}: {len(found)} blocks")
        blocks.extend(found)
    return blocks
