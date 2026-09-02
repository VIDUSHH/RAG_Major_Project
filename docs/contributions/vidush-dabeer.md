# Vidush Dabeer

**GitHub:** [VIDUSHH](https://github.com/VIDUSHH)
**Email:** vidushdabeer06@gmail.com

---

## Assigned Role

**RAG / Backend Lead** — Primary engineer for the core RAG pipeline and all backend services.

Per the project report (`RAG_Postmortem_Intelligence_Weekly_Daily_Report_July20_Aug29_2026.md`), Vidush acted as the primary engineer for the core RAG pipeline and the backend, with primary ownership over RAG architecture, FastAPI, Qdrant, Neo4j, LLM grounding, embeddings, and hybrid retrieval.

---

## Contribution Summary

Vidush designed the system architecture (dual-plane FastAPI/Django) and the RAG pipeline flow: query understanding → hybrid retrieval → graph retrieval → context assembly → LLM generation → grounding.

- Designed and implemented the embedding provider abstraction (local sentence-transformers + Gemini), the hybrid retriever (dense Qdrant + sparse BM25 + RRF fusion), the graph retriever, and the query understanding engine.
- Implemented the LLM provider with server-side grounding (prevents fabricated citations), the `RAGPipeline` orchestrator, and all query/analysis endpoints.
- Built the Qdrant vector service (collection management, payload indexes, dimension-mismatch recreation) and the core Neo4j graph service (nodes, relationships, schema/constraints).
- Owned the ingestion pipeline, multi-tenancy enforcement, and the event-loop freeze fix; wrote the security, LLM grounding, ingestion, and activity test suites.

---

## Contributed Files

- `fastapi_backend/app/embeddings/provider.py` — embedding provider abstraction and factory
- `fastapi_backend/app/retrieval/hybrid.py` — dense + BM25 sparse + RRF hybrid retriever
- `fastapi_backend/app/retrieval/graph_retrieval.py` — Neo4j graph retriever
- `fastapi_backend/app/rag/pipeline.py` — RAG pipeline orchestrator and query understanding engine
- `fastapi_backend/app/rag/models.py` — shared RAG data models
- `fastapi_backend/app/llm/provider.py` — LLM provider (Gemini + mock) with server-side grounding
- `fastapi_backend/app/services/vector_service.py` — Qdrant vector service
- `fastapi_backend/app/services/graph_service.py` — core Neo4j graph service
- `fastapi_backend/app/services/activity_service.py` — activity log service
- `fastapi_backend/app/api/v1/query.py` — query/analysis API endpoints
- `fastapi_backend/app/api/v1/ingestion.py` — ingestion pipeline (`_ingest_entries` helper)
- `fastapi_backend/app/core/config.py`, `app/core/security.py`, `app/core/dependencies.py` — configuration, security, tenant dependencies
- `django_backend/apps/core/clients.py`, `django_backend/apps/accounts`, `django_backend/apps/organizations`, `django_backend/apps/projects` — Django control-plane core
- `tests/fastapi_backend/test_security.py`, `test_llm.py`, `test_ingestion.py`, `test_activity_service.py`, `test_health.py` — core test suites

---

## Lessons Learnt

- Building the embedding provider as an abstraction let the system hot-swap between Gemini API and local sentence-transformers without code changes, saving API quota and enabling offline operation.
- Synchronous blocking calls in `async def` handlers freeze the FastAPI event loop; converting handlers to plain `def` runs blocking work safely in worker threads.
- Lazy construction of the BM25 corpus from Qdrant scroll on first query (with periodic refresh) keeps ingestion write-only and fast while still delivering true hybrid retrieval.
- Server-side grounding of LLM output (rebuilding evidence-derived fields from actual retrieved chunks) structurally prevents fabricated citations.

---

## Skills Learnt

- RAG architecture and pipeline design (query understanding, hybrid retrieval, graph retrieval, context assembly, generation, grounding)
- FastAPI API design and asynchronous/threaded execution models
- Qdrant vector store (collections, payload indexes, dimension-mismatch recreation)
- Neo4j graph database (nodes, relationships, schema/constraints, mypy/StrEnum Cypher rendering)
- Hybrid retrieval: BM25 + dense vector search + Reciprocal Rank Fusion (RRF)
- LLM integration and server-side grounding (Gemini + mock fallback)
- sentence-transformers embeddings, pytest, multi-tenancy enforcement

---

## Contribution Links

- [fastapi_backend RAG pipeline](https://github.com/VIDUSHH/RAG_Major_Project/tree/main/fastapi_backend/app/rag)
- [fastapi_backend retrieval](https://github.com/VIDUSHH/RAG_Major_Project/tree/main/fastapi_backend/app/retrieval)
- [fastapi_backend LLM provider](https://github.com/VIDUSHH/RAG_Major_Project/tree/main/fastapi_backend/app/llm)
- [fastapi_backend embeddings](https://github.com/VIDUSHH/RAG_Major_Project/tree/main/fastapi_backend/app/embeddings)
- [fastapi_backend services](https://github.com/VIDUSHH/RAG_Major_Project/tree/main/fastapi_backend/app/services)
- [fastapi_backend API v1](https://github.com/VIDUSHH/RAG_Major_Project/tree/main/fastapi_backend/app/api/v1)
- [fastapi_backend core](https://github.com/VIDUSHH/RAG_Major_Project/tree/main/fastapi_backend/app/core)
- [tests/fastapi_backend](https://github.com/VIDUSHH/RAG_Major_Project/tree/main/tests/fastapi_backend)
- [django_backend core](https://github.com/VIDUSHH/RAG_Major_Project/tree/main/django_backend/apps/core)
