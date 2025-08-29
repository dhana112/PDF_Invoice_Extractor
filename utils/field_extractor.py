import re
import logging

# Setup logging for debug mode
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def extract_fields(text: str, source_file: str = None) -> dict:
    """
    Extract structured invoice fields from text:
      - invoice_number
      - invoice_date
      - vendor_name (clean, not address block)
      - total_amount
      - currency
    Returns a dict with None for unavailable fields.
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

    # -------------------------
    # Invoice number
    # -------------------------
    m = re.search(r"Invoice\s*#\s*[:\-]?\s*([A-Za-z0-9\-\/]+)", text, re.IGNORECASE)
    if m and "@" not in m.group(1):
        result["invoice_number"] = m.group(1).strip()
    else:
        # Alternate explicit form: "Invoice No:"
        m = re.search(r"Invoice\s*No[:\-]?\s*([A-Za-z0-9\-\/]+)", text, re.IGNORECASE)
        if m and "@" not in m.group(1):
            result["invoice_number"] = m.group(1).strip()
        else:
            # Fallback patterns (rare cases)
            m = re.search(r"(?:Inv|Bill)\s*(?:No|#)[:\-]?\s*([A-Za-z0-9\-\/]+)", text, re.IGNORECASE)
            if m and "@" not in m.group(1):
                result["invoice_number"] = m.group(1).strip()
            else:
                logging.warning(f"[{source_file}] Invoice number not found.")

    # -------------------------
    # Invoice date
    # (matches: 'Dated:', 'Date:', 'Invoice Date:')
    # Invoice Date (support multiple formats: 05 Jan 2024, 2024-01-05, 05/01/2024, 01/05/24, Nov 03, 2022, 03-11-22)
    # -------------------------
    m = re.search(
        r"(?:Dated|Date|Invoice\s*Date)[:\-]?\s*"
        r"([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4}|"   # 03/11/2022 or 03-11-22
        r"[0-9]{4}[\/\-][0-9]{1,2}[\/\-][0-9]{1,2}|"      # 2022-11-03
        r"[0-9]{1,2}\s*\w+\s*[0-9]{2,4}|"                 # 03 Nov 2022
        r"\w+\s*[0-9]{1,2},\s*[0-9]{4})",                 # Nov 03, 2022
        text,
        re.IGNORECASE,
    )
    if m:
        result["invoice_date"] = m.group(1).strip()
    else:
        # Fallback: search any date-like pattern anywhere in text
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
    # Vendor name (tiered approach)
    # 1) strongest: a single line that looks like a legal entity
    # 2) fallback: the first line after 'Web:' (Doc2 style)
    # 3) final fallback: first proper noun sequence (best-effort)
    # -------------------------
    vendor = None

    # 1) Strongest: line with company keywords (but avoid full addresses)
    m = re.search(
        r"(?m)^(?:(?!Street|Road|Rd|Avenue|Ave|Lane|Ln|Drive|Dr|Gloucestershire|India|United|Kingdom).)*\b"
        r"(?:Limited|Ltd|Pvt|LLP|Inc|Corporation|Corp|LLC|Company)\b.*$",
        text,
        re.IGNORECASE,
    )
    if m:
        vendor = m.group(0).strip()

    # 2) Fallback: line after "Web:" (Doc2 style)
    if not vendor:
        m = re.search(r"Web.*?\n([A-Za-z0-9\s,&\.-]+)", text, re.IGNORECASE)
        if m:
            line = m.group(1).strip()
            # reject if looks like address
            if not re.search(r"\b(Street|Road|Avenue|Gloucestershire|USA|India|United Kingdom)\b", line, re.I):
                vendor = line

    # 3) Fallback: first 2–4 consecutive capitalized words
    if not vendor:
        m = re.search(r"\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){1,3})\b", text)
        if m:
            vendor = m.group(1).strip()

    if vendor:
        # Final cleanup: strip trailing commas/countries/postcodes
        vendor = re.sub(r"\b(United\s+Kingdom|India|USA|U\.S\.A\.|Gloucestershire.*)$", "", vendor, flags=re.I).strip(", ")
        result["vendor_name"] = vendor
    else:
        logging.warning(f"[{source_file}] Vendor name not found.")


    # -------------------------
    # Total amount
    # Prefer explicit labels; else fallback to max amount > threshold
    # -------------------------
    m = re.search(
        r"(?:Total|Amount\s*Due|Invoice\s*Total|Balance\s*Due)[:\-\s]*([\d,]+\.\d{2})",
        text,
        re.IGNORECASE,
    )
    if m:
        result["total_amount"] = m.group(1).replace(",", "")
    else:
        # fallback: largest float > 100
        amounts = [float(x.replace(",", "")) for x in re.findall(r"[\d,]+\.\d{2}", text)]
        if amounts:
            big = [n for n in amounts if n > 100]
            if big:
                result["total_amount"] = str(max(big))
            else:
                logging.warning(f"[{source_file}] No valid total amount above threshold found.")
        else:
            logging.warning(f"[{source_file}] Total amount not found.")

    # -------------------------
    # Currency detection
    # -------------------------
    m = re.search(r"\b(GBP|USD|INR|EUR|CAD|AUD)\b", text, re.IGNORECASE)
    if m:
        result["currency"] = m.group(1).upper()
    else:
        # Symbols
        if "£" in text:
            result["currency"] = "GBP"
        elif "$" in text:
            result["currency"] = "USD"
        elif "₹" in text:
            result["currency"] = "INR"
        else:
            logging.warning(f"[{source_file}] Currency not detected.")

    return result
