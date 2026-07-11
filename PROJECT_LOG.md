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

---

## Phase 2 — Data Modeling + Validation
*(to be filled in as we go)*