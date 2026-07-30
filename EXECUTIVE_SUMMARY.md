---
title: "Enterprise ESG Data Platform"
subtitle: "Executive Summary — A Personal Data Engineering Portfolio Project"
author: "Ishan Peshkar"
date: "July 2026"
---

# Enterprise ESG Data Platform
### Executive Summary

## Background

While working as an intern on an ESG/EPD (Environmental Product Declaration) document
analysis project — extracting data from sustainability documents and assessing it
against regulatory rulesets — I wanted to deepen my Data Engineering skills through a
parallel personal project. Rather than build a generic pipeline, I chose to build a
scaled-down, fully local, and completely original version of the kind of ESG data
platform that firms like Deloitte, EY, and Infosys build for enterprise clients.

**Goal:** learn real Data Engineering practices (extraction, validation, orchestration,
data modeling) while applying my existing AI/GenAI/RAG background to a domain I already
understood — without using any real company data, and without any paid tools or cloud
subscriptions.

## What Was Built

A complete, local, end-to-end data platform processing real public ESG/EPD documents:

```
 PDF/Excel Sources → Bronze (raw) → Silver (cleaned) → Gold (validated)
        │                                                     │
        └──────────────► Orchestrated by Apache Airflow ◄─────┘
                                     │
                    ┌────────────────┴────────────────┐
                    ▼                                  ▼
          Streamlit Dashboard                RAG-based Q&A (Groq LLM)
       (assessment metrics, flags)        (grounded document Q&A)
```

**Core components:**

- **Extraction** — PDF (pdfplumber) and Excel (pandas) parsers producing raw "bronze"
  records
- **Cleaning** — rule-based field extraction into structured "silver" tables (DuckDB)
- **Validation** — a two-layer validation system: structural schema checks (Pandera) and
  domain-specific business rules, producing a "gold" layer split into valid vs. flagged
  records
- **Orchestration** — the full pipeline runs as a single Apache Airflow DAG (containerized
  via Docker/WSL2), replacing manual script execution with a scheduled, dependency-aware,
  retryable pipeline
- **Dashboard** — a Streamlit application surfacing pass/fail metrics and flagged-record
  detail, mirroring a real compliance-assessment interface
- **AI-Powered Q&A (RAG)** — documents are chunked, embedded locally (sentence-transformers),
  and stored in a vector database (ChromaDB); user questions are answered by an LLM (Groq)
  strictly grounded in retrieved document content, with source citations

## Key Engineering Insights

This project intentionally treated failures as data, not noise. A few findings stood out:

1. **Syntactic validation ≠ semantic validation.** A schema can confirm a field is
   "shaped" correctly (e.g. a valid number) while still being factually wrong. All 8
   documents passed structural validation, yet business-rule checks correctly flagged
   100% of them as semantically unreliable — proving the validation *system* worked
   exactly as intended, even though the *data* wasn't yet trustworthy.
2. **Regex-based extraction has a hard ceiling.** Naive keyword/pattern extraction worked
   for narrow, consistent fields (e.g. standard references) but failed on fields where
   real-world documents vary by issuer and layout (e.g. product names). This is direct,
   reproducible evidence for why production ESG platforms — including the one at my
   internship — rely on LLM-based, context-aware extraction instead.
3. **Idempotency matters.** An early version of the pipeline silently duplicated data on
   every re-run (24 records instead of 8) because bronze files were timestamped rather
   than keyed by source. Fixing this was a concrete, practical lesson in a core Data
   Engineering principle: pipelines should produce the same result no matter how many
   times they run.
4. **Grounded RAG correctly refuses to guess.** When asked out-of-scope questions (e.g.
   about a company never present in the ingested documents), the system explicitly
   stated the answer wasn't present in its retrieved context rather than falling back on
   the underlying LLM's general knowledge — the core discipline that separates a real RAG
   system from simply calling an LLM directly.

## Tech Stack (100% local, zero cost)

| Layer | Tool |
|---|---|
| Extraction | pdfplumber, pandas |
| Storage | DuckDB (silver & gold layers) |
| Validation | Pandera (schema) + custom business rules |
| Orchestration | Apache Airflow (Docker + WSL2) |
| Dashboard | Streamlit |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Vector store | ChromaDB |
| LLM | Groq (Llama 3.3 70B, free tier) |

## Status & Next Steps

All five planned phases (Foundations → Manual Pipeline → Validation → Orchestration →
Dashboard/RAG) are complete and verified end-to-end. Potential future extensions include
scheduled/automated DAG runs, additional source types (Excel silver-layer cleaning,
government APIs), and swapping the current rule-based PDF field extraction for the
LLM-based structured extraction validated as necessary in Phase 1.

*For the full technical build log — every decision, command, bug, and fix — see the
companion document: **Technical Deep Dive**.*
