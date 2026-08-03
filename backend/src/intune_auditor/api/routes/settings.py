"""Explicit local privacy preferences and destructive cleanup actions."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from intune_auditor.api.dependencies import response_meta
from intune_auditor.api.response_models import ResponseEnvelope, ResponseMeta
from intune_auditor.application.audit_service import AuditService
from intune_auditor.config import get_settings
from intune_auditor.graph.service import TenantGraphService
from intune_auditor.persistence.database import Database

router = APIRouter(prefix="/settings", tags=["Settings"])


class LocalPreferences(BaseModel):
    history_enabled: bool = False
    retention_days: int = Field(default=30, ge=1, le=3650)
    save_reports: bool = False
    automatic_cleanup: bool = True


class PublicSettings(LocalPreferences):
    bind_address: str
    tenant_mode_configured: bool
    raw_uploads_retained: bool = False


class TokenCacheClearResult(BaseModel):
    token_cache_deleted: bool


def database(request: Request) -> Database:
    return request.app.state.database  # type: ignore[no-any-return]


def audit_service(request: Request) -> AuditService:
    return request.app.state.audit_service  # type: ignore[no-any-return]


def tenant_service(request: Request) -> TenantGraphService:
    return request.app.state.tenant_service  # type: ignore[no-any-return]


@router.get("", response_model=ResponseEnvelope[PublicSettings])
def public_settings(
    service: AuditService = Depends(audit_service),
    meta: ResponseMeta = Depends(response_meta),
) -> ResponseEnvelope[PublicSettings]:
    settings = get_settings()
    preferences = LocalPreferences.model_validate(service.preferences())
    return ResponseEnvelope(
        data=PublicSettings(
            **preferences.model_dump(),
            bind_address=settings.host,
            tenant_mode_configured=bool(settings.tenant_id and settings.client_id),
        ),
        meta=meta,
    )


@router.put("", response_model=ResponseEnvelope[LocalPreferences])
def update_settings(
    preferences: LocalPreferences,
    store: Database = Depends(database),
    meta: ResponseMeta = Depends(response_meta),
) -> ResponseEnvelope[LocalPreferences]:
    store.set_setting("local_preferences", preferences.model_dump(mode="json"))
    return ResponseEnvelope(data=preferences, meta=meta)


@router.get("/audit-history", response_model=ResponseEnvelope[list[dict[str, object]]])
def audit_history(
    store: Database = Depends(database),
    meta: ResponseMeta = Depends(response_meta),
) -> ResponseEnvelope[list[dict[str, object]]]:
    store.delete_expired_audits(datetime.now(UTC))
    return ResponseEnvelope(data=store.list_audit_summaries(), meta=meta)


@router.delete("/local-audit-data", response_model=ResponseEnvelope[dict[str, int]])
def delete_local_audit_data(
    service: AuditService = Depends(audit_service),
    store: Database = Depends(database),
    meta: ResponseMeta = Depends(response_meta),
) -> ResponseEnvelope[dict[str, int]]:
    service.store.clear()
    removed = store.clear_audits()
    reports = service.data_dir / "reports"
    report_count = (
        sum(1 for item in reports.rglob("*") if item.is_file()) if reports.is_dir() else 0
    )
    if reports.is_dir():
        shutil.rmtree(reports)
    return ResponseEnvelope(
        data={"audit_records": removed, "report_files": report_count}, meta=meta
    )


@router.post("/clear-temporary", response_model=ResponseEnvelope[dict[str, int]])
def clear_temporary_files(
    service: AuditService = Depends(audit_service),
    meta: ResponseMeta = Depends(response_meta),
) -> ResponseEnvelope[dict[str, int]]:
    target = (service.data_dir / "tmp").resolve()
    target.relative_to(service.data_dir.resolve())
    count = sum(1 for item in target.rglob("*") if item.is_file()) if target.is_dir() else 0
    if target.is_dir():
        shutil.rmtree(target)
    return ResponseEnvelope(data={"temporary_files": count}, meta=meta)


@router.post("/clear-token-cache", response_model=ResponseEnvelope[TokenCacheClearResult])
def clear_token_cache(
    tenant: TenantGraphService = Depends(tenant_service),
    meta: ResponseMeta = Depends(response_meta),
) -> ResponseEnvelope[TokenCacheClearResult]:
    tenant.sign_out()
    return ResponseEnvelope(data=TokenCacheClearResult(token_cache_deleted=True), meta=meta)


@router.post("/reset", response_model=ResponseEnvelope[dict[str, int]])
def reset_application_settings(
    store: Database = Depends(database),
    meta: ResponseMeta = Depends(response_meta),
) -> ResponseEnvelope[dict[str, int]]:
    return ResponseEnvelope(data={"settings_removed": store.reset_settings()}, meta=meta)
