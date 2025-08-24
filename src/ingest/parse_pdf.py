"""Text extractor with basic heading preservation; OCR fallback handled separately."""
from pathlib import Path
import fitz  # PyMuPDF
from typing import List, Tuple

def extract_text_by_page(pdf_path: Path) -> List[Tuple[int, str]]:
    doc = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc, start=1):
        txt = page.get_text("text") or ""
        pages.append((i, txt))
    doc.close()
    return pages
