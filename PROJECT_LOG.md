# Enterprise ESG Data Platform — Project Log

## 1. Backstory & Motivation

Currently interning on an ESG/EPD document analysis project — extracting data from
sustainability documents and assessing them against regulatory rulesets. Wanted to build
a parallel personal project to (a) gain hands-on Data Engineering skills beyond my
ML/GenAI/RAG background, and (b) apply that DE skillset to a domain I already understand
deeply from the internship, without using any real/confidential company data.

Goal: build "Enterprise ESG Data Platform" — a scaled-down, personal, fully local version
of the kind of ESG data platform companies like Deloitte/EY/Infosys build for clients.

## 2. Constraints & Ground Rules
- No paid tools/subscriptions (no AWS) — everything runs locally
- No real internship data used anywhere — only public EPD/ESG/BRSR documents
- Learning-first: build in phases, prove each layer works before adding complexity
- Domain reused from internship (ESG/EPD), but tech stack and code built independently

## 3. Tech Stack Decisions
| Layer | Tool | Why |
|---|---|---|
| Extraction | pdfplumber, pandas/openpyxl | Free, standard, no API cost |
| Storage | Local filesystem + DuckDB | Zero-setup analytical DB, mimics real warehouse |
| (Planned) Validation | Great Expectations / pandera | Phase 2 |
| (Planned) Orchestration | Airflow / Prefect | Phase 3 |
| (Planned) Dashboard | Streamlit / Metabase | Phase 4 |
| (Planned) AI Q&A | Custom RAG (reusing existing GenAI skills) | Phase 5 |

---

## Phase 0 — Foundations
**Status:** Completed prior to formal logging.
Learned: ETL vs ELT, data lake vs warehouse vs lakehouse, Docker basics, medallion
architecture (bronze/silver/gold) pattern.

---

## Phase 1 — Manual Pipeline (No Orchestration)

### Step 1.1 — Environment Setup
- Created project folder structure (`data/`, `src/extract`, `src/clean`, etc.)
- Set up Python virtual environment
- Installed: `pdfplumber`, `pymupdf`, `pandas`, `openpyxl`, `duckdb`, `python-dotenv`
- **Status:** Done

### Step 1.2 — Source Documents
- Collected public EPD/ESG/BRSR PDFs (ABB, Lival OY, ecoinvent, PolyCo, Tata Steel,
  a company BRSR report, GRI report, a network cable EPD) — 8 PDFs total
- Decision: use only public documents, never real internship files
- **Status:** Done

### Step 1.3 — Extraction (Bronze Layer)
- Built `src/extract/pdf_extractor.py` — extracts raw text + tables per page using
  pdfplumber, saves as timestamped JSON in `data/bronze/pdf/`
- Built `src/extract/excel_extractor.py` — extracts all sheets/rows via pandas, saves
  as timestamped JSON in `data/bronze/excel/`
- Both ran successfully on first real test
- **Key decision:** bronze layer = raw/untouched data, no cleaning applied yet
- **Status:** Done

### Step 1.4 — Cleaning (Silver Layer)

**Excel cleaner (`src/clean/excel_cleaner.py`):**
- Attempt 1: Failed — `InvalidInputException: Could not convert string 'Tin' to INT32`
  - Root cause: real-world ESG Excel templates (e.g. Conflict Minerals Reporting
    Template) mix text and numbers in the same column due to multi-row headers/section
    labels — DuckDB couldn't infer one strict type per column.
  - Fix attempt: force all columns to string type via `df[col].apply(...)`
- Attempt 2: Failed — `ValueError: The truth value of a Series is ambiguous`
  - Root cause: duplicate column names (multiple "Unnamed: X" columns collapsing to the
    same name) meant `df[col]` returned a DataFrame, not a Series
  - Fix attempt: de-duplicate column names + switch to `.applymap()` for elementwise casting
- Attempt 3: Still failed.
  - **Decision:** parked Excel silver-layer cleaning for now. Real-world messy ESG Excel
    templates need more deliberate handling (proper multi-header parsing) — revisit later
    once schema-driven approach or cleaner sample sheets are available. Bronze extraction
    for Excel already succeeded, which proved the core concept.

**PDF cleaner (`src/clean/pdf_cleaner.py`):**
- Built naive rule-based (regex) field extraction for: product_name, declared_unit,
  reporting_period, gwp_total, standard_reference
- Ran successfully on all 8 PDFs, wrote to DuckDB table `silver_pdf_esg_data`

**Result / Eureka moment:**
`standard_reference` worked reasonably well (caught EN 15804 variants across documents).
Everything else was inconsistent or wrong — e.g. `product_name` grabbed section headings
or mid-sentence fragments instead of actual product names; `gwp_total` was almost entirely
`NaN` because GWP values live in tables or use inconsistent phrasing across issuers (ABB,
Tata Steel, ecoinvent, GRI all format documents completely differently).

**Insight:** this is direct, hands-on proof of why production ESG platforms (like the one
at my internship) use LLM-based extraction against a defined schema instead of naive
keyword/regex matching — an LLM can infer meaning from context; regex can't handle format
variance across issuers. This mirrors a real problem I'm separately investigating at work
(inconsistent LLM extraction field counts across runs).

- **Status:** Done (baseline). Next: iterate to improve regex where cheap wins exist,
  before moving to Phase 2 (validation).


### Step 1.4 — Cleaning (Silver Layer) — Regex Tuning Iteration

Attempted to improve PDF field extraction accuracy:
- Restricted header-style field search (product_name, declared_unit, reporting_period)
  to the first 3 pages of each document, since EPDs place summary info near the front
- Added max_len caps to reject clearly-wrong matches (whole sentences vs short values)
- Tightened gwp_total pattern to also catch "kg CO2-eq" phrasing, not just literal "GWP total"

**Bug hit:** Used `^`/`$` line anchors in regex without `re.MULTILINE` flag — anchors
defaulted to matching only the start/end of the entire text blob (not per-line), so
product_name matched nothing at all (100% None).
**Fix:** Added `re.MULTILINE` flag to `re.search()` call in `extract_field()`.

**Result after fix:**
- gwp_total and reporting_period improved meaningfully (real values now captured for
  several documents, e.g. "5 years", "2030-06-19", "2.22")
- standard_reference remained reliable across EN 15804 variants
- product_name remained unreliable even after fixes — different issuers either omit an
  explicit "Product Name:" label entirely, or use inconsistent phrasing/placement, which
  regex cannot resolve since it has no contextual understanding of the document layout

**Decision:** Stop regex tuning here — diminishing returns. This result gives concrete,
reproducible evidence that keyword/regex extraction breaks down on real-world document
variance across issuers, motivating the move to schema-driven LLM extraction in a later
phase. This mirrors the actual extraction-consistency problem I'm separately investigating
at my internship (LLM output varying between runs on the same document).

**Phase 1 status: COMPLETE.**
- Bronze layer: PDF ✅, Excel ✅
- Silver layer: PDF ✅ (rule-based, with documented limitations), Excel parked (messy
  real-world template, revisit later with schema-driven approach)
---


## Phase 2 — Data Modeling + Validation

### Step 2.1 — Define Validation Schema
- Installed `pandera`. Hit a transient PyPI 503 error on first attempt — retried, worked.
- Built `src/validate/pdf_schema.py` defining a `DataFrameSchema` for `silver_pdf_esg_data`:
  hard requirements on `_source_file`, `page_count`, `char_count`; nullable/conditional
  checks on `product_name` (max length), `gwp_total` (numeric-pattern regex), and
  `standard_reference` (must match known standards like EN 15804 / ISO 14025)
- **Decision:** validated `gwp_total` as a string with a numeric regex pattern rather than
  casting to float, to avoid type-casting crashes (learned from Excel cleaning failures
  earlier) since the DuckDB column currently stores mixed/text values
- **Status:** Done

### Step 2.2 — Run Validation
- Built `src/validate/validate_pdf_data.py` — loads silver_pdf_esg_data from DuckDB, runs
  it against the schema using `lazy=True` (collects all failures, not just first)
- **Bug hit:** `ModuleNotFoundError: No module named 'pdf_schema'` when running as a module
  - **Fix:** added `__init__.py` to `src/` and `src/validate/`, changed import to
    `from src.validate.pdf_schema import pdf_esg_schema`
- **Result:** All 8 rows PASSED validation on first successful run
- **Cleanup:** Pandera raised a deprecation warning for top-level imports; updated both
  files to use `pandera.pandas` instead of `pandera` directly (covers both `pa.` usage and
  `Column`/`Check`/`DataFrameSchema` imports)

**Key insight (important):** All rows passing validation does NOT mean the data is
correct — it means the data is *structurally well-formed*. E.g. `gwp_total` values like
`16` and `2` passed because they're valid numbers, even though we have strong evidence
(from Phase 1 regex analysis) that these are likely mis-extracted footnote digits, not
real GWP values. Similarly, `product_name` values like "related or management
system-related certifications" passed (under 100 chars) despite clearly not being real
product names. This demonstrates the gap between **syntactic validation** (is it
shaped correctly) and **semantic validation** (does it mean what it should) — rule-based
schemas alone cannot close that gap; it requires either much more specific business rules
or contextual/LLM-based understanding.

- **Status:** Done



### Step 2.3 — Business Rules + Gold Layer Split
- Built `src/validate/business_rules.py` — encodes domain-specific rules derived directly
  from observed Phase 1 extraction failures: product_name blocklist patterns
  (certification, management system, declaration number, etc.), and a "suspiciously
  small GWP" threshold to flag likely mis-extracted footnote digits
- Built `src/validate/build_gold_layer.py` — loads silver data, re-runs pandera schema
  validation as a safety net, applies business rules, splits into `gold_valid_records`
  and `gold_flagged_records` DuckDB tables

**Result:** 0 clean records, 8/8 flagged records.
**Interpretation:** This is expected and correct, not a bug. The business rules were
built directly from known weaknesses in the Phase 1 regex-based product_name extraction
(no real product-name label consistency across issuers). The validation layer is
correctly surfacing that 100% of our current extraction is semantically unreliable for
product_name — proving the schema/business-rule validation logic works as intended, and
strongly reinforcing the case for LLM-based structured extraction in a later phase.

**Key takeaway for documentation:** a validation layer's job is not to make the data look
clean — it's to honestly expose where the data is NOT trustworthy. A 0% pass rate here is
a successful test of the validation logic, not a failure of the project.

**Phase 2 status: COMPLETE.**
- Schema-level (structural) validation: implemented, passing
- Business-rule (semantic) validation: implemented, correctly flagging known weak points
- Gold layer: valid/flagged split implemented and working


*(to be filled in as we go)*