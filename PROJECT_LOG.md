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



## Phase 3 — Orchestration

### Decision: Prefect vs Airflow
- Initially considered Prefect for simplicity (pure Python, no Docker needed, native
  Windows support)
- **Decision reversed:** chose Airflow instead, since it's more commonly required in
  Data Engineering job listings and is a stronger resume/interview signal. Accepted the
  added setup complexity (Docker + WSL2 required on Windows) as a worthwhile tradeoff
  for industry-relevance over convenience.

### Step 3.1 — WSL2 + Docker Setup
Commands run:
```bash
wsl --update
wsl --set-default-version 2
docker --version
docker run hello-world
docker compose version
```
- WSL2 updated to version 2.7.10, set as default version successfully
- Installed Docker Desktop (with WSL2 engine integration)
- Verified with `docker --version` → Docker version 29.1.3
- Verified with `docker run hello-world` → success, confirmed Docker daemon working
  end-to-end (pull image → create container → run → stream output)
- Verified with `docker compose version` → Docker Compose v5.0.1
- **Result:** No errors. Docker + Compose fully working on first attempt.
- **Status:** Done

### Step 3.2 — Airflow Setup via Docker Compose
Plan/commands:
```bash
mkdir airflow
cd airflow
mkdir dags logs plugins config
```
Downloaded official Airflow docker-compose.yaml (v2.10.4):
```powershell
Invoke-WebRequest -Uri "https://airflow.apache.org/docs/apache-airflow/2.10.4/docker-compose.yaml" -OutFile "docker-compose.yaml"
```
Created `.env` file inside `airflow/` folder:
AIRFLOW_UID=50000

- **Decision/note:** hardcoded `AIRFLOW_UID=50000` since Windows has no direct equivalent
  of the Linux user-ID auto-detection the official docs assume — this is a standard,
  documented workaround, not a hack.

Initialization and startup:
```bash
docker compose up airflow-init
docker compose up -d
```
Then accessed Airflow UI at `http://localhost:8080` (default login: airflow / airflow).

**Result:** `docker compose up airflow-init` completed successfully (downloaded Airflow
images, initialized metadata DB, created default admin user). `docker compose up -d`
started all services in background. Airflow UI accessible at http://localhost:8080,
logged in successfully with default credentials.

**Status:** Done

### Step 3.3 — Connect Airflow to Project Code
- Edited `airflow/docker-compose.yaml`:
  - Added volume mount: `../:/opt/airflow/esg_project` — makes the entire project folder
    visible inside Airflow containers
  - Set `_PIP_ADDITIONAL_REQUIREMENTS: pdfplumber pandas openpyxl duckdb pandera` so
    Airflow's containers have the same dependencies as the local venv
- Restarted with `docker compose down` then `docker compose up -d`
- Verified mount with:
```bash
  docker exec -it airflow-airflow-scheduler-1 ls /opt/airflow/esg_project
```
  → Confirmed all project folders/files visible inside the container
- **Status:** Done

### Step 3.5 — First DAG Trigger
- Triggered `esg_data_pipeline` DAG manually via Airflow UI
- `extract_pdf` succeeded; `clean_pdf` failed with:
  `ModuleNotFoundError: No module named 'duckdbQ'`
- **Root cause:** stray typo in local `src/clean/pdf_cleaner.py` — line 5 read
  `import duckdbQ` instead of `import duckdb`. Not an Airflow/Docker issue — this was
  a pre-existing typo in the file that hadn't been re-run locally since introduced.
  Airflow surfaced it because it executes the actual script fresh via BashOperator.
- Downstream tasks (`validate_pdf`, `build_gold_layer`) correctly showed
  `upstream_failed` status — demonstrating Airflow's dependency enforcement working
  as intended (it correctly refused to run tasks whose prerequisite failed)
- **Fix:** corrected import statement, re-triggered DAG
- **Status:** In progress — pending confirmation of full successful run

### Step 3.5 — First Successful End-to-End DAG Run
- Fixed the `duckdbQ` typo in `pdf_cleaner.py`, re-triggered the DAG fresh
- All 4 tasks completed successfully in order: extract_pdf → clean_pdf → validate_pdf →
  build_gold_layer (each shown green in Airflow Graph view)
- Verified output correctness by checking `gold_valid_records` / `gold_flagged_records`
  row counts in DuckDB — matched the known-correct manual run result (0 valid, 8 flagged)

**Milestone:** the full Phase 1 + Phase 2 pipeline (extraction, cleaning, schema
validation, business-rule validation, gold layer split) is now running as a single
orchestrated Airflow DAG instead of 4 manual script executions. This is the core
"data engineering" deliverable of the project — a real, working pipeline with enforced
task ordering, retry logic, and full execution/log history per run.

**Status: Phase 3 core orchestration — Done.**

## Phase 3 — COMPLETE ✅

Summary: Set up WSL2 + Docker Desktop, initialized Apache Airflow via Docker Compose,
mounted project code into containers, built a DAG (`esg_data_pipeline`) wiring the full
Phase 1+2 pipeline (extract_pdf -> clean_pdf -> validate_pdf -> build_gold_layer) as a
single orchestrated flow with enforced task dependencies and retry logic. Fixed one
real bug (stray typo) surfaced during first DAG execution. Verified full pipeline runs
successfully end-to-end, output matching manual execution results.

Committed with message: "feat: orchestrate ESG pipeline with Airflow (Phase 3)"



## Phase 4 — Dashboard

### Step 4.1 — Install Streamlit
Commands run:
```bash
pip install streamlit
streamlit hello
```
- Installed cleanly, `streamlit hello` opened the built-in demo app in browser at
  http://localhost:8501, confirming install worked correctly
- **Status:** Done

### Step 4.2 — Build Dashboard + Idempotency Bug Discovered
- Built `src/dashboard/app.py` using Streamlit — reads gold_valid_records and
  gold_flagged_records from DuckDB, shows summary metrics (total/valid/flagged/pass rate),
  and tabbed views with a flag-reason filter
- Ran successfully, dashboard rendered correctly

**Bug discovered:** dashboard showed 24 total documents instead of the expected 8.
**Root cause:** `pdf_extractor.py` saved bronze JSON files with a timestamp in the
filename, so every pipeline run (including repeated Airflow DAG triggers) created NEW
files instead of overwriting existing ones — silver/gold layers then processed
duplicated bronze records across multiple runs.
**Concept:** lack of **idempotency** — re-running the pipeline did not produce the same
result as running it once, a real and common data engineering issue (especially relevant
for scheduled/repeated pipeline runs, where bronze data would grow unbounded with
duplicates over time).

**Fix attempt 1:** removed timestamp from bronze filename — but left a stray reference
to the old `timestamp` variable in `out_path`, causing `NameError: name 'timestamp' is
not defined`.
**Fix attempt 2 (final):** corrected `save_bronze_record()` fully to build the output
path from the source filename only. Also fixed an unrelated `datetime.utcnow()`
deprecation warning by switching to `datetime.now(timezone.utc)`.

Verified fix: cleared bronze folder, re-ran full pipeline, dashboard confirmed back to
correct 8 total documents (0 valid, 8 flagged) — idempotency restored.

**Phase 4 status: COMPLETE.**


## Phase 5 — AI-powered ESG Q&A (RAG)

### Decision: LLM Provider
Considered a paid API (OpenAI/Anthropic) vs fully local (Ollama) vs Groq.
**Chose Groq** — free tier, fast inference, hosts strong open-weight models (Llama family)
via an OpenAI-compatible API, keeping the project fully cost-free while avoiding the
hardware/setup overhead of running models locally via Ollama.


### Incident — Docker Desktop Container/Volume Wipe
- Opened Docker Desktop and found all containers and volumes gone (unclear root cause —
  suspected Docker Desktop update or reset). Confirmed via `docker ps -a` (empty) and
  `docker volume ls` (empty).
- **Reassurance/learning:** project logic was NOT lost — docker-compose.yaml, .env, and
  the DAG file all live on the actual filesystem (mounted volumes), not inside Docker's
  internal storage. Only lost: Airflow's run history and default admin login.
- **Fix:** re-ran `docker compose up airflow-init` (re-pulled images, ~400MB, recreated
  Postgres metadata DB and admin user) then `docker compose up -d`. Confirmed containers
  running via `docker ps` (scheduler, webserver, worker, triggerer, postgres, redis all up).
- **Status:** Recovered (webserver took ~1-2 min after startup to pass health checks
  before UI became accessible — normal startup behavior, not a bug)

### Step 5.1 — Groq API Setup + Test Call
- Installed Groq SDK: `pip install groq`
- Created `.env` in project root with `GROQ_API_KEY` (excluded from git via existing
  .gitignore)
- Built `src/rag/test_groq_connection.py` — simple test call using
  `llama-3.3-70b-versatile` model
- Ran successfully, received a correct, coherent one-sentence answer about EPDs
- Confirms Groq API key, SDK, and connectivity all working end-to-end
- **Status:** Done

- Airflow UI confirmed accessible again at http://localhost:8080. Re-triggered
  `esg_data_pipeline` DAG — all 4 tasks (extract_pdf, clean_pdf, validate_pdf,
  build_gold_layer) completed successfully.
- **Docker incident fully resolved.**

### Step 5.2.1 — Install Embedding/Vector Store Dependencies
- Ran `pip install sentence-transformers chromadb`
- **Error hit:** `OSError: [WinError 206] The filename or extension is too long` while
  installing `torch` (a dependency of sentence-transformers) — caused by Windows' default
  260-character MAX_PATH limit being exceeded by deeply nested folders inside the torch
  package, combined with an already-long project path.
- **Fix (no restart required):** used `subst X: "<full project path>"` to map a short
  virtual drive letter to the project folder, shortening effective paths underneath it
  below the 260-char limit. Re-ran install from `X:\` — succeeded.
- **Note:** `subst` mapping only persists until the PC restarts — needs to be re-run each
  fresh session (added reminder to `START_HERE.md`).
- **Status:** Done

### Step 5.2.2 — Chunking + Embedding (Vector Store)
- Built `src/rag/build_vector_store.py`:
  - Loads bronze PDF JSON records
  - Chunks page text by character count (800 chars, 150 overlap) to preserve context
    across chunk boundaries
  - Embeds chunks using `all-MiniLM-L6-v2` (free, local, ~80MB, sentence-transformers)
  - Stores embeddings + text + metadata (source_file, page_number) in a persistent
    ChromaDB collection (`esg_documents`)
  - Collection is deleted and recreated on each run for idempotency (same lesson as
    the bronze/gold layer duplication bug earlier)
- Ran successfully: 8 bronze PDF records -> 849 chunks -> all embedded and stored
- Minor Windows-only warning about symlink support in HuggingFace cache — cosmetic,
  no functional impact (would just save disk space if enabled via Developer Mode)
- **Status:** Done

### Step 5.3 — Retrieval + Groq Q&A (First Working RAG Query)
- Built `src/rag/ask_esg.py`:
  - Embeds the user's question with the same model used for chunks (all-MiniLM-L6-v2)
  - Retrieves top-5 most similar chunks from ChromaDB (`esg_documents` collection)
  - Builds a grounded prompt instructing the LLM to answer ONLY from retrieved context
    and to cite sources, avoiding hallucination
  - Sends prompt to Groq (llama-3.3-70b-versatile) for final answer generation
  - Prints answer + retrieved source files/pages for transparency

**Test query:** "What standards are referenced in these EPD documents?"
**Result:** Correctly identified EN 15804, International EPD System General Programme
Instructions v5.0, and PCR 2019:14 — all grounded in actual retrieved chunks with correct
source file + page number citations. Multiple standards synthesized from different
documents in one coherent answer.

**Milestone:** first fully working end-to-end RAG query. This is a clear, demonstrable
upgrade over the naive regex-based `standard_reference` field from Phase 1 — where regex
could only catch a single rigid pattern per document, the RAG system retrieves and
synthesizes information contextually across multiple documents and phrasings, directly
validating the reasoning we documented back in Phase 1 for why LLM-based extraction/
retrieval outperforms keyword matching on real-world document variance.

- **Status:** Done


### Step 5.4 — Interactive Q&A in Dashboard
- Added a "💬 Ask a Question" tab to `src/dashboard/app.py`, reusing the same
  embedding model, ChromaDB collection, and Groq client from `ask_esg.py`
  (cached via `st.cache_resource` so models/clients load once, not per interaction)
- Added a text input + "Ask" button, displaying the generated answer and retrieved
  source documents/pages directly in the dashboard

**Test query:** "what is the epd and esg relation and how does brsr fits into it?"
**Result:** Retrieved chunks from both an EPD document and the BRSR report (cross-source
retrieval working correctly). The model explicitly noted that the provided context did
not directly state the EPD-ESG relationship, then reasoned carefully from what it did
retrieve to construct an accurate, well-cited answer (EPD as a specific environmental
sub-report, BRSR as the broader ESG-attribute report) — demonstrating appropriate
epistemic honesty rather than hallucinating a confident but ungrounded answer.

**Status:** Done. Phase 5 core (retrieval + generation + interactive UI) fully working.


### Step 5.5 — Edge Case Testing (Out-of-Scope Questions)

Tested the system's behavior when asked questions with no real answer in the ingested
documents, to verify it doesn't hallucinate using the underlying LLM's general training
knowledge.

**Test 1:** "What is the carbon footprint of Apple's iPhone 15 supply chain?"
**Result:** Correctly identified that the context only covered TCS's sustainability
report and an unrelated life cycle assessment document, explicitly stated Apple/iPhone
15 was not mentioned, and did not fabricate an answer.

**Test 2:** "What is the current stock price of Tesla?"
**Result:** Correctly identified the context was unrelated (TCS reporting/sustainability
documents), explicitly stated Tesla was not mentioned, and did not fabricate a stock
price.

**Key insight:** the vector retriever always returns its top-K nearest chunks regardless
of true relevance (cosine similarity has no built-in "nothing matches" threshold) — so
in both tests, *irrelevant* chunks were still retrieved. The critical safeguard is the
generation step: the prompt explicitly instructs the LLM to answer ONLY from provided
context and admit when the answer isn't present, which correctly overrode the LLM's
general pretrained knowledge about Tesla/Apple in both cases. This confirms the grounding
discipline built into `build_prompt()` (Step 5.3) works as intended even under adversarial/
out-of-scope questioning.

**Status:** Done. RAG system verified to correctly refuse ungrounded answers rather than
hallucinate.


*(to be filled in as we go)*