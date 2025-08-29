import json
import pandas as pd


def _coerce_types(rows):
    """Light validation/coercion with pandas-style dtypes."""
    for r in rows:
        # Amount to numeric if possible
        amt = r.get("total_amount")
        if isinstance(amt, str):
            try:
                r["total_amount"] = float(amt)
            except ValueError:
                pass
        # Keep other fields as-is; assignment only needs basic checks
    return rows


def save_results(results: list, output_file: str):
    """
    Save results to JSON or CSV based on the file extension.
    Applies light validation/coercion using pandas.
    """
    results = _coerce_types(results or [])

    if output_file.lower().endswith(".json"):
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    elif output_file.lower().endswith(".csv"):
        df = pd.DataFrame(results)
        # Order columns nicely if present
        preferred = [
            "doc_type",
            "invoice_number",
            "invoice_date",
            "vendor_name",
            "total_amount",
            "currency",
            "source_file",
        ]
        cols = [c for c in preferred if c in df.columns] + [c for c in df.columns if c not in preferred]
        df = df[cols]
        df.to_csv(output_file, index=False, encoding="utf-8")
    else:
        raise ValueError("Unsupported output format. Use .json or .csv")
