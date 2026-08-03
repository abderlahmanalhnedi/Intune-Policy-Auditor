"""Non-sensitive local readiness diagnostics."""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from intune_auditor.api.dependencies import response_meta
from intune_auditor.api.response_models import ResponseEnvelope, ResponseMeta
from intune_auditor.application.audit_service import AuditService
from intune_auditor.graph.service import TenantGraphService
from intune_auditor.version import API_VERSION, APP_VERSION

router = APIRouter(prefix="/diagnostics", tags=["Diagnostics"])


class DiagnosticsResult(BaseModel):
    application_version: str
    api_version: str
    offline_mode_ready: bool
    knowledge_pack_count: int = Field(ge=0)
    active_knowledge_pack_count: int = Field(ge=0)
    tenant_configured: bool
    tenant_authenticated: bool
    notes: list[str]


@router.get("", response_model=ResponseEnvelope[DiagnosticsResult])
def diagnostics(
    request: Request,
    meta: ResponseMeta = Depends(response_meta),
) -> ResponseEnvelope[DiagnosticsResult]:
    audit_service: AuditService = request.app.state.audit_service
    tenant_service: TenantGraphService = request.app.state.tenant_service
    packs = audit_service.installed_packs()
    tenant = tenant_service.status()
    return ResponseEnvelope(
        data=DiagnosticsResult(
            application_version=APP_VERSION,
            api_version=API_VERSION,
            offline_mode_ready=True,
            knowledge_pack_count=len(packs),
            active_knowledge_pack_count=sum(pack.active for pack in packs),
            tenant_configured=tenant.configured,
            tenant_authenticated=tenant.authenticated,
            notes=[
                "Diagnostics never include upload content, secrets, or access tokens.",
                "Tenant Mode remains optional; Offline Mode is independent.",
            ],
        ),
        meta=meta,
    )
