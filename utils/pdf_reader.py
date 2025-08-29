import os
import io
import logging

import fitz  # PyMuPDF
from PIL import Image
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def _ocr_page(page) -> str:
    """Render a page to image and OCR it."""
    # scale up for better OCR
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    img_bytes = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_bytes))
    return pytesseract.image_to_string(img)


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from a PDF:
      1) Try PyMuPDF selectable text per page
      2) If empty, fallback to OCR (Tesseract)
    Returns concatenated text for all pages.
    """
    doc = fitz.open(pdf_path)
    texts = []

    for i, page in enumerate(doc, start=1):
        page_text = page.get_text("text")
        if page_text and page_text.strip():
            texts.append(page_text)
        else:
            logging.info(f"OCR needed on page {i} of {pdf_path}")
            try:
                ocr_text = _ocr_page(page)
                texts.append(ocr_text)
            except Exception as e:
                logging.warning(f"OCR failed on page {i} of {pdf_path}: {e}")

    doc.close()
    return "\n".join(texts)
