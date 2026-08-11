import sys
from pathlib import Path

# Ensure fastapi_backend directory is in sys.path for direct imports
fastapi_dir = Path(__file__).resolve().parent.parent
if str(fastapi_dir) not in sys.path:
    sys.path.insert(0, str(fastapi_dir))

"""FastAPI AI & Data Plane Package."""

