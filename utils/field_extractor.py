import re
import logging
import os
from PIL import Image
import fitz  # PyMuPDF
import pytesseract


# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# ✅ Configure Tesseract path (adjust if installed elsewhere)
# Example default Windows path:
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from PDF using PyMuPDF.
    If page has no text, fallback to OCR using pytesseract.
    """
    doc = fitz.open(pdf_path)
    full_text = ""

    for page_number, page in enumerate(doc, start=1):
        text = page.get_text()
        if text.strip():
            full_text += text + "\n"
        else:
            # OCR fallback
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            ocr_text = pytesseract.image_to_string(img)
            if ocr_text.strip():
                logging.info(f"[{pdf_path}][Page {page_number}] OCR text extracted.")
            else:
                logging.warning(f"[{pdf_path}][Page {page_number}] No text found via OCR.")
            full_text += ocr_text + "\n"

    return full_text


def extract_fields(text: str, source_file: str = None, mode: str = "regex") -> dict:
    """
    Extract invoice fields using either regex (default) or LLM mode.
    """
    result = {
        "doc_type": "invoice",
        "invoice_number": None,
        "invoice_date": None,
        "vendor_name": None,
        "total_amount": None,
        "currency": None,
        "source_file": source_file,
    }

    if mode == "regex":
        # -------------------------
        # Invoice Number
        # -------------------------
        m = re.search(r"Invoice\s*#\s*[:\-]?\s*([A-Za-z0-9\-\/]+)", text, re.IGNORECASE)
        if m and "@" not in m.group(1):
            result["invoice_number"] = m.group(1).strip()
        else:
            m = re.search(r"Invoice\s*No[:\-]?\s*([A-Za-z0-9\-\/]+)", text, re.IGNORECASE)
            if m and "@" not in m.group(1):
                result["invoice_number"] = m.group(1).strip()
            else:
                m = re.search(r"(?:Inv|Bill)\s*(?:No|#)[:\-]?\s*([A-Za-z0-9\-\/]+)", text, re.IGNORECASE)
                if m and "@" not in m.group(1):
                    result["invoice_number"] = m.group(1).strip()
                else:
                    logging.warning(f"[{source_file}] Invoice number not found.")

        # -------------------------
        # Invoice Date
        # -------------------------
        m = re.search(
            r"(?:Dated|Date|Invoice\s*Date)[:\-]?\s*"
            r"([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4}|"
            r"[0-9]{4}[\/\-][0-9]{1,2}[\/\-][0-9]{1,2}|"
            r"[0-9]{1,2}\s*\w+\s*[0-9]{2,4}|"
            r"\w+\s*[0-9]{1,2},\s*[0-9]{4})",
            text,
            re.IGNORECASE,
        )
        if m:
            result["invoice_date"] = m.group(1).strip()
        else:
            m = re.search(
                r"([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4}|"
                r"[0-9]{4}[\/\-][0-9]{1,2}[\/\-][0-9]{1,2}|"
                r"[0-9]{1,2}\s*\w+\s*[0-9]{2,4}|"
                r"\w+\s*[0-9]{1,2},\s*[0-9]{4})",
                text,
            )
            if m:
                result["invoice_date"] = m.group(1).strip()
            else:
                logging.warning(f"[{source_file}] Invoice date not found.")

        # -------------------------
        # Vendor Name
        # -------------------------
        vendor_name = None
        for line in text.splitlines():
            m = re.search(
                r"\b([A-Za-z0-9\s,&\.-]+(?:Ltd|Limited|Pvt|LLP|Inc|Corporation|Company|Processing))\b",
                line.strip(),
                re.IGNORECASE,
            )
            if m:
                vendor_name = m.group(1).strip()
                break
        if vendor_name:
            result["vendor_name"] = vendor_name
        else:
            logging.warning(f"[{source_file}] Vendor name not found.")

        # -------------------------
        # Total Amount
        # -------------------------
        m = re.search(
            r"(?:Total\s*Amount|Amount\s*Due|Invoice\s*Total|Balance\s*Due)[:\-]?\s*([\d,]+\.\d{2})",
            text,
            re.IGNORECASE,
        )
        if m:
            result["total_amount"] = float(m.group(1).replace(",", ""))
        else:
            numbers = [float(x.replace(",", "")) for x in re.findall(r"[\d,]+\.\d{2}", text)]
            if numbers:
                result["total_amount"] = max(numbers)
            else:
                logging.warning(f"[{source_file}] Total amount not found.")

        # -------------------------
        # Currency
        # -------------------------
        m = re.search(r"\b(GBP|USD|INR|EUR|CAD|AUD)\b", text, re.IGNORECASE)
        if m:
            result["currency"] = m.group(1).upper()
        else:
            if "£" in text:
                result["currency"] = "GBP"
            elif "$" in text:
                result["currency"] = "USD"
            elif "₹" in text:
                result["currency"] = "INR"
            else:
                logging.warning(f"[{source_file}] Currency not detected.")

        return result  # ✅ return at end of regex block

    elif mode == "llm":
        try:
            from llm_extractor import llm_extract_invoice
            return llm_extract_invoice(text, source_file)
        except Exception as e:
            logging.error(f"[{source_file}] LLM extraction failed: {e}")
            return result  # return empty regex-like structure if LLM fails

    else:
        raise ValueError(f"Unsupported extraction mode: {mode}")
