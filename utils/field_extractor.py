import re
import logging
import os
import json
from dotenv import load_dotenv
from openai import OpenAI

# ✅ Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# ✅ Initialize OpenAI client (new SDK)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


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
        prompt = f"""
        Extract invoice details from the text below and return JSON with keys:
        invoice_number, invoice_date, vendor_name, total_amount, currency.

        Text:
        {text}
        """
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an invoice parser."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
            )
            content = response.choices[0].message.content
            parsed = json.loads(content)
            result.update(parsed)
        except Exception as e:
            logging.error(f"[{source_file}] LLM extraction failed: {e}")
        return result  # ✅ return at end of LLM block

    else:
        raise ValueError(f"Unsupported extraction mode: {mode}")
