# File: src/extract/pdf_extractor.py

import pdfplumber
import json
import os
from datetime import datetime
from pathlib import Path

# ---- CONFIG ----
BRONZE_DIR = Path("data/bronze/pdf")
BRONZE_DIR.mkdir(parents=True, exist_ok=True)


def extract_pdf(pdf_path: str) -> dict:
    """
    Extracts raw text and tables from a PDF, page by page.
    Returns a dict — this is our 'bronze' record, untouched/raw.
    """
    pdf_path = Path(pdf_path)
    result = {
        "source_file": pdf_path.name,
        "extracted_at": datetime.utcnow().isoformat(),
        "pages": []
    }

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            page_data = {
                "page_number": page_num,
                "text": page.extract_text() or "",
                "tables": page.extract_tables() or []
            }
            result["pages"].append(page_data)

    return result


def save_bronze_record(record: dict, original_filename: str):
    """
    Saves the extracted raw record as JSON into the bronze layer.
    Filename pattern: <original_name>_<timestamp>.json
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    base_name = Path(original_filename).stem
    out_path = BRONZE_DIR / f"{base_name}_{timestamp}.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    print(f"[OK] Saved bronze record -> {out_path}")
    return out_path


if __name__ == "__main__":
    # ---- USAGE ----
    # Put your downloaded EPD/ESG PDFs into: data/raw_inputs/
    # This script reads from there and writes bronze JSON output.

    input_dir = Path("data/raw_inputs")
    input_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = list(input_dir.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDFs found in {input_dir}. Drop your EPD PDFs there and rerun.")
    else:
        for pdf_file in pdf_files:
            print(f"Processing: {pdf_file.name}")
            record = extract_pdf(pdf_file)
            save_bronze_record(record, pdf_file.name)