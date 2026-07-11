# File: src/clean/excel_cleaner.py

import json
import duckdb
import pandas as pd
from pathlib import Path

BRONZE_EXCEL_DIR = Path("data/bronze/excel")
SILVER_DB_PATH = Path("data/silver/esg_silver.duckdb")
SILVER_DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_bronze_excel_records() -> list:
    """Loads all bronze Excel JSON files into memory."""
    records = []
    for json_file in BRONZE_EXCEL_DIR.glob("*.json"):
        with open(json_file, "r", encoding="utf-8") as f:
            records.append(json.load(f))
    return records


def clean_excel_records(records: list) -> pd.DataFrame:
    """
    Flattens all sheets/rows from all bronze Excel records into
    a single clean DataFrame, with basic cleaning applied.
    """
    all_rows = []

    for record in records:
        source_file = record["source_file"]
        extracted_at = record["extracted_at"]

        for sheet_name, sheet_data in record["sheets"].items():
            for row in sheet_data["rows"]:
                cleaned_row = {
                    k: (v.strip() if isinstance(v, str) else v)
                    for k, v in row.items()
                }
                cleaned_row["_source_file"] = source_file
                cleaned_row["_sheet_name"] = sheet_name
                cleaned_row["_extracted_at"] = extracted_at
                all_rows.append(cleaned_row)

    df = pd.DataFrame(all_rows)
    df = df.dropna(how="all")

    # Clean column names
    new_cols = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    # --- NEW: de-duplicate column names ---
    # Real-world ESG Excel templates often have multiple blank/unnamed
    # columns that collapse into the same name after cleaning.
    # We make each one unique (e.g. unnamed:_0, unnamed:_0__2, ...)
    # so pandas treats them as distinct Series, not a repeated block.
    seen = {}
    deduped_cols = []
    for c in new_cols:
        if c not in seen:
            seen[c] = 0
            deduped_cols.append(c)
        else:
            seen[c] += 1
            deduped_cols.append(f"{c}__{seen[c]}")
    df.columns = deduped_cols

    # --- Force every cell to a safe string type (elementwise, not per-column) ---
    # Using applymap avoids the duplicate-column Series-vs-DataFrame issue entirely,
    # since it operates on raw values, not column selection.
    df = df.applymap(lambda v: None if pd.isna(v) else str(v))

    return df


def save_to_duckdb(df: pd.DataFrame, table_name: str = "silver_excel_esg_data"):
    """Writes the cleaned DataFrame into DuckDB as a table (replaces if exists)."""
    con = duckdb.connect(str(SILVER_DB_PATH))
    con.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM df")
    row_count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
    con.close()
    print(f"[OK] Wrote {row_count} rows into DuckDB table '{table_name}' at {SILVER_DB_PATH}")


if __name__ == "__main__":
    records = load_bronze_excel_records()

    if not records:
        print(f"No bronze Excel JSON files found in {BRONZE_EXCEL_DIR}.")
    else:
        df = clean_excel_records(records)
        print(f"Cleaned DataFrame shape: {df.shape}")
        print(df.head())
        save_to_duckdb(df)