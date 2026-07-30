# 🌱 Enterprise ESG Data Platform

A local, end-to-end **Data Engineering platform** for ingesting, validating, and querying ESG / EPD (Environmental Product Declaration) documents — built as a hands-on project to bridge a Data Analysis / GenAI background into real Data Engineering practice.

> Extraction → Cleaning → Validation → Orchestration → Dashboard → AI-Powered Q&A (RAG)
> **100% local. Zero cloud cost. No paid tools or subscriptions.**

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Airflow](https://img.shields.io/badge/Orchestration-Apache%20Airflow-017CEE?logo=apacheairflow&logoColor=white)](https://airflow.apache.org/)
[![DuckDB](https://img.shields.io/badge/Warehouse-DuckDB-FFF000?logo=duckdb&logoColor=black)](https://duckdb.org/)
[![Docker](https://img.shields.io/badge/Container-Docker-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Groq](https://img.shields.io/badge/LLM-Groq%20(Llama%203.3)-F55036)](https://groq.com/)
[![License](https://img.shields.io/badge/License-MIT-green)](#license)

---

## 📖 Why This Project Exists

While interning on an ESG/EPD document assessment project, I wanted to build a parallel, self-directed project to gain real **Data Engineering** skills — extraction pipelines, data validation, orchestration, containerization — while applying my existing **AI / GenAI / RAG** background to a domain I already understood.

Rather than build a generic "toy" ETL pipeline, this project mirrors the shape of a real enterprise ESG platform (the kind built by firms like Deloitte, EY, and Infosys) — scaled down to run entirely on a personal laptop, with zero paid infrastructure.

📄 **[Read the full Executive Summary](./docs/EXECUTIVE_SUMMARY.pdf)** — a 2-page overview of the project, decisions, and key engineering insights.
📄 **[Read the full Technical Deep Dive](./docs/TECHNICAL_DEEP_DIVE.pdf)** — the complete phase-by-phase build log, including every bug, fix, and design decision.

---

## 🏗️ Architecture

```
                     ┌────────────────────────────────────┐
                     │        Source Documents             │
                     │   (Public EPD/ESG/BRSR PDFs, Excel)  │
                     └────────────────┬─────────────────────┘
                                      ▼
                     ┌────────────────────────────────────┐
                     │     BRONZE LAYER (raw extraction)    │
                     │  pdfplumber / pandas → JSON per doc   │
                     └────────────────┬─────────────────────┘
                                      ▼
                     ┌────────────────────────────────────┐
                     │     SILVER LAYER (cleaned data)      │
                     │  Rule-based field extraction → DuckDB │
                     └────────────────┬─────────────────────┘
                                      ▼
                     ┌────────────────────────────────────┐
                     │      GOLD LAYER (validated data)     │
                     │  Pandera schema + business rules      │
                     │  → gold_valid_records                 │
                     │  → gold_flagged_records                │
                     └────────────────┬─────────────────────┘
                                      │
                    Orchestrated end-to-end by Apache Airflow
                                      │
                ┌─────────────────────┴─────────────────────┐
                ▼                                             ▼
   ┌───────────────────────────┐               ┌───────────────────────────┐
   │   Streamlit Dashboard       │               │   RAG Q&A (Groq + Chroma)  │
   │   Metrics, flagged records   │               │   Chunk → Embed → Retrieve │
   │                              │               │   → Grounded LLM Answer     │
   └───────────────────────────┘               └───────────────────────────┘
```

---

## ✨ Features

- 📄 **Multi-format extraction** — PDF (pdfplumber) and Excel (pandas) parsers
- 🧱 **Medallion architecture** — bronze (raw) → silver (cleaned) → gold (validated) layers, all in DuckDB
- ✅ **Two-layer validation** — structural schema checks (Pandera) *and* domain-specific business rules, cleanly separating "is it shaped right" from "is it actually correct"
- 🔄 **Fully orchestrated pipeline** — a single Apache Airflow DAG (containerized via Docker) replacing manual script execution with scheduled, dependency-aware, retryable tasks
- 📊 **Live assessment dashboard** — Streamlit app showing pass/fail rates and flagged-record detail, mirroring a real compliance review tool
- 🤖 **Grounded AI Q&A (RAG)** — ask natural-language questions about your ingested ESG/EPD documents; answers are generated **only** from retrieved document content (via Groq + ChromaDB), with source citations, and the system explicitly declines to answer when the context doesn't support it
- 🔁 **Idempotent by design** — pipeline re-runs produce consistent output rather than duplicating data (a real bug found and fixed during development — see the deep dive)

---

## 🧰 Tech Stack

| Layer | Tool | Why |
|---|---|---|
| Extraction | `pdfplumber`, `pandas`, `openpyxl` | Free, standard, no API cost |
| Storage | `DuckDB` | Zero-setup analytical database, mimics a real warehouse |
| Validation | `pandera` + custom business rules | Lightweight schema validation |
| Orchestration | `Apache Airflow` (Docker + WSL2) | Industry-standard orchestration tool |
| Dashboard | `Streamlit` | Fast to build, queries DuckDB directly |
| Embeddings | `sentence-transformers` (all-MiniLM-L6-v2) | Free, local, no API cost |
| Vector store | `ChromaDB` | Free, local, no server required |
| LLM | `Groq` (Llama 3.3 70B) | Free tier, fast inference, strong quality |

---

## 📂 Project Structure

```
esg-data-platform/
├── data/
│   ├── raw_inputs/       # Source PDFs/Excel files (not tracked in git)
│   ├── bronze/           # Raw extracted JSON
│   ├── silver/           # Cleaned structured data (DuckDB)
│   ├── gold/              # Validated data (DuckDB) — valid + flagged tables
│   ├── vector_store/      # ChromaDB persistent store (RAG embeddings)
│   └── reports/          # Validation failure reports (CSV)
├── src/
│   ├── extract/           # pdf_extractor.py, excel_extractor.py
│   ├── clean/              # pdf_cleaner.py
│   ├── validate/           # pdf_schema.py, business_rules.py, build_gold_layer.py
│   ├── dashboard/          # app.py (Streamlit)
│   └── rag/                # build_vector_store.py, ask_esg.py
├── airflow/
│   ├── dags/esg_pipeline_dag.py
│   └── docker-compose.yaml
├── docs/
│   ├── EXECUTIVE_SUMMARY.pdf
│   └── TECHNICAL_DEEP_DIVE.pdf
├── requirements.txt
├── START_HERE.md          # Quick reboot instructions after time away
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Docker Desktop + WSL2 (Windows) — for the Airflow orchestration layer
- A free [Groq API key](https://console.groq.com/) — for the RAG Q&A layer

### 1. Clone and set up the environment
```bash
git clone https://github.com/<your-username>/esg-data-platform.git
cd esg-data-platform
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### 2. Add your API key
Create a `.env` file in the project root:
```
GROQ_API_KEY=your_key_here
```

### 3. Add source documents
Drop your own public EPD/ESG/BRSR PDFs (or Excel files) into `data/raw_inputs/`.

### 4. Run the pipeline manually
```bash
python src/extract/pdf_extractor.py
python src/clean/pdf_cleaner.py
python -m src.validate.validate_pdf_data
python -m src.validate.build_gold_layer
```

### 5. Build the RAG vector store
```bash
python src/rag/build_vector_store.py
```

### 6. Launch the dashboard
```bash
streamlit run src/dashboard/app.py
```

### 7. (Optional) Run the fully orchestrated pipeline via Airflow
```bash
cd airflow
docker compose up -d
# Open http://localhost:8080  (login: airflow / airflow)
# Trigger the "esg_data_pipeline" DAG
```

---

## 🔍 Key Engineering Insights

A few findings from building this that I think are worth highlighting:

1. **Syntactic validation ≠ semantic validation.** All 8 test documents passed structural schema validation (Pandera), yet business-rule checks correctly flagged 100% of them as semantically unreliable. This proved the *validation system* worked as intended — a schema can confirm a field is shaped correctly while still being factually wrong.
2. **Regex extraction has a hard ceiling.** Naive pattern-matching worked for narrow, consistent fields (e.g. standard references like "EN 15804") but failed on fields that vary by issuer and document layout (e.g. product names). This is concrete evidence for why production ESG platforms use LLM-based, context-aware extraction instead — and it directly motivated the RAG system built in this project.
3. **Idempotency isn't automatic.** An early pipeline version silently duplicated data on every re-run (24 records instead of 8) because bronze files were keyed by timestamp rather than source identity — a realistic, easy-to-miss Data Engineering pitfall.
4. **Grounded RAG must be explicitly disciplined to refuse to guess.** When asked questions with no answer in the ingested documents, the system correctly stated the answer wasn't present rather than falling back on the underlying LLM's general knowledge — verified with deliberate out-of-scope test questions.

Full details on every decision, bug, and fix are in the [Technical Deep Dive](./docs/TECHNICAL_DEEP_DIVE.pdf).

---

## 🗺️ Roadmap / Possible Extensions

- [ ] Replace regex-based PDF field extraction with LLM-based structured extraction
- [ ] Add DAG scheduling (e.g. daily) and failure alerting in Airflow
- [ ] Revisit Excel silver-layer cleaning with proper multi-header parsing
- [ ] Expand source coverage (additional public EPD/ESG document types, government APIs)

---

## 📜 License

This project is licensed under the MIT License — see the [LICENSE](./LICENSE) file for details.

All source documents used for testing are publicly available EPD/ESG/BRSR reports; no confidential or proprietary data is included in this repository.

---

## 🙋 About

Built by **Ishan Peshkar** as a self-directed Data Engineering learning project, informed by real-world ESG/EPD document assessment work.

[LinkedIn](#) · [Portfolio](#) · [Email](#)