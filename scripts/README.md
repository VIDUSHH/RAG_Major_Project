# Scripts

Developer utility scripts for the RAG Postmortem Intelligence System.

Scripts are added here as the project grows — seeding data, running evaluations,
managing collections, etc.

## Available Scripts

_None yet — scripts will be added from Phase 2 onward._

## Planned Scripts

| Script | Phase | Purpose |
|--------|-------|---------|
| `seed_demo_data.py` | 2+ | Seed demo organizations, projects, incidents |
| `create_qdrant_collections.py` | 8 | Initialize Qdrant collections with correct config |
| `init_neo4j_schema.py` | 9 | Create Neo4j indexes and constraints |
| `evaluate_retrieval.py` | 24 | Run retrieval evaluation against test queries |
| `ingest_sample_postmortems.py` | 4 | Bulk-ingest sample postmortem documents |

## Usage Convention

All scripts should be run from the workspace root:

```bash
python scripts/<script_name>.py
```

Scripts must not import from `sys.path` hacks. The workspace root should
be on the Python path (e.g. via `venv` + `pip install -e .` or explicit `PYTHONPATH`).
