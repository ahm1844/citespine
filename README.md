# CiteSpine

*A compliance‑grade, metadata‑driven RAG assistant for financial reporting and audit.*

---

## What this project is

CiteSpine is a local, Dockerized Proof‑of‑Concept (PoC) that demonstrates an end‑to‑end Retrieval‑Augmented Generation (RAG) system built for **finance/audit** questions where **traceability and citations** are mandatory. It ingests a small corpus of financial PDFs (standards, filings, policies), enforces a strict metadata schema, chunks and embeds the text, indexes it in a vector store, retrieves with **metadata filters**, and composes **answers strictly from retrieved evidence** with paragraph‑level citations. It can also produce **structured artifacts** (e.g., accounting memo, journal entry, disclosure) that are **filled only when a supporting citation exists**.

This PoC runs **fully on your laptop** via Docker Compose, minimizes (or eliminates) paid services, and includes **reproducible evaluation** (recall\@k and faithfulness) plus **run manifests** for auditability.

> Pinecone vs. pgvector
> **What is Pinecone?** Pinecone is a managed vector database that stores embeddings and supports fast similarity search with metadata filters and namespaces. It's highly available, horizontally scalable, and production‑ready.
> **What we use here:** For the local PoC we use **Postgres + pgvector** to keep costs near zero while mirroring Pinecone semantics behind a thin adapter.
> **Required phrasing:** "**in our project with the client, we are gonna use Pinecone... for our project, we will use pgvector.**"

---

## Why this project exists

Financial reporting and audit teams need **fast, accurate, and well‑sourced answers**. Traditional search either returns too much or lacks the provenance auditors require. CiteSpine:

* **Grounds answers in specific paragraphs**, with inline citations and links.
* **Enforces metadata** (framework, jurisdiction, doc\_type, authority\_level, effective\_date, version) so users can filter precisely (e.g., "IFRS as of 2023, disclosures, authoritative").
* **Prevents hallucinations** via a hard "no citation → no claim" rule.
* **Measures quality** (recall\@k and faithfulness) from day one.
* **Keeps everything reproducible** with run manifests and pinned environments.

---

## What it does (capabilities)

* **Ingest PDFs** (parse text, preserve headings/section paths, extract tables; OCR fallback for scans).
* **Validate + normalize metadata** against `config/metadata.yml`; reject out‑of‑spec and produce `exceptions.csv`.
* **Chunk + embed** content, store in **pgvector** with stable IDs and full metadata.
* **Retrieve** with **pre‑filters** (framework/jurisdiction/doc\_type/authority\_level/as‑of date).
* **Answer** from evidence only; output inline **citations** with page spans.
* **Generate structured outputs** (memo, journal, disclosure) as **JSON** with a **source map**; leave fields blank if ungrounded.
* **Evaluate** on a seed question set with **recall\@k** and **faithfulness**; publish `/eval/report`.
* **Operate locally** via Docker Compose; optional **Ollama** for offline LLM.

---

## How it works (at a glance)

1. **Ingest** → Parse PDFs, OCR if needed, extract headings/tables, detect candidate metadata.
2. **Validate** → Normalize to controlled vocabularies; accept or write an exception record.
3. **Chunk & Embed** → Section‑aware chunks with overlap; generate embeddings (local or API).
4. **Index** → Upsert into pgvector with **stable IDs** + metadata; write an index manifest.
5. **Retrieve** → Apply metadata filters first, then vector similarity; optional in‑process rerank.
6. **Compose Answer** → Build answer from retrieved spans only; insert **paragraph‑level citations**.
7. **Structured Outputs** → Fill JSON schemas from the same evidence; leave ungrounded fields blank+flag.
8. **Evaluate & Observe** → Run seed set, compute metrics, store run manifests and an evaluation report.

---

## Project status and scope (PoC)

* **Local PoC**: small corpus (50–100 documents), pgvector, minimal API/UI, reproducible metrics.
* **Production parity**: a **Pinecone adapter** is included to make migration trivial.
* **License‑safe**: ingest public/owned documents; avoid restricted texts unless licensed (e.g., IFRS codification).

---

## Repository layout

```
citespine/
  README.md
  TECHNICAL_SPEC.md
  .env.example
  docker-compose.yml
  Dockerfile
  Makefile
  requirements.txt

  config/
    metadata.yml             # controlled vocabularies + synonym rules
    prompts/                 # system & composer templates

  data/
    raw/                     # drop PDFs here
    processed/               # normalized chunks + metadata (JSONL)
    eval/                    # seed questions, gold spans, and run reports

  src/
    ingest/
      parse_pdf.py
      ocr.py
      extract_tables.py
      normalize_metadata.py
      chunker.py
    index/
      schemas.py
      build_index.py
      pinecone_adapter.py    # same call-shapes as Pinecone; backed by pgvector
    retrieve/
      query.py
      filters.py
      rerank.py              # in-process cross-encoder (optional)
    answer/
      compose.py
      citations.py
    artifacts/
      memo.py
      journal_entry.py
      disclosure.py
      schemas/
        memo.schema.json
        journal_entry.schema.json
        disclosure.schema.json
    eval/
      seed_questions.jsonl
      evaluate.py
      metrics.py
    api/
      app.py                 # FastAPI
      routes/
        ingest.py
        query.py
        generate.py
        eval.py
    ui/
      app.py                 # optional Streamlit demo

  tests/
    unit/
    integration/
```

---

## Requirements

* **System**: Docker + Docker Compose, Python 3.11, Tesseract OCR, poppler-utils, libmagic, ghostscript.
* **Python** (pinned in `requirements.txt`):

  * fastapi, uvicorn\[standard], pydantic, python-dotenv, pyyaml, httpx, loguru
  * psycopg\[binary], SQLAlchemy, alembic, pgvector, asyncpg
  * pymupdf, pdfplumber, pypdf, unstructured\[pdf], pytesseract
  * sentence-transformers, torch (CPU), numpy, scikit-learn
  * openai *(optional)*, ollama *(optional)*, anthropic *(optional)*, litellm
  * ragas, datasets, rapidfuzz, rank-bm25 *(optional)*
  * pytest, pytest-asyncio, coverage, ruff, black, mypy, pre-commit
  * opentelemetry-api, opentelemetry-sdk *(local traces only)*

---

## Quick start

1. **Clone & bootstrap**

```bash
git clone https://github.com/your-org/citespine.git
cd citespine
cp .env.example .env
```

2. **Configure environment** (`.env`)

```bash
# LLM/embeddings: choose local or API
LLM_PROVIDER=ollama         # or openai
EMBEDDINGS_PROVIDER=local   # or openai

# Postgres + pgvector
PG_HOST=postgres
PG_PORT=5432
PG_DB=citespine
PG_USER=postgres
PG_PASSWORD=postgres
PG_DSN=postgresql+psycopg://postgres:postgres@postgres:5432/citespine

# Optional
OPENAI_API_KEY=
AS_OF_DEFAULT=2023-12-31
```

3. **Start the stack**

```bash
docker compose up -d
make install          # pip install -r requirements.txt inside api container (or local)
```

4. **Add documents**
   Place PDFs into `data/raw/`.

5. **Ingest & index**

```bash
make ingest           # parse → validate → chunk → embed (writes exceptions.csv if any)
make index            # upsert into pgvector; writes index manifest
```

6. **Run API / UI**

```bash
make api              # FastAPI @ http://localhost:8000
make ui               # Streamlit demo @ http://localhost:8501 (optional)
```

7. **Evaluate**

```bash
make eval             # runs seed set; writes data/eval/<timestamp>/*
```

---

## Using the API

* `POST /ingest` → ingest/validate PDFs found in `data/raw/`
* `GET  /ingest/exceptions` → list unresolved validation exceptions
* `POST /query` → body: `{ "q": "How does IFRS vs US GAAP treat...?", "filters": { "framework": "IFRS", "jurisdiction": "Global", "as_of": "2023-12-31" } }`
* `POST /generate/memo|journal|disclosure` → returns JSON artifact with only **cited** fields
* `GET  /eval/report` → latest recall\@k + faithfulness + run manifest id

---

## Evaluation & acceptance (PoC)

* **Metadata validation**: ≥ 95% docs pass; failures appear in `exceptions.csv`.
* **Retrieval quality**: **recall\@10 ≥ 0.80** on the seed set (50± questions).
* **Faithfulness**: **No unsupported claims**; every claim has a citation.
* **Operational**: `docker compose up` healthy; volumes persist; secrets in `.env`.
* **Reproducibility**: Re‑running from a stored manifest reproduces same sources and a materially identical answer.

---

## Data & licensing

* Use only **public** or **owned** documents for the PoC (e.g., SEC filings, regulator guidance).
* **Do not** ingest restricted IFRS/US GAAP codification content unless you have licensed access.

---

## Security & governance (local)

* **Least privilege**: local network only; separate DB creds.
* **PII minimization**: redact obvious PII at ingest before storage.
* **Traceability**: every answer & eval writes a **run manifest** (models, params, corpus hash, cited chunk IDs).
* **Egress control**: offline by default; only the chosen LLM provider if enabled.

---

## Roadmap (after PoC)

* Swap pgvector adapter → **Pinecone** in client environment.
* Add **hybrid retrieval** (BM25 signals) if metrics justify.
* Expand structured schemas and add reviewer UI for SMEs.
* Hardening: concurrency, back‑pressure, and larger corpora.

---

## Contributing

* Small PRs only.
* One lever per change (chunking **or** embeddings **or** prompts **or** rerank).
* Every PR must:

  1. state a hypothesis,
  2. run the seed eval,
  3. attach metrics + manifest,
  4. update docs/runbooks if behavior changes.

---

## License

TBD by your organization's policy.

---
