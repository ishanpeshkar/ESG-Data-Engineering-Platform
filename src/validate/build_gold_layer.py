# File: src/validate/build_gold_layer.py

import duckdb
import pandas as pd
import pandera.pandas as pa
from pathlib import Path

from src.validate.pdf_schema import pdf_esg_schema
from src.validate.business_rules import apply_business_rules

SILVER_DB_PATH = Path("data/silver/esg_silver.duckdb")
GOLD_DB_PATH = Path("data/gold/esg_gold.duckdb")
GOLD_DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_silver_pdf_data() -> pd.DataFrame:
    con = duckdb.connect(str(SILVER_DB_PATH))
    df = con.execute("SELECT * FROM silver_pdf_esg_data").fetchdf()
    con.close()
    return df


def run_schema_validation(df: pd.DataFrame):
    """
    Runs pandera schema validation. Since we already confirmed all rows pass
    structurally (Step 2.2), this mainly acts as a safety net going forward
    (e.g. if new/different documents get added later).
    """
    try:
        pdf_esg_schema.validate(df, lazy=True)
        return True, None
    except pa.errors.SchemaErrors as err:
        return False, err.failure_cases


def build_gold_tables(df: pd.DataFrame):
    """
    Applies business rules, splits into gold_valid_records and
    gold_flagged_records, writes both to the gold DuckDB database.
    """
    df_with_flags = apply_business_rules(df)

    valid_df = df_with_flags[df_with_flags["_is_clean"]].drop(columns=["_flags", "_is_clean"])
    flagged_df = df_with_flags[~df_with_flags["_is_clean"]].copy()

    # Convert list-of-strings _flags column into a single readable string
    # (DuckDB/CSV don't handle Python lists cleanly)
    flagged_df["_flags"] = flagged_df["_flags"].apply(lambda flags: "; ".join(flags))
    flagged_df = flagged_df.drop(columns=["_is_clean"])

    con = duckdb.connect(str(GOLD_DB_PATH))
    con.execute("CREATE OR REPLACE TABLE gold_valid_records AS SELECT * FROM valid_df")
    con.execute("CREATE OR REPLACE TABLE gold_flagged_records AS SELECT * FROM flagged_df")
    con.close()

    return valid_df, flagged_df


if __name__ == "__main__":
    df = load_silver_pdf_data()
    print(f"Loaded {len(df)} rows from silver_pdf_esg_data\n")

    schema_ok, schema_failures = run_schema_validation(df)
    if not schema_ok:
        print("[WARN] Schema-level validation failures found:")
        print(schema_failures.to_string())
    else:
        print("[OK] Schema-level validation passed for all rows.\n")

    valid_df, flagged_df = build_gold_tables(df)

    print(f"[RESULT] Clean records: {len(valid_df)}")
    print(f"[RESULT] Flagged records: {len(flagged_df)}\n")

    if len(flagged_df) > 0:
        print("Flagged records and reasons:")
        print(flagged_df[["_source_file", "product_name", "gwp_total", "_flags"]].to_string())

    print(f"\n[OK] Gold tables written to {GOLD_DB_PATH}")