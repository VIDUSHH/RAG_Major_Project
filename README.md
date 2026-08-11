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
                  PostgreSQL Redis Auth
                       |
                       | internal API
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

## Quick Start (Phase 1)

### Setup Environment
```bash
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r django_backend/requirements.txt
pip install -r fastapi_backend/requirements.txt
```

### Run Local Infrastructure (Docker Compose)
```bash
docker compose -f infrastructure/docker-compose.yml up -d
```

### Run Django Control Plane
```bash
cd django_backend
python manage.py migrate
python manage.py runserver 8000
```

### Run FastAPI Data Plane
```bash
cd fastapi_backend
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Run Tests
```bash
pytest tests/
```
