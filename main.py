import os
import click
import json
import pandas as pd
from utils.pdf_reader import extract_text_from_pdf
from utils.field_extractor import extract_fields

@click.command()
@click.option("--input_path", required=True, help="Path to input PDF or folder containing PDFs")
@click.option("--output_file", required=True, help="Output file (results.json or results.csv)")
@click.option("--mode", type=click.Choice(["regex", "llm"]), default="regex", help="Extraction mode: regex or llm")
def process_invoices(input_path, output_file, mode):
    results = []

    # If input_path is a directory, process all files inside
    if os.path.isdir(input_path):
        files = [os.path.join(input_path, f) for f in os.listdir(input_path) if f.lower().endswith(".pdf")]
    else:
        files = [input_path]

    for file in files:
        print(f"📄 Processing: {file}")
        text = extract_text_from_pdf(file)
        if not text.strip():
            print(f"⚠️ Skipped empty or unreadable file: {file}")
            continue

        fields = extract_fields(text, os.path.basename(file), mode=mode)

        # Only keep if recognized as an invoice
        if fields.get("doc_type") == "invoice":
            results.append(fields)
        else:
            print(f"❌ Invalid input (not recognized as an invoice): {os.path.basename(file)}")

    # Save results
    if output_file.endswith(".json"):
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
    elif output_file.endswith(".csv"):
        df = pd.DataFrame(results)
        df.to_csv(output_file, index=False)
    else:
        print("⚠️ Unsupported output format. Use .json or .csv")

    print(f"\n✅ Done. Processed: {len(results)}")
    print(f"➡️  Output saved to: {output_file}")

if __name__ == "__main__":
    process_invoices()
