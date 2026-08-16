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
- `EMBEDDING_PROVIDER=gemini` and `EMBEDDING_MODEL=gemini-embedding-2` — providers are called with `output_dimensionality=768` so vectors match the Qdrant collection dimension, and `embed_documents` batches texts so one API call covers up to `batch_size` chunks (important: `gemini-embedding-2` free-tier quota is only ~100 req/min and 1000/day).
- `LLM_PROVIDER=gemini` and `LLM_MODEL=gemini-flash-latest`.
- Avoid `text-embedding-004` (returns 404 — deprecated), `gemini-1.5-flash` (404) and `gemini-2.5-flash` (not available to new users). If a quota error (`429 ... retry in Ns`) is returned, the provider honors the server's suggested wait (capped at 60s) before retrying. `EMBEDDING_PROVIDER` / `LLM_PROVIDER` are documented in `.env.example`.

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
- The FastAPI image is **lean** (`infrastructure/docker/requirements.fastapi.txt`) — `torch`/`sentence-transformers` are excluded, so cross-encoder reranking is automatically disabled and RRF fusion is used instead.
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

The FastAPI app serves a single-page UI at `http://localhost:8001/` with tabs for:

- **Dashboard** — vector/graph store overview
- **Ingest Files** — upload one or more log/postmortem files (parsers auto-detected, chunking strategy selectable)
- **Analyze Incident** — ask a natural-language question; get a Gemini analysis with cited evidence
- **Vector DB / Graph DB** — inspect stored vectors and graph nodes
- **System Status** — Qdrant/Neo4j health

Interactive API docs: `http://localhost:8001/docs`. Health check: `http://localhost:8001/health`.

### 7. Run tests

```bash
pytest
```

Runs the FastAPI contract tests and the full Django control-plane suite (120 tests).

## Key Configuration

| Variable | Purpose |
| --- | --- |
| `FASTAPI_INTERNAL_API_KEY` | Header key used for Django → FastAPI service-to-service auth |
| `QDRANT_URL` / `QDRANT_API_KEY` | Qdrant cloud endpoint (local host/port used when unset) |
| `NEO4J_HOST` / `NEO4J_PASSWORD` | Neo4j connection |
| `GEMINI_API_KEY` | Gemini key for embeddings/LLM |
| `EMBEDDING_PROVIDER` / `EMBEDDING_MODEL` / `EMBEDDING_DIMENSION` | Embedding provider selection |
| `LLM_PROVIDER` / `LLM_MODEL` / `LLM_TEMPERATURE` | LLM provider selection (`gemini` or `mock`) |
| `POSTGRES_*` | Django database connection |
| `MAX_CHUNKS_PER_FILE` | Ingestion guardrail: caps chunks produced per file (default `5000`) |

## Robustness & Known Behaviors

- **Long requests never block the event loop.** Ingestion (`/ingest`, `/ingest/batch`) and all `/query` and `/database` handlers are plain `def` endpoints, so FastAPI runs them in a worker thread. Health checks and other requests keep responding even while a large ingest or an LLM call is in flight.
- **Embedding retry sleeps are capped** (60s max) and each batch logs progress, so a rate-limited provider degrades gracefully instead of stalling.
- **Free-tier quotas.** The Gemini free tier is ~100 requests/min and **1000/day per model** for `gemini-embedding-2`. When the daily budget is exhausted, ingest/query return a clear `429` error rather than hanging. A single huge file can burn the whole daily budget — `MAX_CHUNKS_PER_FILE` prevents that by capping chunks per ingest (see the `truncated: true` field in the ingest response).
- **Neo4j schema is auto-initialized.** Constraints and indexes for the graph schema are created on first graph use (idempotent `IF NOT EXISTS`). If Neo4j is unreachable, graph features degrade gracefully to vector-only.
- **Hybrid retrieval actually uses both channels.** The BM25 sparse index is built lazily from the Qdrant collection on first query and refreshed as new points arrive, so RRF fuses dense + sparse results (the cross-encoder reranker is disabled in the lean Docker image).
- **Incident analyses are server-grounded.** The LLM writes the narrative (title, root cause, recommendations) but `incident_id`, `evidence`, `sources` and `graph_relationships` are always rebuilt from the actual retrieved chunks, so the API can never cite fabricated sources. Enum fields are normalized and a malformed/unavailable LLM degrades to a grounded fallback instead of a 500.
- **Postmortem ingestion is wired end-to-end.** Besides file uploads (`/ingest`, `/ingest/batch`), the data plane accepts direct text via `/ingest/text`; the Django control plane's "Trigger Ingestion" button on a postmortem calls it through `FastAPIClient.trigger_postmortem_ingestion` and reflects `completed`/`failed` status back on the record.
- **Interactive requests never hang silently.** Gemini calls carry explicit timeouts (60s LLM, 30s/60s embeddings) and retries respect a hard deadline, so a rate-limited provider fails fast with a clear error instead of spinning. The SPA's Analyze screen shows animated progress + an elapsed timer and aborts after 60s with a friendly timeout message.

## API Surface (FastAPI data plane, under `/api/v1`)

- **Ingestion**: `POST /ingest`, `POST /ingest/batch`, `GET /ingest/parsers`
- **Query**: `POST /query/analyze`, `POST /query/search`, `GET /query/intents`, `GET /query/examples`
- **Database inspection**: vectors (`/database/vectors/*`) and graph (`/database/graph/*`)
- **Health**: `/health`, `/api/v1/status`

All endpoints are tenant-scoped via the `X-Organization-ID` header; service calls also send `X-Internal-API-Key`. The SPA injects the internal API key server-side at page load, so no key is hardcoded in the browser.

## Qdrant / qdrant-client Notes

- `qdrant-client` is pinned to `1.19.0` to match the Qdrant cloud server API. Code must use the 1.14+ client API: `query_points`/`query_batch_points` (not the removed `search`/`search_batch`), `scroll_filter=` (not `filter_=`), and `points_count` (the old `vectors_count` attribute was removed from `CollectionInfo`).
- Tenant-filtered fields (`organization_id`, `project_id`, `service`, `level`, `source`, `timestamp`) get **payload indexes** automatically via `QdrantService.ensure_payload_indexes()`; without these, filtered searches fail with `Index required but not found`.
- Neo4j is **best-effort**: if it is unreachable, ingestion and analysis log a warning and continue with vector-only results.

## Interview Prep

See [`questions.md`](questions.md) for a curated set of interview questions covering this project's walkthrough, RAG evaluation, pipeline failure points, and production deployment.
