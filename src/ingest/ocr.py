"""OCR for low-text pages using Tesseract."""
from pathlib import Path
from typing import Optional
import fitz
from PIL import Image
import io
import pytesseract

def ocr_page(pdf_path: Path, page_number: int) -> Optional[str]:
    doc = fitz.open(pdf_path)
    page = doc[page_number - 1]
    pix = page.get_pixmap(dpi=200)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    text = pytesseract.image_to_string(img) or ""
    doc.close()
    return text.strip() or None
