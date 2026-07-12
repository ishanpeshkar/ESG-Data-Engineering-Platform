# File: src/validate/business_rules.py

import re
import pandas as pd

# ---- Known false-positive patterns for product_name ----
# Built directly from evidence in our Phase 1 regex output — these are phrases
# we've observed regex incorrectly grabbing instead of real product names.
PRODUCT_NAME_BLOCKLIST_PATTERNS = [
    r"certification",
    r"management system",
    r"declaration number",
    r"^related or",
]

# ---- Suspiciously small GWP values that are likely mis-extracted digits ----
# (e.g. footnote markers, page numbers) rather than real GWP totals.
# This threshold is a judgment call, not a hard scientific rule — documented as such.
SUSPICIOUS_GWP_MAX = 1.0  # values <= this are flagged for manual review, not rejected


def check_product_name(value):
    """Returns a flag reason if product_name looks like a mis-extraction, else None."""
    if pd.isna(value):
        return "missing_product_name"
    for pattern in PRODUCT_NAME_BLOCKLIST_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE):
            return f"product_name_looks_invalid (matched pattern: '{pattern}')"
    return None


def check_gwp_total(value):
    """Returns a flag reason if gwp_total looks suspicious, else None."""
    if pd.isna(value):
        return None  # missing GWP is allowed/expected at this stage, not flagged
    try:
        num = float(value)
    except ValueError:
        return "gwp_total_not_numeric"
    if num < 0:
        return "gwp_total_negative"
    if num <= SUSPICIOUS_GWP_MAX:
        return f"gwp_total_suspiciously_small (value={num}, likely mis-extraction)"
    return None


def apply_business_rules(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies business rules row by row, collecting all flag reasons per row
    into a single '_flags' column (empty list = clean record).
    """
    flags_list = []

    for _, row in df.iterrows():
        row_flags = []

        pn_flag = check_product_name(row.get("product_name"))
        if pn_flag:
            row_flags.append(pn_flag)

        gwp_flag = check_gwp_total(row.get("gwp_total"))
        if gwp_flag:
            row_flags.append(gwp_flag)

        flags_list.append(row_flags)

    df = df.copy()
    df["_flags"] = flags_list
    df["_is_clean"] = df["_flags"].apply(lambda flags: len(flags) == 0)

    return df