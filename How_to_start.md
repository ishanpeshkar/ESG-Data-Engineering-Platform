# 🚀 How to Start This Project — Full Step-by-Step Guide

This is the complete reference for spinning up the entire ESG Data Platform from a cold
start — whether it's been a day or several months since you last touched it. Follow the
sections in order the first time; after that, jump to whichever section you need.

Replace `D:\Ishan-Peshkar-Personel\coding\Projects\ESG-DataEngineering-Platform\esg-data-platform`
below with your actual project path if it ever changes.

---

## 0. Directory Map (know where you are, always)

```
esg-data-platform/                  ← PROJECT ROOT (start here)
│
├── .venv/                          ← Python virtual environment
├── .env                            ← GROQ_API_KEY lives here (never commit this)
│
├── data/
│   ├── raw_inputs/                 ← Drop source PDFs/Excel here BEFORE extraction
│   ├── bronze/pdf/, bronze/excel/  ← Raw extracted JSON (auto-generated)
│   ├── silver/esg_silver.duckdb    ← Cleaned data (auto-generated)
│   ├── gold/esg_gold.duckdb        ← Validated data: valid + flagged tables (auto-generated)
│   ├── vector_store/               ← ChromaDB embeddings for RAG (auto-generated)
│   └── reports/                    ← Validation failure CSVs (auto-generated)
│
├── src/
│   ├── extract/pdf_extractor.py, excel_extractor.py
│   ├── clean/pdf_cleaner.py
│   ├── validate/pdf_schema.py, business_rules.py, validate_pdf_data.py, build_gold_layer.py
│   ├── dashboard/app.py            ← Streamlit dashboard
│   └── rag/build_vector_store.py, ask_esg.py
│
├── airflow/                        ← SEPARATE working directory for Docker/Airflow
│   ├── dags/esg_pipeline_dag.py
│   ├── docker-compose.yaml
│   ├── .env                        ← AIRFLOW_UID lives here (different from root .env)
│   ├── logs/, plugins/, config/
│
├── PROJECT_LOG.md                  ← Full decision/build history
├── INSTRUCTIONS.md                 ← Command reference
├── START_HERE.md                   ← 6-line quick reboot cheat sheet
└── HOW_TO_START.md                 ← This file
```

**Rule of thumb:** anything Python-related (extraction, cleaning, validation, dashboard,
RAG) is run from `esg-data-platform/` (the **project root**). Anything Docker/Airflow
related is run from `esg-data-platform/airflow/` (**one level down**). Mixing these up is
the #1 source of "command not found" or "file not found" errors — always check your
terminal prompt shows the right folder before running a command.

---

## 1. Open a Terminal and Navigate to the Project

```bash
cd D:\Ishan-Peshkar-Personel\coding\Projects\ESG-DataEngineering-Platform\esg-data-platform
```

Confirm you're in the right place:
```bash
dir
```
You should see `data`, `src`, `airflow`, `PROJECT_LOG.md`, etc.

---

## 2. (If Needed) Fix Windows Long Path Issue

If you ever reinstall dependencies and hit an error like:
```
OSError: [WinError 206] The filename or extension is too long
```
Map a short virtual drive letter to the project first:
```powershell
subst X: "D:\Ishan-Peshkar-Personel\coding\Projects\ESG-DataEngineering-Platform\esg-data-platform"
X:
cd X:\
```
Note: this mapping resets every time you restart your PC — just re-run it if needed.
Skip this step entirely if you're not installing new packages.

---

## 3. Activate the Python Virtual Environment

From the **project root**:
```bash
.venv\Scripts\activate
```
Your terminal prompt should now show `(.venv)` at the start of the line — confirming
you're using the project's isolated Python environment, not your system Python.

---

## 4. Confirm Your `.env` File Exists (Project Root)

This file holds your Groq API key and should already exist at:
```
esg-data-platform\.env
```
containing:
```
GROQ_API_KEY=your_key_here
```
If it's missing (e.g. fresh clone on a new machine), recreate it manually — it's
intentionally excluded from git via `.gitignore`.

---

## 5. Add Source Documents (Only If Testing New Files)

Drop any `.pdf` or `.xlsx` files into:
```
data\raw_inputs\
```
Skip this step if you're just re-running the pipeline on existing documents.

---

## 6. Run the Data Pipeline (Manual Mode)

Still from the **project root**, with the venv activated, run these **in order**:

```bash
# 1. Extraction — raw PDFs/Excel -> bronze layer (JSON)
python src/extract/pdf_extractor.py
python src/extract/excel_extractor.py

# 2. Cleaning — bronze -> silver layer (DuckDB)
python src/clean/pdf_cleaner.py

# 3. Schema validation — structural checks
python -m src.validate.validate_pdf_data

# 4. Business rules + gold layer split — silver -> gold layer (DuckDB)
python -m src.validate.build_gold_layer
```

**What each step produces:**
| Step | Output location |
|---|---|
| Extraction | `data/bronze/pdf/*.json`, `data/bronze/excel/*.json` |
| Cleaning | `data/silver/esg_silver.duckdb` → table `silver_pdf_esg_data` |
| Validation | `data/reports/pdf_validation_failures.csv` (only if failures occur) |
| Gold layer | `data/gold/esg_gold.duckdb` → tables `gold_valid_records`, `gold_flagged_records` |

**Quick inspection command** (check any table's contents):
```bash
python -c "
import duckdb
con = duckdb.connect('data/gold/esg_gold.duckdb')
print(con.execute('SELECT * FROM gold_flagged_records').fetchdf())
con.close()
"
```

---

## 7. Build/Refresh the RAG Vector Store

Only needs to be re-run if you've added new source documents or changed chunking logic.
From the **project root**:
```bash
python src/rag/build_vector_store.py
```
This reads bronze PDF JSON, chunks it, embeds it, and stores it in
`data/vector_store/` (ChromaDB). It's idempotent — safe to re-run any time.

---

## 8. Launch the Dashboard (Streamlit)

From the **project root**:
```bash
streamlit run src/dashboard/app.py
```
Opens automatically in your browser at:
```
http://localhost:8501
```
Includes: summary metrics, flagged/valid record tables, and the "Ask a Question" RAG tab.
Press `Ctrl+C` in the terminal to stop it when done.

---

## 9. Start Airflow (Orchestrated Pipeline)

This uses **Docker Desktop**, so make sure Docker Desktop is running first (check the
whale icon in your system tray / taskbar — it should say "Docker Desktop is running").

Navigate to the **airflow subfolder** (different from steps 1–8 above):
```bash
cd airflow
```

Start all containers:
```bash
docker compose up -d
```
Give it 30–60 seconds to fully start (Postgres, Redis, scheduler, webserver, worker,
triggerer all need to come up and pass health checks).

Check status any time:
```bash
docker ps
```
All containers should show `Up` (and eventually `healthy` for postgres/redis).

Open the Airflow UI:
```
http://localhost:8080
```
Login: `airflow` / `airflow`

Find `esg_data_pipeline` in the DAG list, toggle it **on** (if paused), and click the
▶ (trigger) button to run the full pipeline end-to-end through Airflow instead of
manually.

**Stopping Airflow when done** (frees up RAM/CPU):
```bash
cd airflow
docker compose down
```

---

## 10. Full Cold-Start Checklist (Copy-Paste Order)

If you're starting completely fresh after a long break, here's the full sequence,
top to bottom:

```bash
# 1. Navigate to project
cd D:\Ishan-Peshkar-Personel\coding\Projects\ESG-DataEngineering-Platform\esg-data-platform

# 2. Activate virtual environment
.venv\Scripts\activate

# 3. Run the pipeline manually (or skip and use Airflow instead — step 9 below)
python src/extract/pdf_extractor.py
python src/clean/pdf_cleaner.py
python -m src.validate.validate_pdf_data
python -m src.validate.build_gold_layer

# 4. Rebuild the RAG vector store
python src/rag/build_vector_store.py

# 5. Launch the dashboard
streamlit run src/dashboard/app.py
```

In a **separate terminal**, if you also want Airflow running:
```bash
cd D:\Ishan-Peshkar-Personel\coding\Projects\ESG-DataEngineering-Platform\esg-data-platform\airflow
docker compose up -d
```

---

## 11. Troubleshooting Quick Reference

| Symptom | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError` | venv not activated | Run `.venv\Scripts\activate` |
| `localhost:8080` won't load | Airflow containers still starting | Wait 1–2 min, check `docker ps` for `healthy` status |
| Docker shows 0 containers | Docker Desktop reset/restarted | `cd airflow` then `docker compose up -d` (re-pulls images if needed) |
| `WinError 206` during pip install | Windows long path limit | Use the `subst X:` trick from Step 2 |
| Dashboard shows unexpected row counts | Pipeline re-run duplicated data | Check `data/bronze/pdf/` for duplicate/old files; extraction is filename-keyed (idempotent) as of the Phase 4 fix |
| `GROQ_API_KEY not found` | `.env` missing or in wrong folder | Confirm `.env` is in **project root**, not inside `src/` or `airflow/` |

---

## 12. When You're Done for the Day

```bash
# Stop the dashboard: Ctrl+C in its terminal

# Stop Airflow (optional, saves resources)
cd airflow
docker compose down

# Deactivate the virtual environment
deactivate
```

Your data (DuckDB files, vector store, bronze/silver/gold layers) all persist on disk —
nothing is lost by shutting everything down.