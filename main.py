import os
import json
import csv
import logging
import click
from utils.field_extractor import extract_fields, extract_text_from_pdf

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def flatten_result(item):
    """Flatten nested dicts for CSV output."""
    flat = {"source_file": item["source_file"]}
    for k, v in item["regex"].items():
        flat[f"regex_{k}"] = v
    for k, v in item["llm"].items():
        flat[f"llm_{k}"] = v
    for k, v in item["differences"].items():
        flat[f"diff_{k}"] = str(v)
    for k, v in item["accuracy"].items():
        flat[f"accuracy_{k}"] = v
    return flat


def save_results(results, output_file):
    """Save results to JSON or CSV based on file extension."""
    if output_file.lower().endswith(".json"):
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4, ensure_ascii=False)
        logging.info(f"✅ JSON output saved to: {output_file}")

    elif output_file.lower().endswith(".csv"):
        if results:
            # Flatten all results
            flat_results = [flatten_result(item) for item in results]

            # Collect all keys across all rows
            all_keys = set()
            for row in flat_results:
                all_keys.update(row.keys())
            all_keys = list(all_keys)

            # Ensure all rows have all keys
            for row in flat_results:
                for k in all_keys:
                    if k not in row:
                        row[k] = ""  # fill missing keys with empty string

            # Write CSV
            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=all_keys)
                writer.writeheader()
                writer.writerows(flat_results)
        logging.info(f"✅ CSV output saved to: {output_file}")
    else:
        logging.error("Unsupported file format! Please use .json or .csv")


@click.command()
@click.option("--input_path", required=True, help="Folder containing invoice PDFs or text files")
@click.option("--output_file", required=True, help="Output file (.json or .csv)")
@click.option("--ground_truth", default="ground_truth.json", help="JSON file with correct invoice data for accuracy comparison")
def process_invoices(input_path, output_file, ground_truth):
    all_results = []

    # Load ground truth
    if os.path.exists(ground_truth):
        with open(ground_truth, "r", encoding="utf-8") as f:
            gt_data = {item["source_file"]: item for item in json.load(f)}
    else:
        logging.warning(f"⚠️ Ground truth file not found: {ground_truth}")
        gt_data = {}

    if not os.path.exists(input_path):
        logging.error(f"❌ Input path does not exist: {input_path}")
        return

    files = [f for f in os.listdir(input_path) if f.lower().endswith((".pdf", ".txt"))]
    if not files:
        logging.warning(f"⚠️ No invoice files found in {input_path}")
        return

    for file_name in files:
        file_path = os.path.join(input_path, file_name)
        logging.info(f"📄 Processing: {file_path}")

        try:
            # Extract text
            if file_name.lower().endswith(".txt"):
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
            else:
                text = extract_text_from_pdf(file_path)

            # Extract fields using both modes
            fields_regex = extract_fields(text, source_file=file_name, mode="regex")
            fields_llm = extract_fields(text, source_file=file_name, mode="llm")

            # Compute differences
            differences = {
                k: {"regex": fields_regex.get(k), "llm": fields_llm.get(k)}
                for k in fields_regex
                if fields_regex.get(k) != fields_llm.get(k)
            }

            # Compute accuracy if ground truth is available
            accuracy = {"regex": 0, "llm": 0}
            gt = gt_data.get(file_name)
            if gt:
                total_fields = len(gt) - 1  # exclude source_file
                regex_correct = sum(
                    1 for k in gt if k != "source_file" and fields_regex.get(k) == gt.get(k)
                )
                llm_correct = sum(
                    1 for k in gt if k != "source_file" and fields_llm.get(k) == gt.get(k)
                )
                accuracy["regex"] = round((regex_correct / total_fields) * 100, 2)
                accuracy["llm"] = round((llm_correct / total_fields) * 100, 2)

                # Log which mode is more accurate
                if accuracy["regex"] > accuracy["llm"]:
                    logging.info(f"✅ {file_name}: Regex more accurate ({accuracy['regex']}%)")
                elif accuracy["regex"] < accuracy["llm"]:
                    logging.info(f"✅ {file_name}: LLM more accurate ({accuracy['llm']}%)")
                else:
                    logging.info(f"✅ {file_name}: Both modes equal ({accuracy['regex']}%)")

            # Combine all info
            combined = {
                "source_file": file_name,
                "regex": fields_regex,
                "llm": fields_llm,
                "differences": differences,
                "accuracy": accuracy,
            }
            all_results.append(combined)

            # Log differences
            if differences:
                logging.info(f"⚠️ Differences found in {file_name}: {differences}")
            else:
                logging.info(f"✅ No differences found for {file_name}")

        except Exception as e:
            logging.error(f"❌ Failed to process {file_name}: {e}")

    # Save results
    save_results(all_results, output_file)

    # Summary statistics
    if all_results:
        regex_avg = round(sum(item["accuracy"]["regex"] for item in all_results) / len(all_results), 2)
        llm_avg = round(sum(item["accuracy"]["llm"] for item in all_results) / len(all_results), 2)
        logging.info(f"📊 Average Accuracy - Regex: {regex_avg}%, LLM: {llm_avg}%")


if __name__ == "__main__":
    process_invoices()
