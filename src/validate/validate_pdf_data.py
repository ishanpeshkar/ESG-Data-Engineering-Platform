# File: src/validate/validate_pdf_data.py

import duckdb
import pandas as pd
import pandera.pandas as pa
from pathlib import Path

# Import the schema we defined in Step 2.1
from src.validate.pdf_schema import pdf_esg_schema

SILVER_DB_PATH = Path("data/silver/esg_silver.duckdb")
REPORTS_DIR = Path("data/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def load_silver_pdf_data() -> pd.DataFrame:
    """Loads the silver PDF table from DuckDB into a DataFrame."""
    con = duckdb.connect(str(SILVER_DB_PATH))
    df = con.execute("SELECT * FROM silver_pdf_esg_data").fetchdf()
    con.close()
    return df


def run_validation(df: pd.DataFrame):
    """
    Validates the DataFrame against the schema.
    Uses lazy=True to collect ALL failures, not just the first one.
    Returns (is_valid, failure_cases_df_or_None)
    """
    try:
        pdf_esg_schema.validate(df, lazy=True)
        print("[PASS] All rows passed validation.")
        return True, None
    except pa.errors.SchemaErrors as err:
        print(f"[FAIL] Validation failed. {len(err.failure_cases)} failure case(s) found.\n")
        print(err.failure_cases.to_string())
        return False, err.failure_cases


if __name__ == "__main__":
    df = load_silver_pdf_data()
    print(f"Loaded {len(df)} rows from silver_pdf_esg_data\n")

    is_valid, failures = run_validation(df)

    if failures is not None:
        report_path = REPORTS_DIR / "pdf_validation_failures.csv"
        failures.to_csv(report_path, index=False)
        print(f"\n[OK] Failure report saved to: {report_path}")