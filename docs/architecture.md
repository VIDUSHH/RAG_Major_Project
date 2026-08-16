# Architecture

**RAG-Based Postmortem Intelligence System**

> This document reflects Phase 1 of the implementation. It will be updated as each phase completes.

---

## Overview

The system is a dual-plane backend platform that ingests historical postmortems, incident reports, and application logs, then enables engineers to query the resulting knowledge base for root-cause analysis, incident similarity, remediation recommendations, and automated postmortem generation.

---

## Dual-Plane Architecture

```
                      CLIENTS
                         |
          +--------------+--------------+
          |                             |
          v                             v
    Django (Control Plane)         MCP Clients
    :8000                          (Phase 19)
          |
          v
     PostgreSQL
          |
          | authenticated internal call (Phase 3)
          v
    FastAPI (AI / Data Plane)
    :8001
          |
    +-----+------+---------+
    |            |         |
    v            v         v
  Qdrant       Neo4j    Gemini LLM
  (Phase 8)  (Phase 9) (Phase 15)
```

### Django — Control Plane

Responsible for all relational metadata and administrative operations:

| Concern | Detail |
|---------|--------|
| Auth | Token-based via DRF + SimpleJWT (Phase 3) |
| RBAC | Organization-scoped roles: OWNER / ADMIN / ENGINEER / VIEWER (Phase 3) |
| Tenancy | Organization model, membership table (Phase 2) |
| Domain data | User, Organization, Project, Service, Incident, Postmortem, LogSource, AuditLog, APIKey (Phase 2) |
| Admin UI | Django Admin (Phase 2) |
| Database | PostgreSQL exclusively |

**What Django does NOT do:** embedding generation, vector retrieval, graph queries, LLM orchestration.

### FastAPI — AI / Data Plane

Responsible for all AI and data-processing operations:

| Concern | Detail |
|---------|--------|
| Ingestion | PDF, Markdown, TXT, JSON, HTML (Phase 4) |
| Chunking | Structured, semantic, hierarchical (Phase 6) |
| Embeddings | SentenceTransformers `all-mpnet-base-v2` / 768-dim (Phase 7) |
| Vector store | Qdrant with tenant-aware payload filtering (Phase 8) |
| Sparse search | BM25 (Phase 10) |
| Hybrid retrieval | Dense + BM25 + RRF (Phase 11) |
| Reranking | cross-encoder/ms-marco-MiniLM-L-6-v2 (Phase 12) |
| Graph | Neo4j GraphRAG (Phase 9 / Phase 13) |
| RAG | Full retrieval-augmented generation pipeline (Phase 14) |
| LLM | Google Gemini (Phase 15) |
| MCP | MCP server + tools (Phase 19) |

---

## Five-Layer Architecture

```
Layer 1 — Storage
  PostgreSQL | Qdrant | Neo4j | Object Storage (abstracted)

Layer 2 — Ingestion
  Document parsers | Log ingestion | Source connectors | Kafka producers (future)

Layer 3 — Processing
  Parsing | Chunking | Embedding | Graph entity extraction | Indexing

Layer 4 — API + MCP
  FastAPI versioned API | Django REST API | MCP server

Layer 5 — Intelligence
  RAG pipeline | Incident analysis | Prediction | Postmortem generation
```

---

## Technology Stack (Phase 1 — Installed)

| Component | Technology | Version |
|-----------|-----------|---------|
| Django | Control plane framework | 5.1.15 |
| DRF | REST API framework | 3.16.0 |
| SimpleJWT | Token auth (Phase 3) | 5.5.0 |
| FastAPI | AI/data plane framework | 0.115.12 |
| Pydantic | Schema validation | 2.11.3 |
| pydantic-settings | Env config | 2.9.1 |
| PostgreSQL | Relational database | 16 (Docker) |
| Qdrant | Vector store | 1.8.3 (Docker) |
| Neo4j | Graph database | 5.18.0 (Docker) |
| python-json-logger | Structured logging | 3.3.0 |

### Future Stack (not yet installed)

| Component | Phase |
|-----------|-------|
| SentenceTransformers | 7 |
| Qdrant Python client | 8 |
| neo4j Python driver | 9 |
| rank-bm25 | 10 |
| google-generativeai | 15 |
| kafka-python | 20 |
| pyspark | 21 |
| mlflow | 25 |
| dvc | 26 |
| redis / celery | When actually required |

---

## Repository Layout

```
RAG Project/
├── django_backend/          # Control plane
│   ├── config/              # Django settings, URLs, ASGI/WSGI
│   └── apps/
│       ├── accounts/        # User model
│       ├── organizations/   # Organization + membership
│       ├── projects/
│       ├── services/
│       ├── incidents/
│       ├── postmortems/
│       ├── log_sources/
│       ├── audit/
│       └── api_keys/
│
├── fastapi_backend/         # AI / data plane
│   └── app/
│       ├── core/            # config, logging, security, dependencies
│       ├── api/v1/          # Route handlers (thin layer only)
│       ├── schemas/         # Pydantic request/response models
│       ├── ingestion/       # Parsers, connectors (Phase 4+)
│       ├── processing/      # Chunking, normalization (Phase 6+)
│       ├── embeddings/      # EmbeddingProvider interface (Phase 7+)
│       ├── retrieval/       # Dense, sparse, hybrid, reranking (Phase 10+)
│       ├── graph/           # Neo4j client (Phase 9+)
│       ├── rag/             # RAG orchestrator (Phase 14+)
│       ├── llm/             # LLMProvider interface (Phase 15+)
│       └── mcp/             # MCP server (Phase 19+)
│
├── infrastructure/
│   ├── docker-compose.yml   # Local dev: postgres + qdrant + neo4j + django + fastapi
│   └── docker/
│       ├── Dockerfile.django
│       └── Dockerfile.fastapi
│
├── tests/
│   ├── django_backend/
│   └── fastapi_backend/
│
├── docs/                    # Architecture and operational docs
├── scripts/                 # Developer utility scripts
├── pyproject.toml           # Ruff, mypy config
├── pytest.ini               # Test config
├── Makefile                 # Developer shortcuts
└── .env.example             # Environment variable documentation
```

---

## Engineering Principles (Key Subset)

- PostgreSQL is the only permitted application database. No SQLite fallback.
- Never expose infrastructure details (hosts, credentials) through health or status endpoints.
- CORS must be configurable via `CORS_ALLOWED_ORIGINS` env var; never unconditionally open in non-debug mode.
- No runtime `sys.path` manipulation.
- All secrets via environment variables. `.env` is gitignored. `.env.example` is maintained.
- Tenant isolation is enforced server-side, never client-side.
- Domain logic stays out of HTTP route handlers.
- RAG logic stays out of FastAPI route handlers.
- Infrastructure clients are behind service/repository abstractions.

---

## Phase Status

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Repository audit | ✅ Complete |
| 1 | Project foundation | ✅ Complete |
| 2 | Django domain models | ⏳ Next |
| 3 | Authentication / RBAC | ⏳ Pending |
| 4–19 | Data + AI pipeline | ⏳ Pending |
| 20+ | Streaming, MLOps, Infra | ⏳ Pending |
