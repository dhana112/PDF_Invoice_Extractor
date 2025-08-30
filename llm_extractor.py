import re
import logging
import openai
import json
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Load API key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

def extract_fields(text: str, source_file: str = None, mode: str = "regex") -> dict:
    """
    Extract invoice fields using either regex rules (default) or LLM.
    """
    if mode == "llm":
        return extract_with_llm(text, source_file)

    # ---------- Regex Mode ----------
    result = {
        "doc_type": "invoice",
        "invoice_number": None,
        "invoice_date": None,
        "vendor_name": None,
        "total_amount": None,
        "currency": None,
        "source_file": source_file
    }

    # Invoice number
    m = re.search(r"(?:Invoice\s*(?:No|#)?[:\-]?\s*|Inv\s*No[:\-]?\s*|Bill\s*No[:\-]?\s*)([A-Za-z0-9\-\/]+)", text, re.IGNORECASE)
    if m and "@" not in m.group(1):  
        result["invoice_number"] = m.group(1).strip()

    # Date
    m = re.search(r"(?:Date|Dated|Invoice\s*Date)[:\-]?\s*([A-Za-z]{3,9}\s*\d{1,2},?\s*\d{4})", text, re.IGNORECASE)
    if m:
        result["invoice_date"] = m.group(1).strip()

    # Vendor
    m = re.search(r"([A-Za-z0-9\s,&\.-]+(?:Ltd|Limited|Pvt|LLP|Inc|Company|Corporation))", text, re.IGNORECASE)
    if m:
        result["vendor_name"] = m.group(1).strip()

    # Total amount
    m = re.search(r"(?:Total|Amount\s*Due|Invoice\s*Total|Balance\s*Due)[:\-]?\s*([\d,]+\.\d{2})", text, re.IGNORECASE)
    if m:
        result["total_amount"] = float(m.group(1).replace(",", ""))

    # Currency
    m = re.search(r"\b(GBP|USD|INR|EUR|CAD|AUD)\b", text, re.IGNORECASE)
    if m:
        result["currency"] = m.group(1).upper()
    elif "£" in text:
        result["currency"] = "GBP"
    elif "$" in text:
        result["currency"] = "USD"
    elif "₹" in text:
        result["currency"] = "INR"

    return result


def extract_with_llm(text: str, source_file: str):
    """
    Use OpenAI LLM to extract fields from invoice text.
    """
    prompt = f"""
    Extract the following fields from this invoice text and return JSON only:
    - Invoice Number
    - Invoice Date
    - Vendor Name
    - Total Amount
    - Currency

    Invoice Text:
    {text}
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        content = response.choices[0].message["content"].strip()
        extracted = json.loads(content)

        return {
            "doc_type": "invoice",
            "invoice_number": extracted.get("Invoice Number"),
            "invoice_date": extracted.get("Invoice Date"),
            "vendor_name": extracted.get("Vendor Name"),
            "total_amount": extracted.get("Total Amount"),
            "currency": extracted.get("Currency"),
            "source_file": source_file
        }
    except Exception as e:
        logging.error(f"[{source_file}] LLM extraction failed: {e}")
        return {
            "doc_type": "invoice",
            "invoice_number": None,
            "invoice_date": None,
            "vendor_name": None,
            "total_amount": None,
            "currency": None,
            "source_file": source_file
        }
