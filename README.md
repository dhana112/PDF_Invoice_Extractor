# PDF Invoice Extractor 

## Objective
Extract structured fields (**invoice number, date, vendor name, total amount, currency**) from **Document2**-style invoices.  
Supports **digital PDFs** and **scanned PDFs** (via OCR). Batch mode optional.

## Project Structure
```
PDF_Invoice_Extractor
  main.py
  utils/
    pdf_reader.py
    field_extractor.py
    output_formatter.py
  invoices/
    Document2.pdf
    Img1.pdf  
  requirements.txt
  README.md
  LICENSE
  .gitignore
```

## Pipeline
+-----------------+
|   Input PDFs    |   (Invoices)
+--------+--------+
         |
         v
+---------------------+
| pdf_reader.py       | → Extract text (PyPDF2 → OCR fallback)
+---------------------+
         |
         v
+---------------------+
| field_extractor.py  | → Regex rules:
|                     |   - Invoice No
|                     |   - Date
|                     |   - Vendor
|                     |   - Total + Currency
+---------------------+
         |
         v
+---------------------+
| output_formatter.py | → Save as JSON / CSV (pandas)
+---------------------+
         |
         v
+-----------------+
|   Results       | → results.json / results.csv
+-----------------+

## Setup
```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
# Install Tesseract (system dependency) if you need OCR:
# Windows: https://github.com/UB-Mannheim/tesseract/wiki
# Ubuntu:  sudo apt-get install tesseract-ocr
```

## Run
```bash
# Single file - JSON
python main.py --input_path .\invoices\Document2.pdf --output_file result.json

# Single file - CSV
python main.py --input_path .\invoices\Document2.pdf --output_file result.json

# Batch folder - JSON
python main.py --input_path .\invoices --output_file results.json

# Batch folder - CSV
python main.py --input_path .\invoices --output_file results.csv

```

## Invalid Input Handling
If a non-invoice PDF is given, output will contain:
```json
{ "doc_type": "invalid", "error": "❌ Not an invoice document or empty text", "source_file": "X.pdf" }
```

## Sample Output
```json
[
  {
    "doc_type": "invoice",
    "invoice_number": "S2401-34",
    "invoice_date": "05 Jan 2024",
    "vendor_name": "Renishaw UK Sales Limited",
    "total_amount": "27743.11",
    "currency": "GBP",
    "source_file": "Document2.pdf"
  }
]
```

## Tools & Rationale

- **PyMuPDF**: modern PDF text + image extraction
- **Tesseract OCR + Pillow**: scanned PDFs
- **Regex**: robust, explainable rules for fixed vendor (Doc2)
- **pandas**: validation + JSON/CSV
- **tabulate**: markdown preview
- **Click**: clean CLI
- **joblib**: optional parallelism for batch mode

## SOTA Comparison (Accuracy vs Speed)
| Tool            | Accuracy (digital) | Accuracy (scanned) | Speed | Notes                       |
|-----------------|--------------------|--------------------|-------|-----------------------------|
| PyMuPDF         | Very High          | N/A                | Fast  | Better layout handling      |
| invoice2data    | High (with templates) | Low-Med         | Med   | Template/ML extraction      |
| Tesseract (OCR) | N/A                | Medium             | Slow  | Needs good image quality    |

## Security
- No PII/API keys in code
- `.gitignore` excludes virtualenv, caches, local artifacts
- Use env vars if adding credentials later

## Acceptance Criteria Mapping
- Modular Python code ✔
- `requirements.txt` pinned ✔
- README with pipeline, implementation, steps ✔
- OCR fallback ✔
- Comparison section ✔
- Apache 2.0 license ✔

## License
Apache 2.0 — see [LICENSE](LICENSE).
