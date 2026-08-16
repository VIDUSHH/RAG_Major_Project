# Dataset Ingestion Guide

## Overview

This guide explains how to ingest the log datasets from the `Datasets/` folder into the vector database (Qdrant) and graph database (Neo4j).

## Prerequisites

1. **Docker & Docker Compose** - Required for running Qdrant and Neo4j
2. **Python 3.11+** with the project virtual environment
3. **Dependencies installed**:
   ```bash
   pip install -r fastapi_backend/requirements.txt
   ```

## Quick Start

### 1. Start Infrastructure Services

From the **project root** (so the `.env` with secrets is picked up):

```bash
docker compose -f infrastructure/docker-compose.yml up -d qdrant neo4j
# (or `up -d --build` to also start the FastAPI data plane in Docker)
```

Postgres is only needed for the Django control plane and is behind a profile:
`docker compose -f infrastructure/docker-compose.yml --profile control-plane up -d postgres`.

Verify services are healthy:
```bash
# Qdrant
curl http://localhost:6333/healthz

# Neo4j
curl http://localhost:7474
```

### 2. Run Ingestion Script

```bash
cd scripts
python ingest_datasets.py
```

## What Gets Ingested

| Dataset | Source | Entries | Description |
|---------|--------|---------|-------------|
| SSH.log | SSH auth logs | ~655K | Brute force attempts, successful logins |
| Proxifier.log | Proxy logs | ~13K | Chrome proxy connections |
| HealthApp.log | Android health app | ~114K | Step counter, sensor data |
| Apache.log | Apache error logs | ~52K | Server startup, errors |
| Android.log | Android logcat | ~1.2M | System events, app lifecycle |

## Data Model

### Qdrant (Vector Store)
- **Collection**: `postmortems_v1`
- **Vector**: 768-dim (all-mpnet-base-v2)
- **Payload fields**:
  - `organization_id`, `project_id` (tenant isolation)
  - `service`, `source`, `source_type`
  - `text` (chunk content)
  - `timestamp`
  - `metadata` (chunk_type, parent_id, levels, log_count)

### Neo4j (Graph)
- **Nodes**: Organization, Project, Service, LogEntry
- **Relationships**:
  - `Organization -[:HAS_PROJECT]-> Project`
  - `Project -[:HAS_SERVICE]-> Service`
  - `Service -[:PRODUCED_LOG]-> LogEntry`
  - `LogEntry -[:RELATED_ERROR]-> LogEntry` (error correlations)

## Configuration

Edit `scripts/ingest_datasets.py` `Config` class to customize:
- Database connections
- Organization/Project IDs
- Chunking parameters
- Embedding model

## Troubleshooting

### Qdrant Connection Failed
```bash
# Check if Qdrant is running
docker ps | grep qdrant

# Check logs
docker logs postmortem_qdrant
```

### Neo4j Connection Failed
```bash
# Check if Neo4j is running
docker ps | grep neo4j

# Check logs
docker logs postmortem_neo4j

# Default credentials: neo4j / postmortem_neo4j_pass
```

### Memory Issues
For large datasets (Android.log = 1.2M entries), increase Docker memory:
```yaml
# In docker-compose.yml
services:
  qdrant:
    deploy:
      resources:
        limits:
          memory: 4G
```

## Verification

After ingestion, verify data:

```bash
# Qdrant - count points
curl -X POST http://localhost:6333/collections/postmortems_v1/points/count

# Neo4j - count nodes
cypher-shell -u neo4j -p postmortem_neo4j_pass "MATCH (n) RETURN labels(n), count(n)"

# Search test
curl -X POST http://localhost:6333/collections/postmortems_v1/points/search \
  -H "Content-Type: application/json" \
  -d '{"vector": [0.1]*768, "limit": 5}'
```

## Next Steps

After successful ingestion:
1. Start FastAPI backend: `cd fastapi_backend && python -m app.main`
2. Test RAG queries via `/api/v1/search`
3. Test MCP tools via configured clients
4. Start Django control plane for full application