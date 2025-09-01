import os
import json
import logging
import re
import google.generativeai as genai

# Load API key
API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)

# Use a Gemini model (16k tokens, safe for invoices)
MODEL_NAME = "gemini-1.5-flash"
model = genai.GenerativeModel(MODEL_NAME)

def llm_extract_invoice(text: str, source_file: str = None) -> dict:
    prompt = f"""
    You are an AI that extracts structured data from invoices.
    Return output strictly in JSON with the following keys:
    - doc_type (always "invoice")
    - invoice_number
    - invoice_date
    - vendor_name
    - total_amount
    - currency

    Invoice text:
    {text}
    """

    try:
        response = model.generate_content(prompt)
        raw_text = response.text.strip()

        logging.info(f"[LLM Raw Response] {raw_text}")

        # ✅ 1. Remove markdown code fences like ```json ... ```
        clean_text = re.sub(r"^```json\s*|\s*```$", "", raw_text, flags=re.DOTALL).strip()

        # ✅ 2. Extract JSON if there’s extra explanation before/after
        match = re.search(r"\{.*\}", clean_text, re.DOTALL)
        if match:
            clean_text = match.group(0)

        # ✅ 3. Load JSON safely
        result = json.loads(clean_text)

    except Exception as e:
        logging.error(f"LLM extraction failed for {source_file}: {e}")
        result = {
            "doc_type": "invoice",
            "invoice_number": None,
            "invoice_date": None,
            "vendor_name": None,
            "total_amount": None,
            "currency": None,
            "source_file": source_file,
        }

    result["source_file"] = source_file
    return result
