# ESG Data Platform — Setup & Run Instructions

Quick reference for starting up and running this project. For full背景, decisions,
and detailed step-by-step history, see `PROJECT_LOG.md`.

---

## 1. Project Structure
esg-data-platform/
├── data/
│   ├── raw_inputs/      # Drop source PDFs/Excel files here
│   ├── bronze/          # Raw extracted JSON (PDF + Excel)
│   ├── silver/           # Cleaned structured data (DuckDB)
│   ├── gold/              # Validated + business-rule-checked data (DuckDB)
│   └── reports/          # Validation failure reports (CSV)
├── src/
│   ├── extract/          # pdf_extractor.py, excel_extractor.py
│   ├── clean/             # pdf_cleaner.py, excel_cleaner.py (parked)
│   └── validate/         # pdf_schema.py, business_rules.py, validate_pdf_data.py,
│                          # build_gold_layer.py
├── airflow/               # Airflow orchestration (Docker-based)
├── PROJECT_LOG.md         # Full detailed project history/decisions
└── INSTRUCTIONS.md        # This file


---

## 2. One-Time Environment Setup (already done, for reference)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows PowerShell
pip install pdfplumber pymupdf pandas openpyxl duckdb python-dotenv pandera
```

---

## 3. Running the Pipeline Manually (Phase 1 + 2 — no orchestration)

Activate your virtual environment first, every time:
```bash
.venv\Scripts\activate
```

Run steps in this order, from the project root:

```bash
# 1. Extraction (bronze layer)
python src/extract/pdf_extractor.py
python src/extract/excel_extractor.py     # currently produces bronze only; silver cleaning parked

# 2. Cleaning (silver layer)
python src/clean/pdf_cleaner.py

# 3. Schema validation
python -m src.validate.validate_pdf_data

# 4. Business rules + gold layer split
python -m src.validate.build_gold_layer
```

**Inputs:** place source `.pdf` / `.xlsx` files into `data/raw_inputs/` before running extraction.

**Outputs to check:**
- `data/bronze/pdf/*.json`, `data/bronze/excel/*.json` — raw extracted data
- `data/silver/esg_silver.duckdb` → table `silver_pdf_esg_data`
- `data/gold/esg_gold.duckdb` → tables `gold_valid_records`, `gold_flagged_records`
- `data/reports/pdf_validation_failures.csv` — only generated if schema validation fails

**Quick DuckDB inspection command:**
```bash
python -c "
import duckdb
con = duckdb.connect('data/gold/esg_gold.duckdb')
print(con.execute('SELECT * FROM gold_flagged_records').fetchdf())
con.close()
"
```
(Swap the table name/db path to inspect any other table.)

---

## 4. Airflow Setup & Access (Phase 3 — Orchestration)

Airflow runs via Docker Compose, in a separate `airflow/` subfolder.

### First-time setup (already done, for reference)
```bash
cd airflow
mkdir dags logs plugins config
# .env file created with: AIRFLOW_UID=50000
# docker-compose.yaml downloaded from official Airflow docs (v2.10.4)
docker compose up airflow-init
```

### Starting Airflow (every time you want to work on it)
```bash
cd airflow
docker compose up -d
```

### Accessing the Airflow UI
- URL: http://localhost:8080
- Login: `airflow` / `airflow` (default credentials)

### Stopping Airflow (when done, to free up resources)
```bash
cd airflow
docker compose down
```

### After editing docker-compose.yaml (e.g. adding volumes/dependencies)
```bash
cd airflow
docker compose down
docker compose up -d
```
(Takes a couple of minutes if additional pip packages need reinstalling inside containers.)

---

## 5. Current Status (as of last update)

- ✅ Phase 0 — Foundations
- ✅ Phase 1 — Manual pipeline (PDF extraction + cleaning working; Excel cleaning parked)
- ✅ Phase 2 — Validation (schema + business rules + gold layer split working)
- 🔄 Phase 3 — Orchestration (Airflow running locally via Docker; DAG build in progress)
- ⬜ Phase 4 — Dashboard
- ⬜ Phase 5 — AI-powered ESG Q&A (RAG)

See `PROJECT_LOG.md` for full detail, decisions, and reasoning behind each step.