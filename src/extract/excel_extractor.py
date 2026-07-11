# File: src/extract/excel_extractor.py

import pandas as pd
import json
import os
from datetime import datetime
from pathlib import Path

# ---- CONFIG ----
BRONZE_DIR = Path("data/bronze/excel")
BRONZE_DIR.mkdir(parents=True, exist_ok=True)


def extract_excel(excel_path: str) -> dict:
    """
    Extracts all sheets from an Excel file as raw records.
    Returns a dict — bronze layer, untouched data (just structured as JSON-able).
    """
    excel_path = Path(excel_path)
    result = {
        "source_file": excel_path.name,
        "extracted_at": datetime.utcnow().isoformat(),
        "sheets": {}
    }

    # Read all sheets at once
    all_sheets = pd.read_excel(excel_path, sheet_name=None, engine="openpyxl")

    for sheet_name, df in all_sheets.items():
        # Convert NaN to None so JSON serialization doesn't break
        df = df.where(pd.notnull(df), None)
        records = df.to_dict(orient="records")

        result["sheets"][sheet_name] = {
            "columns": list(df.columns),
            "row_count": len(records),
            "rows": records
        }

    return result


def save_bronze_record(record: dict, original_filename: str):
    """
    Saves the extracted raw Excel record as JSON into the bronze layer.
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    base_name = Path(original_filename).stem
    out_path = BRONZE_DIR / f"{base_name}_{timestamp}.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False, default=str)

    print(f"[OK] Saved bronze record -> {out_path}")
    return out_path


if __name__ == "__main__":
    # ---- USAGE ----
    # Put your Excel files (.xlsx) into: data/raw_inputs/
    # This script reads from there and writes bronze JSON output.

    input_dir = Path("data/raw_inputs")
    input_dir.mkdir(parents=True, exist_ok=True)

    excel_files = list(input_dir.glob("*.xlsx"))

    if not excel_files:
        print(f"No Excel files found in {input_dir}. Drop your .xlsx files there and rerun.")
    else:
        for excel_file in excel_files:
            print(f"Processing: {excel_file.name}")
            record = extract_excel(excel_file)
            save_bronze_record(record, excel_file.name)