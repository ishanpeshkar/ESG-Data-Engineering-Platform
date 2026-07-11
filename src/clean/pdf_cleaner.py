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
    """Loads all bronze PDF JSON files into memory."""
    records = []
    for json_file in BRONZE_PDF_DIR.glob("*.json"):
        with open(json_file, "r", encoding="utf-8") as f:
            records.append(json.load(f))
    return records


def extract_field(text: str, patterns: list) -> str:
    """
    Tries each regex pattern in order against the text.
    Returns the first match found, or None.
    """
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def clean_pdf_records(records: list) -> pd.DataFrame:
    """
    For each PDF bronze record, joins all page text into one blob,
    then attempts simple rule-based extraction of a few known EPD fields.
    """
    rows = []

    for record in records:
        source_file = record["source_file"]
        extracted_at = record["extracted_at"]

        # Join all pages into one big text blob for this document
        full_text = "\n".join(page["text"] for page in record["pages"])

        row = {
            "_source_file": source_file,
            "_extracted_at": extracted_at,
            "page_count": len(record["pages"]),
            "char_count": len(full_text),

            # --- Simple rule-based field extraction (placeholder logic) ---
            # These patterns are naive on purpose — this is just to prove
            # the "unstructured text -> structured field" concept.
            # Real structured extraction (inventory, methodology, results
            # overview, EPD scenarios etc.) comes later via schema-driven
            # LLM extraction.
            "product_name": extract_field(full_text, [
                r"Product\s*Name[:\-]?\s*(.+)",
                r"Product[:\-]?\s*(.+)"
            ]),
            "declared_unit": extract_field(full_text, [
                r"Declared\s*Unit[:\-]?\s*(.+)"
            ]),
            "reporting_period": extract_field(full_text, [
                r"Reporting\s*Period[:\-]?\s*(.+)",
                r"Validity\s*Period[:\-]?\s*(.+)"
            ]),
            "gwp_total": extract_field(full_text, [
                r"GWP[\-\s]*total[:\-]?\s*([\d\.,]+)",
                r"Global\s*Warming\s*Potential[:\-]?\s*([\d\.,]+)"
            ]),
            "standard_reference": extract_field(full_text, [
                r"(EN\s?15804[\+A-Za-z0-9]*)",
                r"(ISO\s?14025)"
            ]),
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    return df


def save_to_duckdb(df: pd.DataFrame, table_name: str = "silver_pdf_esg_data"):
    """Writes the cleaned DataFrame into DuckDB as a table (replaces if exists)."""
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