# File: src/clean/pdf_cleaner.py

import json
import re
import duckdb
import pandas as pd
from pathlib import Path

BRONZE_PDF_DIR = Path("data/bronze/pdf")
SILVER_DB_PATH = Path("data/silver/esg_silver.duckdb")
SILVER_DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_bronze_pdf_records() -> list:
    records = []
    for json_file in BRONZE_PDF_DIR.glob("*.json"):
        with open(json_file, "r", encoding="utf-8") as f:
            records.append(json.load(f))
    return records


def extract_field(text: str, patterns: list, max_len: int = 120) -> str:
    """
    Tries each regex pattern in order. Returns first match, trimmed and
    capped in length (to avoid grabbing runaway sentences).
    """
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            value = match.group(1).strip()
            # Reject matches that are clearly not real values (too long = probably
            # grabbed a whole sentence/paragraph instead of a field value)
            if 0 < len(value) <= max_len:
                return value
    return None


def clean_pdf_records(records: list) -> pd.DataFrame:
    rows = []

    for record in records:
        source_file = record["source_file"]
        extracted_at = record["extracted_at"]

        # Prioritize first 3 pages — EPD "declaration summary" info is almost
        # always near the front, not buried deep in the document
        front_pages_text = "\n".join(
            page["text"] for page in record["pages"][:3]
        )
        full_text = "\n".join(page["text"] for page in record["pages"])

        row = {
            "_source_file": source_file,
            "_extracted_at": extracted_at,
            "page_count": len(record["pages"]),
            "char_count": len(full_text),

            "product_name": extract_field(front_pages_text, [
                r"^Product\s*Name\s*[:\-]\s*(.+)$",
                r"^Product\s*[:\-]\s*(.+)$",
            ], max_len=80) or extract_field(front_pages_text, [
                r"Product\s*Name\s*[:\-]\s*(.+)",
            ], max_len=80),

            "declared_unit": extract_field(front_pages_text, [
                r"Declared\s*Unit\s*[:\-]\s*([^\n\.]{1,80})",
            ]),

            "reporting_period": extract_field(front_pages_text, [
                r"(?:Reporting|Validity)\s*Period\s*[:\-]\s*([^\n\.]{1,60})",
                r"Issue\s*[Dd]ate\s*[:\-]\s*([^\n]{1,40})",
                r"Valid\s*(?:until|to)\s*[:\-]?\s*([^\n\.]{1,40})",
            ]),

            "gwp_total": extract_field(full_text, [
                r"GWP[\-\s]*total[^\d\-]{0,15}(-?[\d]+[\.,]?\d*)",
                r"Global\s*Warming\s*Potential[^\d\-]{0,20}(-?[\d]+[\.,]?\d*)",
                r"(?:kg\s*CO2[\-\s]?e(?:q)?)[^\d\-]{0,10}(-?[\d]+[\.,]?\d*)",
            ], max_len=20),

            "standard_reference": extract_field(full_text, [
                r"(EN\s?15804\+?A?\d?)",
                r"(ISO\s?14025)",
                r"(ISO\s?21930)",
            ], max_len=20),
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    return df


def save_to_duckdb(df: pd.DataFrame, table_name: str = "silver_pdf_esg_data"):
    con = duckdb.connect(str(SILVER_DB_PATH))
    con.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM df")
    row_count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
    con.close()
    print(f"[OK] Wrote {row_count} rows into DuckDB table '{table_name}' at {SILVER_DB_PATH}")


if __name__ == "__main__":
    records = load_bronze_pdf_records()

    if not records:
        print(f"No bronze PDF JSON files found in {BRONZE_PDF_DIR}.")
    else:
        df = clean_pdf_records(records)
        print(f"Cleaned DataFrame shape: {df.shape}")
        print(df.to_string())
        save_to_duckdb(df)