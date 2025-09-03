# CiteSpine

<p align="center">
  <img src="citespine-logo.png" alt="CiteSpine Logo" width="200"/>
</p>

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
.
├─ docker-compose.yml
├─ README.md
├─ public/                      # static landing page served at /site
│  └─ index.html
├─ frontend/                    # React app (served at /app after build)
│  ├─ package.json
│  ├─ vite.config.js
│  ├─ index.html
│  ├─ src/
│  │  ├─ main.tsx
│  │  ├─ App.tsx
│  │  └─ components/
│  │     ├─ Dropzone.tsx
│  │     ├─ QueryForm.tsx
│  │     └─ Citations.tsx
│  └─ styles.css
├─ src/
│  ├─ api/
│  │  ├─ app.py                 # FastAPI app, routes, static mounts
│  │  └─ auth.py                # invite cookie + API key guards
│  ├─ common/
│  │  └─ config.py              # env settings (INVITE_TOKEN, COOKIE_DOMAIN, etc.)
│  ├─ db/
│  │  ├─ models.py              # Document, Chunk, APIKey...
│  │  └─ session.py             # engine/session
│  ├─ ingest/
│  │  ├─ runner.py              # ingest_single_pdf + batch pipeline
│  │  └─ ...                    # parse_pdf, chunker, metadata…
│  ├─ retrieval/
│  │  └─ router.py              # retrieve_any (pgvector by default)
│  ├─ answer/
│  │  └─ compose.py             # "no citation → no claim"
│  ├─ tools/
│  │  └─ apikeys.py             # CLI: create/list/revoke API keys
│  └─ eval/                     # seed, eval harness, parity tools
│     └─ ...
└─ data/
   ├─ uploads/                  # uploaded PDFs (gitignored)
   ├─ manifests/                # run manifests (gitignored)
   ├─ processed/                # chunks/embeddings (gitignored)
   ├─ eval/                     # eval reports (gitignored)
   └─ leads.csv                 # lead capture (gitignored)
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

## Demo Walkthrough

> Backend policy: **in our project with the client, we are gonna use Pinecone... for our project, we will use pgvector.**  
> Flip via `.env` or per-command env vars (see below).

### Prerequisites
- Docker Desktop (WSL2 on Windows)
- `docker compose up -d` starts `postgres` + `api`
- A small corpus ingested & indexed (PCAOB/ESMA PDFs)
- Seed set at `src/eval/seed_questions.jsonl` (10–15 questions)

### 1) Run the demo UI
Open: **http://localhost:8000/demo**  
What to watch:
- `backend` indicator (`pgvector` / `pinecone`)
- `latency_ms`
- `citations[]` with `chunk_id` and `page_span`
- Every answer has a **run manifest** (see `data/manifests/query_*.json`)

### 2) Query examples (copy/paste)
```bash
curl -s -X POST http://localhost:8000/query -H "Content-Type: application/json" \
  -d '{"q":"What does PCAOB require for ICFR audits?","filters":{"framework":"Other","jurisdiction":"US","doc_type":"standard","authority_level":"authoritative","as_of":"2024-12-31"},"top_k":10,"probes":15}' | jq .
```

```bash
curl -s -X POST http://localhost:8000/query -H "Content-Type: application/json" \
  -d '{"q":"What are ESEF primary statement tagging requirements?","filters":{"framework":"Other","jurisdiction":"EU","doc_type":"standard","authority_level":"authoritative","as_of":"2024-12-31"},"top_k":10,"probes":15}' | jq .
```

### 3) Grounded memo generation

```bash
curl -s -X POST http://localhost:8000/generate/memo -H "Content-Type: application/json" \
  -d '{"q":"Key PCAOB requirements for substantive analytical procedures","filters":{"framework":"Other","jurisdiction":"US","doc_type":"standard","authority_level":"authoritative","as_of":"2024-12-31"}}' | jq .
```

* Fields populate **only** when supported by cited text.
* Missing evidence ⇒ field blank + flag (no hallucinations).

### 4) Evaluation

```bash
make eval
# Output includes recall@10 on the seed set and a manifest path.
```

Acceptance target: **recall@10 ≥ 0.80**, faithfulness = 100%.

### 5) Pinecone (client parity)

**Hydrate** (from processed JSONL):

```bash
docker compose run --rm \
  -e PINECONE_API_KEY="***" -e PINECONE_INDEX_NAME="citespine" -e PINECONE_NAMESPACE="default" \
  api python -m src.tools.pinecone_upsert --processed-dir data/processed --namespace default --batch-size 200 --max-chunks -1 --create-index false
```

**Parity check** (one-shot):

```bash
docker compose run --rm \
  -e VECTOR_BACKEND="pinecone" \
  -e PINECONE_API_KEY="***" -e PINECONE_INDEX_NAME="citespine" -e PINECONE_NAMESPACE="default" \
  api python -m src.eval.parity --top-k 10 --probes 15
```

Open: `data/eval/parity_*/report.json`

### 6) Reproducibility

Every `/query` and `/generate` writes a **manifest** with:

* model, parameters, corpus hash, cited chunk IDs, latency, backend.
  Re-run from a manifest to reproduce the same sources and materially identical answers.

### 7) No evidence → no claim

Try a question outside the corpus to see a guarded "no evidence found" response. This enforces compliance-grade answers.

---

## Pinecone credentials (secure handling)

- **Do not** commit keys or `.env`.
- Prefer **ephemeral env** (as shown).  
- For interactive API runs, you can keep a private `my.env` **outside the repo** and do:
  ```bash
  docker compose --env-file ../my.env up -d --force-recreate api
  ```

* Confirm index: `dimension=384`, `metric=cosine`, `namespace=default`.

---

## Release Notes

### v0.1.0-poc (pgvector baseline)

* Quality: recall@10 = **0.92** (11/12 seeds), faithfulness enforced by "no citation → no claim".
* Config: dense-only (pgvector), `probes=15`, `CHUNK_SIZE=900`, `OVERLAP=150`.
* Corpus: PCAOB + ESMA PDFs (public).
* Reproducibility: manifests written for queries and eval runs.
* Note: *in our project with the client, we are gonna use Pinecone... for our project, we will use pgvector.* Pinecone parity tools are ready and can be run when credentials are provided.

**Evaluation Metrics:**
```
Seeds: 12 | Recall@10: 0.92 | Probes: 15 | Backend: pgvector | Chunk: 900/150
```

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

### Gated Demo & API

- **Set invite cookie:** `http://HOST/auth/invite?token=LETMEIN`
- **Public page:** `http://HOST/site`
- **App (after build):** `http://HOST/app`
- **Upload:** `POST /upload` (invite required)
- **UI query:** `POST /query` (invite required)
- **Programmatic query:** `POST /v1/query` with `X-Api-Key: <key>` (generate with `python -m src.tools.apikeys --name <label>`)

We enforce **no citation → no claim**. If we can't find evidence, we say "No evidence found."

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
