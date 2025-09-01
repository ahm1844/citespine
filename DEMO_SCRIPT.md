# CiteSpine Demo Script Walkthrough

## Overview
CiteSpine is now end-to-end operational with **pgvector baseline**, **Pinecone router**, **parity harness**, **demo UI**, and **client-ready upsert loader**.

## Demo Endpoints

### 1. Demo UI (`/demo`)
- **URL**: http://localhost:8000/demo
- **Purpose**: Interactive web interface for live queries
- **Features**:
  - Real-time query interface
  - Backend selection (pgvector/pinecone)
  - Latency monitoring
  - Citation display

### 2. Query API (`/query`)
- **Purpose**: Retrieve relevant chunks with citations
- **Method**: POST
- **Sample PCAOB Query**:
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "q": "What does PCAOB require for ICFR audits?",
    "filters": {
      "framework": "Other",
      "jurisdiction": "US", 
      "doc_type": "standard",
      "authority_level": "authoritative",
      "as_of": "2024-12-31"
    },
    "top_k": 5,
    "probes": 15
  }'
```

- **Sample ESEF Query**:
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "q": "What are ESEF XBRL reporting requirements?",
    "filters": {
      "framework": "Other",
      "jurisdiction": "EU",
      "doc_type": "standard", 
      "authority_level": "authoritative",
      "as_of": "2024-12-31"
    },
    "top_k": 5,
    "probes": 15
  }'
```

### 3. Memo Generation (`/generate/memo`)
- **Purpose**: Generate grounded memos with source mapping
- **Method**: POST
- **Features**:
  - Structured memo format
  - Source citations (_source_map)
  - Blank flagging for unsupported claims

- **Sample Request**:
```bash
curl -X POST http://localhost:8000/generate/memo \
  -H "Content-Type: application/json" \
  -d '{
    "q": "What are the key PCAOB requirements for substantive analytical procedures?",
    "filters": {
      "framework": "Other",
      "jurisdiction": "US",
      "doc_type": "standard",
      "authority_level": "authoritative", 
      "as_of": "2024-12-31"
    }
  }'
```

### 4. Evaluation Report (`/eval/report`)
- **URL**: http://localhost:8000/eval/report
- **Purpose**: Show recall@10 metrics on seed set
- **Current Status**: Shows evaluation results with expanded 12-question seed set

## Demo Script Flow

### Part 1: Multi-Jurisdiction Queries (5 minutes)
1. **US PCAOB Questions**:
   - "What does PCAOB require for substantive analytical procedures?"
   - "How does PCAOB address technology-assisted analysis in audits?"
   - "What are PCAOB requirements for material misstatement evaluation?"

2. **EU ESEF Questions**:
   - "What are ESEF requirements for inline XBRL documents?"
   - "How does ESMA require extension taxonomy elements?"
   - "What are ESEF block tagging requirements?"

3. **Note Backend & Latency**: 
   - Point out backend indicator (pgvector/pinecone)
   - Show latency measurements
   - Highlight citation chunk IDs

### Part 2: Grounded Memo Generation (3 minutes)
1. Generate memo for PCAOB substantive analytical procedures
2. Show structured output with:
   - Title and issue sections
   - Source mapping (_source_map)
   - Citation anchoring
   - Blank fields for unsupported claims

### Part 3: Evaluation & Parity (2 minutes)
1. **Evaluation Report**: 
   - Show recall@10 results on 12-question seed set
   - Current pgvector baseline performance

2. **Manifests**:
   - Open `data/manifests/eval_*.json` to show reproducibility
   - Query manifests showing parameters used

## Technical Architecture Highlights

### Current Configuration
- **Backend**: pgvector (default)
- **Embedding Model**: sentence-transformers/all-MiniLM-L6-v2 (local)
- **Top-K**: 10
- **Probes**: 20 (adjusted for better recall)
- **Chunk Size**: 900 tokens
- **Overlap**: 150 tokens

### Document Coverage
- **PCAOB Standards** (US): Auditing standards, substantive analytical procedures, fraud detection
- **ESMA ESEF Manual** (EU): XBRL reporting, inline taxonomies, extension requirements
- **SEC Forms**: 10-K filings and regulatory guidance

### Evaluation Metrics
- **Seed Set**: 12 questions (6 PCAOB + 6 ESEF)
- **Current Recall@10**: 0.25 (needs optimization)
- **Target**: ≥ 0.80 recall@10

## Next Steps for Client Demo

### Prerequisites
1. **Pinecone Setup** (for client parity):
   - Set PINECONE_API_KEY in .env
   - Set PINECONE_INDEX_NAME=citespine
   - Run: `make pc_upsert NS=default B=200 M=-1 CREATE=false`

2. **Backend Switch**:
   - Change .env: `VECTOR_BACKEND=pinecone`
   - Restart: `docker compose up -d --force-recreate api`
   - Run: `make parity K=10 P=15`

### Demo Sequence
1. **Live Query Demo** (5 min): Multiple PCAOB/ESEF queries via /demo
2. **Memo Generation** (3 min): Show grounded memo with source mapping
3. **Evaluation Results** (2 min): Show recall@10 and parity coverage
4. **Architecture Overview** (2 min): Highlight client-ready features

### Key Selling Points
- ✅ **Multi-jurisdiction**: US (PCAOB) + EU (ESEF) standards
- ✅ **Grounded Output**: Every claim linked to source chunks
- ✅ **Client-Ready**: Pinecone hydration + parity testing
- ✅ **Reproducible**: Full manifest tracking
- ✅ **Scalable**: Technology-assisted analysis ready

## Files Generated
- **Manifests**: `data/manifests/eval_*.json`, `query_*.json`
- **Evaluation**: `data/eval/*/metrics.json`, `predictions.json`
- **Parity**: `data/eval/parity_*/report.json` (after Pinecone setup)
