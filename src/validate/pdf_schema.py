# File: src/validate/pdf_schema.py

import pandera.pandas as pa
from pandera.pandas import Column, Check, DataFrameSchema

# ---- Validation schema for silver_pdf_esg_data ----
# This defines what a "valid" cleaned ESG/EPD record looks like.
# Nullable=True means the field is allowed to be missing, but if present,
# it must satisfy the given Check.

pdf_esg_schema = DataFrameSchema(
    columns={
        "_source_file": Column(
            str,
            nullable=False,
            checks=Check.str_length(min_value=1),
        ),
        "_extracted_at": Column(
            str,
            nullable=False,
        ),
        "page_count": Column(
            int,
            nullable=False,
            checks=Check.greater_than(0),
        ),
        "char_count": Column(
            int,
            nullable=False,
            checks=Check.greater_than_or_equal_to(0),
        ),
        "product_name": Column(
            str,
            nullable=True,
            checks=Check.str_length(max_value=100),
        ),
        "declared_unit": Column(
            str,
            nullable=True,
        ),
        "reporting_period": Column(
            str,
            nullable=True,
        ),
        "gwp_total": Column(
            str,   # stored as string in DuckDB currently; we'll validate numeric-ness via regex check
            nullable=True,
            checks=Check.str_matches(r"^-?\d+(\.\d+)?$"),
        ),
        "standard_reference": Column(
            str,
            nullable=True,
            checks=Check.str_matches(r"^(EN\s?15804.*|ISO\s?14025|ISO\s?21930)$"),
        ),
    },
    strict=False,   # allow extra columns without failing
    coerce=False,
)