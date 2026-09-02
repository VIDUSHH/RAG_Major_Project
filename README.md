# Atit Morutagi — Frontend / Infrastructure Lead

**Folder for Atit Morutagi's individual contributions.**

Commit and push the contents of this folder from Atit's GitHub account.

## Contents (contributed files)

- `fastapi_backend/app/static/` — complete SPA frontend (index.html, app.js, styles.css): six tabs, modals, animated ingest overlay, ChatGPT-style panels, SVG dependency-graph visualization, cache-busting asset URLs, hidden-overlay CSS fix
- `fastapi_backend/app/ingestion/parsers.py` — all log/document parsers (SSH, Apache, Android, Proxifier, HealthApp, text, CSV, Markdown, JSON)
- `fastapi_backend/app/processing/chunking.py` — semantic + fixed chunking strategies
- `fastapi_backend/app/embeddings/provider.py` — Gemini embedding provider (batch + retry)
- `fastapi_backend/app/services/graph_service.py` — Neo4j graph query methods (service graph, incident graph, error patterns)
- `fastapi_backend/app/services/activity_service.py` — activity logging integration
- `fastapi_backend/app/api/v1/database.py` — database inspection endpoints (graph, activity)
- `fastapi_backend/app/main.py` — static serving / SPA wiring
- `infrastructure/docker-compose.yml`, `infrastructure/docker/` — Docker Compose topology and Dockerfiles
- `django_backend/apps/{services,incidents,postmortems,log_sources,api_keys,audit}/models.py` — control-plane models