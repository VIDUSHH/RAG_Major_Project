import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import logger, setup_logging

setup_logging()

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.PROJECT_NAME} in environment: {settings.ENVIRONMENT}")
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health"])
async def root_health():
    """Root health check endpoint."""
    return {"status": "healthy", "service": "fastapi_data_plane", "version": "1.0.0"}


# Serve static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    # Bump whenever the SPA assets change so browsers never serve a stale
    # app.js/styles.css even if an intermediary caches the HTML shell.
    _asset_version = str(
        int((STATIC_DIR / "app.js").stat().st_mtime)
        + int((STATIC_DIR / "styles.css").stat().st_mtime)
    )

    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        # Inject the current internal API key into the page so the SPA can call
        # the /api/v1 endpoints without hardcoding a (potentially stale) key.
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        html = html.replace(
            "__INTERNAL_API_KEY__",
            json.dumps(settings.FASTAPI_INTERNAL_API_KEY),
        )
        # Version the static asset URLs so a redeploy always pulls fresh JS/CSS.
        html = html.replace("__APP_VERSION__", _asset_version)
        # Never cache the shell or static assets: the SPA changes frequently and
        # a stale cached app.js is a classic "UI looks frozen" source of bugs.
        return HTMLResponse(html, headers={"Cache-Control": "no-store"})

    @app.get("/{path:path}", include_in_schema=False)
    async def serve_spa(path: str):
        # Only serve real static files. Everything else falls through so the
        # catch-all never shadows /health, /docs or the /api/v1 endpoints.
        file_path = STATIC_DIR / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path, headers={"Cache-Control": "no-store"})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
