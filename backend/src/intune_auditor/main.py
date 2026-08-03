"""FastAPI application factory and production SPA hosting."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from intune_auditor.api.middleware import RequestSizeLimitMiddleware, SecurityAndRequestIdMiddleware
from intune_auditor.api.routes import router as api_routes
from intune_auditor.application.audit_service import AuditService
from intune_auditor.config import get_settings
from intune_auditor.graph.service import TenantGraphService
from intune_auditor.logging_config import configure_logging
from intune_auditor.persistence.database import Database
from intune_auditor.security.limits import DEFAULT_LIMITS
from intune_auditor.version import API_VERSION, APP_VERSION


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    database = Database(settings)
    repository_root = Path(__file__).resolve().parents[3]
    audit_service = AuditService(
        repository_root,
        database=database,
        data_dir=settings.data_dir,
        retention_days=settings.retention_days,
        history_enabled=settings.history_enabled,
        save_reports=settings.save_reports,
    )
    tenant_service = TenantGraphService(
        settings.tenant_id,
        settings.client_id,
        settings.token_cache_path,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        database.initialize()
        try:
            yield
        finally:
            database.close()

    app = FastAPI(
        title="Intune Policy Auditor API",
        version=APP_VERSION,
        description="Read-only, deterministic analysis of exported Intune policies.",
        lifespan=lifespan,
        docs_url=f"/api/{API_VERSION}/docs",
        openapi_url=f"/api/{API_VERSION}/openapi.json",
    )
    app.state.database = database
    app.state.audit_service = audit_service
    app.state.tenant_service = tenant_service
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Accept", "Content-Type", "X-Request-ID"],
    )
    app.add_middleware(
        RequestSizeLimitMiddleware,
        maximum_bytes=DEFAULT_LIMITS.total_upload_bytes + 10 * 1024 * 1024,
    )
    app.add_middleware(SecurityAndRequestIdMiddleware)

    versioned = APIRouter(prefix=f"/api/{API_VERSION}")
    versioned.include_router(api_routes)
    app.include_router(versioned)

    dist = settings.frontend_dist
    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="frontend-assets")

    @app.get("/{path:path}", include_in_schema=False, response_model=None)
    def spa(path: str) -> Response:
        if path.startswith("api/"):
            return JSONResponse({"detail": "Not found"}, status_code=404)
        index = dist / "index.html"
        if index.is_file():
            return FileResponse(index)
        return JSONResponse(
            {
                "application": "Intune Policy Auditor",
                "status": "frontend_not_built",
                "next_action": "Run the build script before production startup.",
            },
            status_code=503,
        )

    return app


app = create_app()
