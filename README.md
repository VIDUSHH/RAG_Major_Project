# RAG-Based Postmortem Intelligence System

An intelligent backend platform that ingests application/system logs and historical postmortem reports, processes and indexes them, retrieves relevant historical incidents, understands relationships between services/errors/root causes/fixes, and generates grounded explanations and remediation recommendations.

## Architecture

The system enforces a strict dual-plane architecture:

1. **Django (Control Plane)**: Manages users, auth, RBAC, multi-tenancy, projects, services, incident/postmortem metadata, API keys, and audit logging with PostgreSQL.
2. **FastAPI (AI / Data Plane)**: Handles ingestion APIs, log/postmortem parsing, semantic/hierarchical chunking, embeddings, Qdrant vector storage, Neo4j GraphRAG, hybrid retrieval (BM25 + Dense + RRF + Cross-Encoder), and Gemini LLM orchestration.

```
                    CLIENT / FUTURE FRONTEND
                             |
                             v
                    +----------------+
                    |    DJANGO      |
                    |  CONTROL PLANE |
                    +----------------+
                       |     |     |
                       v     v     v
                   PostgreSQL  Auth
                       |
                       | internal API (X-Internal-API-Key)
                       v
                    +----------------+
                    |    FASTAPI     |
                    |   AI / DATA    |
                    |     PLANE      |
                    +----------------+
                       |
             +---------+---------+
             |         |         |
             v         v         v
          Qdrant     Neo4j     LLM (Gemini)
```

## RAG Pipeline

The FastAPI data plane runs a modular RAG pipeline (`app/rag/pipeline.py`):

1. **Query Understanding** — keyword/entity-based intent detection (root cause analysis, historical incident search, dependency investigation, etc.).
2. **Hybrid Retrieval** — BM25 sparse + dense vector search with reciprocal-rank fusion and cross-encoder reranking against Qdrant.
3. **Graph Retrieval** — GraphRAG queries against Neo4j for service/error/root-cause relationships and similar incidents.
4. **Context Assembly** — merges vector + graph evidence with citation metadata.
5. **Generation** — Gemini (or a mock provider in dev) produces a grounded incident analysis with sources.

Ingestion flow: upload → parser (`app/ingestion/parsers`) → semantic/hierarchical chunking (`app/processing/chunking`) → embeddings (`app/embeddings`) → Qdrant points + Neo4j nodes/relationships (`app/services`).

## Repository Layout

```
├── django_backend/       # Django control plane (users, auth, RBAC, tenancy, API keys)
├── fastapi_backend/      # FastAPI AI/data plane
│   ├── app/
│   │   ├── api/v1/       # ingestion, query, database endpoints
│   │   ├── core/         # config (pydantic-settings), logging, security
│   │   ├── embeddings/   # embedding provider abstraction
│   │   ├── ingestion/    # log/postmortem parsers
│   │   ├── processing/   # chunking strategies
│   │   ├── rag/          # pipeline orchestrator + shared models
│   │   ├── retrieval/    # hybrid (BM25+dense+RRF) and graph retrieval
│   │   ├── llm/          # LLM provider abstraction (Gemini/mock)
│   │   └── services/     # Qdrant + Neo4j service layers
│   ├── requirements.txt
│   └── app/main.py       # FastAPI app entry point
├── infrastructure/       # Docker Compose (Postgres, Qdrant, Neo4j) + Dockerfiles
├── scripts/              # ingestion / dataset helpers
├── tests/                # pytest suites (fastapi_backend, django_backend)
├── .env.example          # template for environment configuration
└── Makefile
```

## Prerequisites

- Python 3.11+
- Docker (recommended — the FastAPI app, Qdrant and Neo4j all run in containers; without Docker the app runs in a degraded mode using Qdrant Cloud + Gemini, but Neo4j graph features are unavailable).
- A Google AI Studio API key for `GEMINI_API_KEY` (optional — the mock provider is used otherwise).

## Setup

### 1. Configure environment

```bash
cp .env.example .env
# then edit .env with real values (secrets). Never commit .env.
```

`.env` is read from the project root by the FastAPI `Settings` (pydantic-settings) and the Django control plane. All modules must read configuration via the `settings` object — do not use `os.getenv()` directly, or `.env` values will be silently ignored.

Verified working model settings (as of the current Gemini API):
- **Embeddings are local by default** — `EMBEDDING_PROVIDER=sentence-transformers` with `EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2` (384-dim). The model runs fully offline in-process (via PyTorch), so embedding is free and has **no API quota**. The first embed call downloads the model once (~90MB) from HuggingFace, then runs locally.
- To use the Gemini embedding API instead: `EMBEDDING_PROVIDER=gemini` and `EMBEDDING_MODEL=gemini-embedding-2` — calls use `output_dimensionality=768` so vectors match the collection dimension, and `embed_documents` batches texts (note: `gemini-embedding-2` free-tier quota is only ~100 req/min and 1000/day).
- `LLM_PROVIDER=gemini` and `LLM_MODEL=gemini-flash-latest`.
- Switching embedding models changes the vector dimension; the Qdrant collection is recreated automatically at the new dimension on the next ingest (existing points are dropped and a warning is logged).
- Avoid `text-embedding-004` (returns 404 — deprecated), `gemini-1.5-flash` (404) and `gemini-2.5-flash` (not available to new users). If a Gemini quota error (`429 ... retry in Ns`) is returned, the provider honors the server's suggested wait (capped at 60s) before retrying. `EMBEDDING_PROVIDER` / `LLM_PROVIDER` are documented in `.env.example`.

### 2. Create the virtualenv

```bash
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r django_backend/requirements.txt
pip install -r fastapi_backend/requirements.txt
```

### 3. Run the whole app in Docker (recommended)

```bash
# From the project root — compose reads ../.env (relative to the compose file) for secrets
docker compose -f infrastructure/docker-compose.yml up -d --build
```

This starts Qdrant, Neo4j, and the FastAPI data plane. Open `http://localhost:8001/`.

Notes on the Docker setup:

- **Qdrant** runs locally (`qdrant/qdrant:v1.19.0`, matching `qdrant-client==1.19.0`) even if your `.env` points `QDRANT_URL` at Qdrant Cloud — the compose file forces `QDRANT_URL=` empty for the container.
- **Collections are auto-created**: the first file you upload creates the `postmortems_v1` collection (and payload indexes) on the fly — no manual Qdrant setup.
- The FastAPI image is **lean** (`infrastructure/docker/requirements.fastapi.txt`): it ships **CPU-only PyTorch + `sentence-transformers`** so local (quota-free) embeddings run in the container, but the large cross-encoder rerank model is excluded — `RERANKING_ENABLED=False` and RRF fusion is used instead.
- Uploads and `/data` persist in the `rag_data` volume.
- The Neo4j default password is `postmortem_neo4j_pass` (or whatever `NEO4J_PASSWORD` resolves to in the compose file).

Django + Postgres are on a profile and are **not** started by default. Start them only if you need the control plane:

```bash
docker compose -f infrastructure/docker-compose.yml --profile control-plane up -d
```

### 4. Run Django control plane

```bash
cd django_backend
python manage.py migrate

# Create an admin superuser (interactive — you will be prompted for credentials)
python manage.py createsuperuser

python manage.py runserver 8000
```

### 5. Run FastAPI data plane locally (alternative to Docker)

```bash
# Run from the workspace root — no need to cd
uvicorn --app-dir fastapi_backend app.main:app --host 0.0.0.0 --port 8001 --reload
```

### 6. Open the Web UI

The FastAPI app serves a single-page UI at `http://localhost:8001/` with a sidebar of tabs:

- **Dashboard** — clickable stat cards (documents, chunks, vector store, graph nodes, relationships, incidents) that open detail modals; a per-document table showing which chunking strategy indexed each file; and a live **recent activity** feed (ingest/analyze events).
- **Ingest Files** — select a chunking strategy from cards that explain each approach (hierarchical for logs, semantic for postmortems, fixed-size for generic text), then drag-and-drop files. A full-screen animated overlay shows parse → chunk → embed → store → graph progress.
- **Analyze Incident** — ask a natural-language question; get a Gemini analysis with cited evidence, dependency visualization, and a 60s progress overlay with elapsed timer.
- **Vector DB** — a ChatGPT-style chat panel: type a semantic query, browse clickable result bubbles, and open any chunk's full content + metadata in a detail modal.
- **Graph DB** — enter a service name to visualize its **Service Dependency Graph** (DEPENDS_ON / PRODUCED_LOG edges, clickable nodes), plus filterable node and relationship tables with detail modals.
- **System Status** — per-component health for Qdrant, Neo4j, the local embedding model, and the LLM, with live stats.

Interactive API docs: `http://localhost:8001/docs`. Health check: `http://localhost:8001/health`.

### 7. Run tests

```bash
pytest
```

Runs the FastAPI contract tests and the full Django control-plane suite (127 tests).

## Key Configuration

| Variable | Purpose |
| --- | --- |
| `FASTAPI_INTERNAL_API_KEY` | Header key used for Django → FastAPI service-to-service auth |
| `QDRANT_URL` / `QDRANT_API_KEY` | Qdrant cloud endpoint (local host/port used when unset) |
| `NEO4J_HOST` / `NEO4J_PASSWORD` | Neo4j connection |
| `GEMINI_API_KEY` | Gemini key for the LLM (`gemini-flash-latest`) and optional Gemini embeddings |
| `EMBEDDING_PROVIDER` / `EMBEDDING_MODEL` / `EMBEDDING_DIMENSION` | Embedding provider selection (default: local `sentence-transformers` / `all-MiniLM-L6-v2`, 384-dim) |
| `LLM_PROVIDER` / `LLM_MODEL` / `LLM_TEMPERATURE` | LLM provider selection (`gemini` or `mock`) |
| `RERANKING_ENABLED` | Cross-encoder reranking on top of RRF fusion (default `False` to keep retrieval fast) |
| `POSTGRES_*` | Django database connection |
| `MAX_CHUNKS_PER_FILE` | Ingestion guardrail: caps chunks produced per file (default `5000`) |

## Robustness & Known Behaviors

- **Long requests never block the event loop.** Ingestion (`/ingest`, `/ingest/batch`) and all `/query` and `/database` handlers are plain `def` endpoints, so FastAPI runs them in a worker thread. Health checks and other requests keep responding even while a large ingest or an LLM call is in flight.
- **Embeddings are local and quota-free by default.** The default `sentence-transformers` provider runs `all-MiniLM-L6-v2` fully offline (CPU PyTorch in the container), so ingest is free and unlimited. The Gemini embedding API remains available via `EMBEDDING_PROVIDER=gemini`.
- **Embedding retry sleeps are capped** (60s max) and each batch logs progress, so a rate-limited provider degrades gracefully instead of stalling.
- **Free-tier quotas (Gemini LLM / optional Gemini embeddings).** The Gemini free tier is ~100 requests/min and **1000/day per model** for `gemini-embedding-2`. When the daily budget is exhausted, ingest/query return a clear `429` error rather than hanging. A single huge file can burn the whole daily budget — `MAX_CHUNKS_PER_FILE` prevents that by capping chunks per ingest (see the `truncated: true` field in the ingest response).
- **Neo4j schema is auto-initialized.** Constraints and indexes for the graph schema are created on first graph use (idempotent `IF NOT EXISTS`). If Neo4j is unreachable, graph features degrade gracefully to vector-only.
- **Hybrid retrieval actually uses both channels.** The BM25 sparse index is built lazily from the Qdrant collection on first query and refreshed as new points arrive, so RRF fuses dense + sparse results (the cross-encoder reranker is off by default — `RERANKING_ENABLED=False` — to keep retrieval fast on free-tier hardware).
- **Incident analyses are server-grounded.** The LLM writes the narrative (title, root cause, recommendations) but `incident_id`, `evidence`, `sources` and `graph_relationships` are always rebuilt from the actual retrieved chunks, so the API can never cite fabricated sources. Enum fields are normalized and a malformed/unavailable LLM degrades to a grounded fallback instead of a 500.
- **Postmortem ingestion is wired end-to-end.** Besides file uploads (`/ingest`, `/ingest/batch`), the data plane accepts direct text via `/ingest/text`; the Django control plane's "Trigger Ingestion" button on a postmortem calls it through `FastAPIClient.trigger_postmortem_ingestion` and reflects `completed`/`failed` status back on the record.
- **Chunking strategy is stored per chunk.** Every chunk payload carries `chunking_strategy` (hierarchical/semantic/fixed), so `/database/vectors/summary` can report which documents were indexed with which strategy — surfaced on the dashboard.
- **Service dependencies are extracted from log text.** During ingestion, if a chunk mentions another known service name, a `DEPENDS_ON` edge is created between those service nodes — powering the Service Dependency Graph. (Neo4j stays best-effort; vector storage is the source of truth.)
- **Recent activity is logged without a new database.** Ingestion and analysis events are appended to a bounded JSON activity log (`data/activity.json`, newest first, max 200 records) exposed via `/database/activity/recent` and shown on the dashboard.
- **Interactive requests never hang silently.** Gemini calls carry explicit timeouts (60s LLM, 30s/60s embeddings) and retries respect a hard deadline, so a rate-limited provider fails fast with a clear error instead of spinning. The SPA's Analyze screen shows animated progress + an elapsed timer and aborts after 60s with a friendly timeout message.
- **The SPA is served cache-safe.** Static asset URLs carry a content-based version (`app.js?v=…`, `styles.css?v=…`, computed from file mtimes in `main.py`) and the shell is sent with `Cache-Control: no-store`, so a redeploy can never serve stale JS/CSS that makes the UI look frozen. A global `[hidden] { display: none !important; }` rule makes the full-screen loading/ingest/modal overlays (which set `display: flex`) respect the `hidden` attribute instead of covering the page on load. The internal API key is injected into the page by `main.py` using a marker that is replaced everywhere it appears — so the JS variable name must not contain it (the SPA uses `INTERNAL_API_KEY`, not `__INTERNAL_API_KEY__`).

## API Surface (FastAPI data plane, under `/api/v1`)

- **Ingestion**: `POST /ingest`, `POST /ingest/batch`, `GET /ingest/parsers`
- **Query**: `POST /query/analyze`, `POST /query/search`, `GET /query/intents`, `GET /query/examples`
- **Database inspection**: vectors (`/database/vectors/*`, including `/database/vectors/summary` which groups chunks by source document + chunking strategy), graph (`/database/graph/*`), and `/database/activity/recent` (recent-activity feed)
- **Health**: `/health`, `/api/v1/status`

All endpoints are tenant-scoped via the `X-Organization-ID` header; service calls also send `X-Internal-API-Key`. The SPA injects the internal API key server-side at page load, so no key is hardcoded in the browser.

## Qdrant / qdrant-client Notes

- `qdrant-client` is pinned to `1.19.0` to match the Qdrant cloud server API. Code must use the 1.14+ client API: `query_points`/`query_batch_points` (not the removed `search`/`search_batch`), `scroll_filter=` (not `filter_=`), and `points_count` (the old `vectors_count` attribute was removed from `CollectionInfo`).
- Tenant-filtered fields (`organization_id`, `project_id`, `service`, `level`, `source`, `timestamp`) get **payload indexes** automatically via `QdrantService.ensure_payload_indexes()`; without these, filtered searches fail with `Index required but not found`.
- Neo4j is **best-effort**: if it is unreachable, ingestion and analysis log a warning and continue with vector-only results.

## Interview Prep

See [`questions.md`](questions.md) for a curated set of interview questions covering this project's walkthrough, RAG evaluation, pipeline failure points, and production deployment.
