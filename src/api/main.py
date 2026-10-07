"""FastAPI application — ADEP Platform API [§9, BLK-018].

Scaffold with CORS, health check, OpenAPI docs, and route mounting.
All routes are under /api/v1 prefix to match frontend expectations.

Run with: uvicorn src.api.main:app --reload
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from src.config import settings
from src.definitions.base import InvalidEntityIdError
from src.observability.context import set_context, request_id_var
from src.observability.logging import configure_logging

# Configure structured logging on import [BLK-130]
configure_logging(format_type=settings.log_format, level=settings.log_level)

logger = logging.getLogger(__name__)


class HTTPError(BaseModel):
    """Standard error response model for all endpoints [Wave 5.2]."""

    detail: str | dict = Field(description="Error detail message or structured info")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        A configured FastAPI app instance.
    """
    app = FastAPI(
        title="ADEP — Agentic Document Extraction Platform",
        description=(
            "Backend API for defining and running document extraction agents.\n\n"
            "## Resources\n"
            "- **Definitions**: Agent definitions pairing skills + templates\n"
            "- **Skills**: ReAct reasoning skills with tool preferences\n"
            "- **Templates**: Pydantic schemas defining extraction outcomes\n"
            "- **Runs**: Extraction run lifecycle + SSE streaming\n"
            "- **Admin**: Budget, stats, and configuration endpoints\n"
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/api/v1/openapi.json",
        responses={
            404: {"model": HTTPError, "description": "Resource not found"},
            409: {"model": HTTPError, "description": "Resource already exists"},
            429: {"model": HTTPError, "description": "Budget limit exceeded"},
            500: {"model": HTTPError, "description": "Internal server error"},
        },
    )

    # An entity id that is invalid or would leave the store directory is a client error (ADE-72)
    @app.exception_handler(InvalidEntityIdError)
    async def invalid_entity_id_handler(request: Request, exc: InvalidEntityIdError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    # CORS — allow frontend dev server [§9]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request logging middleware with context propagation [Wave 5.4, BLK-130]
    @app.middleware("http")
    async def request_logging(request: Request, call_next):
        rid = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        start_time = time.perf_counter()

        # Set request_id in contextvars for structured logging [BLK-130]
        token = request_id_var.set(rid)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "HTTP %s %s %d %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={
                "method": request.method,
                "path": str(request.url.path),
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 1),
            },
        )
        response.headers["X-Request-ID"] = rid
        return response

    # Auth middleware [BLK-122]
    from src.api.auth import install_auth_middleware

    install_auth_middleware(app)

    # Rate limiting middleware [BLK-123]
    from src.api.rate_limit import install_rate_limit_middleware

    install_rate_limit_middleware(app)

    # Mount routes under /api/v1
    from src.api.routes.definitions import router as definitions_router
    from src.api.routes.documents import router as documents_router
    from src.api.routes.keys import router as keys_router
    from src.api.routes.runs import router as runs_router
    from src.api.routes.skills import router as skills_router
    from src.api.routes.templates import router as templates_router
    from src.api.routes.webhooks import router as webhooks_router
    from src.api.routes.benchmarks import router as benchmarks_router
    from src.api.routes.batches import router as batches_router

    app.include_router(definitions_router, prefix="/api/v1")
    app.include_router(documents_router, prefix="/api/v1")
    app.include_router(keys_router, prefix="/api/v1")
    app.include_router(skills_router, prefix="/api/v1")
    app.include_router(templates_router, prefix="/api/v1")
    app.include_router(runs_router, prefix="/api/v1")
    app.include_router(webhooks_router, prefix="/api/v1")
    app.include_router(benchmarks_router, prefix="/api/v1")
    app.include_router(batches_router, prefix="/api/v1")

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def landing_page() -> str:
        """Landing page with links to docs and resources."""
        return """
        <!DOCTYPE html>
        <html>
        <head><title>ADEP — Agentic Document Extraction Platform</title></head>
        <body style="font-family: sans-serif; max-width: 720px; margin: 2rem auto;">
            <h1>ADEP — Agentic Document Extraction Platform</h1>
            <p>Backend API for defining and running document extraction agents.</p>
            <h2>Links</h2>
            <ul>
                <li><a href="/docs">Interactive API Docs (Swagger)</a></li>
                <li><a href="/redoc">ReDoc API Docs</a></li>
                <li><a href="/api/v1/openapi.json">OpenAPI JSON Spec</a></li>
                <li><a href="/health">Health Check</a></li>
                <li><a href="/api/v1/health">Health Check (v1)</a></li>
                <li><a href="/api/v1/budget">Budget Status</a></li>
            </ul>
            <h2>Key Endpoints</h2>
            <ul>
                <li><code>POST /api/v1/definitions</code> — Create an agent definition</li>
                <li><code>POST /api/v1/runs</code> — Start an extraction run</li>
                <li><code>GET /api/v1/runs/{id}/stream</code> — SSE stream for a run</li>
                <li><code>GET /api/v1/budget</code> — Budget consumption status</li>
            </ul>
        </body>
        </html>
        """

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint — basic liveness probe."""
        return {"status": "ok"}

    @app.get("/api/v1/health")
    async def health_check_v1() -> dict[str, str]:
        """Health check endpoint under API prefix."""
        return {"status": "ok"}

    @app.get("/ready")
    async def readiness_check() -> dict[str, str]:
        """Readiness check — verifies file store and config are available."""
        from src.definitions.store import get_store

        try:
            store = get_store()
            store.list_definitions()
            return {"status": "ready"}
        except Exception as e:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "detail": str(e)},
            )

    # i18n — locales endpoint [BLK-065]
    @app.get("/api/v1/locales")
    async def get_locales() -> list[dict[str, str]]:
        """List supported locales for i18n [BLK-065]."""
        from src.agent.i18n import get_locales as _get_locales

        return _get_locales()

    # Analytics endpoints [BLK-066]
    @app.get("/api/v1/admin/analytics/skills")
    async def analytics_skills() -> list[dict[str, Any]]:
        """Per-skill analytics [BLK-066]."""
        from src.agent.analytics import get_skill_analytics

        return get_skill_analytics()

    @app.get("/api/v1/admin/analytics/templates")
    async def analytics_templates() -> list[dict[str, Any]]:
        """Per-template analytics [BLK-066]."""
        from src.agent.analytics import get_template_analytics

        return get_template_analytics()

    @app.get("/api/v1/admin/analytics/documents")
    async def analytics_documents() -> dict[str, Any]:
        """Per-document-type analytics [BLK-066]."""
        from src.agent.analytics import get_document_analytics

        return get_document_analytics()

    @app.get("/api/v1/admin/analytics/failures")
    async def analytics_failures() -> dict[str, Any]:
        """Failure analysis [BLK-066]."""
        from src.agent.analytics import get_failure_analytics

        return get_failure_analytics()

    # Cache management endpoints [BLK-124]
    @app.get("/api/v1/admin/cache/stats")
    async def cache_stats() -> dict[str, Any]:
        """Get tool result cache statistics [BLK-124]."""
        from src.tools.cache import get_cache

        return get_cache().stats()

    @app.delete("/api/v1/admin/cache")
    async def clear_cache() -> dict[str, Any]:
        """Clear the tool result cache [BLK-124]."""
        from src.tools.cache import get_cache

        cleared = get_cache().clear()
        return {"cleared": cleared}

    # Store management endpoints [BLK-036]
    @app.get("/api/v1/admin/store/info")
    async def store_info() -> dict[str, Any]:
        """Get current store backend information [BLK-036]."""
        return {
            "backend": settings.store_backend,
            "db_path": settings.store_db_path if settings.store_backend == "sqlite" else None,
        }

    @app.post("/api/v1/admin/store/migrate")
    async def migrate_store() -> dict[str, Any]:
        """Migrate file-based store to SQLite [BLK-036].

        Reads all entities from the current file-based store and inserts
        them into the SQLite store. Existing entities in the target store
        are preserved (not overwritten).
        """
        from src.definitions.store import DefinitionStore
        from src.definitions.db_store import DatabaseDefinitionStore

        file_store = DefinitionStore()
        db_store = DatabaseDefinitionStore(db_path=settings.store_db_path)
        count = db_store.migrate_from_file_store(file_store)
        return {"migrated_count": count, "db_path": settings.store_db_path}

    # Queue admin endpoint [BLK-129]
    @app.get("/api/v1/admin/queue")
    async def queue_status() -> dict[str, Any]:
        """Get async run queue status [BLK-129]."""
        from src.api.run_executor import get_executor

        return get_executor().get_queue_status()

    # Startup/shutdown hooks for RunExecutor [BLK-129]
    @app.on_event("startup")
    async def startup_executor() -> None:
        """Start the async run executor and recover orphaned runs [BLK-129]."""
        from src.api.run_executor import get_executor

        executor = get_executor()
        executor.start()
        orphans = executor.recover_orphans()
        if orphans:
            logger.info("Recovered %d orphaned runs on startup [BLK-129]", orphans)

    @app.on_event("shutdown")
    async def shutdown_executor() -> None:
        """Graceful shutdown — drain in-flight runs [BLK-129]."""
        from src.api.run_executor import get_executor

        executor = get_executor()
        await executor.stop()

    return app


app = create_app()
