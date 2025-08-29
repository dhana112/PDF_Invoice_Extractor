import os
import re
import click

from utils.pdf_reader import extract_text_from_pdf
from utils.field_extractor import extract_fields
from utils.output_formatter import save_results

SUPPORTED_EXTENSIONS = (".pdf",)  # PDFs only


def looks_like_invoice(text: str) -> bool:
    """
    Quick heuristic to reject non-invoice PDFs:
    - must contain 'invoice' somewhere OR
    - contain a common invoice number pattern label
    """
    tl = text.lower()
    if "invoice" in tl:
        return True
    if re.search(r"(invoice\s*(no|#)|inv\s*no|bill\s*no)", tl):
        return True
    return False


@click.command()
@click.option(
    "--input_path",
    required=True,
    help="Path to a folder OR a single PDF file",
)
@click.option(
    "--output_file",
    required=True,
    help="Output file (.json or .csv)",
)
def process_invoices(input_path: str, output_file: str):
    results = []

    # Detect single file vs folder
    if os.path.isfile(input_path):
        files = [os.path.basename(input_path)]
        base_path = os.path.dirname(input_path)
    else:
        files = os.listdir(input_path)
        base_path = input_path

    processed = 0
    skipped = 0

    for file in files:
        if not file.lower().endswith(SUPPORTED_EXTENSIONS):
            print(f"⚠️  Skipped unsupported file (PDFs only): {file}")
            continue

        file_path = os.path.join(base_path, file)
        print(f"📄 Processing: {file_path}")

        try:
            text = extract_text_from_pdf(file_path)

            # Reject non-invoices explicitly
            if not looks_like_invoice(text):
                print(f"❌ Invalid input (not recognized as an invoice): {file}")
                skipped += 1
                continue

            fields = extract_fields(text, source_file=file)

            # If we at least have invoice_number or vendor_name, we’ll keep it
            if any([fields.get("invoice_number"), fields.get("vendor_name")]):
                results.append(fields)
                processed += 1
            else:
                print(f"❌ Invalid input (no key fields found): {file}")
                skipped += 1

        except Exception as e:
            print(f"⚠️  Error processing {file}: {e}")
            skipped += 1

    # Save aggregated results
    save_results(results, output_file)

    print(f"\n✅ Done. Processed: {processed} | Skipped/Invalid: {skipped}")
    print(f"➡️  Output saved to: {output_file}")


if __name__ == "__main__":
    process_invoices()
