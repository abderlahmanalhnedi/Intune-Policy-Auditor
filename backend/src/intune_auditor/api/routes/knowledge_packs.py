"""Knowledge-pack catalog and validation status."""

import json
from datetime import date

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from intune_auditor.api.dependencies import response_meta
from intune_auditor.api.errors import ProblemError
from intune_auditor.api.response_models import ResponseEnvelope, ResponseMeta
from intune_auditor.application.audit_service import AuditService
from intune_auditor.domain.models import KnowledgePackManifest
from intune_auditor.knowledge.loader import LoadedKnowledgePack, PackValidationReport
from intune_auditor.security.filenames import validate_upload_name

router = APIRouter(prefix="/knowledge-packs", tags=["Knowledge Packs"])


class KnowledgePackSummary(BaseModel):
    pack_id: str
    name: str
    vendor: str
    product: str
    version: str
    platform: str
    status: str
    verification_date: date
    source: str
    data_sha256: str
    setting_count: int
    exact_value_count: int
    age_days: int
    stale: bool
    validation_state: str
    active: bool
    synthetic: bool


def audit_service(request: Request) -> AuditService:
    return request.app.state.audit_service  # type: ignore[no-any-return]


def summary(pack: LoadedKnowledgePack, validation_state: str) -> KnowledgePackSummary:
    manifest = pack.manifest
    return KnowledgePackSummary(
        pack_id=manifest.pack_id,
        name=manifest.baseline_name,
        vendor=manifest.vendor,
        product=manifest.product,
        version=manifest.baseline_version,
        platform=manifest.platform.value,
        status=manifest.status.value,
        verification_date=manifest.verified_at,
        source=manifest.source_reference,
        data_sha256=manifest.data_sha256,
        setting_count=manifest.setting_count,
        exact_value_count=manifest.exact_value_count,
        age_days=pack.age_days,
        stale=pack.age_days > 180,
        validation_state=validation_state,
        active=pack.active,
        synthetic=manifest.status.value == "synthetic",
    )


@router.get("", response_model=ResponseEnvelope[list[KnowledgePackSummary]])
def list_knowledge_packs(
    service: AuditService = Depends(audit_service),
    meta: ResponseMeta = Depends(response_meta),
) -> ResponseEnvelope[list[KnowledgePackSummary]]:
    items = [
        summary(pack, "valid" if service.pack_loader.validate(pack.path).valid else "invalid")
        for pack in service.installed_packs()
    ]
    return ResponseEnvelope(data=items, meta=meta)


@router.post("/validate", response_model=ResponseEnvelope[PackValidationReport])
async def validate_knowledge_pack(
    pack: UploadFile = File(description="ZIP containing one manifest.json and settings JSON"),
    service: AuditService = Depends(audit_service),
    meta: ResponseMeta = Depends(response_meta),
) -> ResponseEnvelope[PackValidationReport]:
    try:
        filename = validate_upload_name(pack.filename or "unnamed")
    except ValueError as exc:
        await pack.close()
        raise ProblemError(status=422, title="Knowledge pack rejected", detail=str(exc)) from exc
    if not filename.lower().endswith(".zip"):
        await pack.close()
        raise ProblemError(
            status=422, title="Knowledge pack rejected", detail="pack_file_must_be_zip"
        )
    content = await pack.read(service.limits.single_file_bytes + 1)
    await pack.close()
    if len(content) > service.limits.single_file_bytes:
        raise ProblemError(
            status=413, title="Knowledge pack rejected", detail="single_file_size_exceeded"
        )
    try:
        report = service.pack_manager.validate_archive(content)
    except ValueError as exc:
        raise ProblemError(status=422, title="Knowledge pack rejected", detail=str(exc)) from exc
    return ResponseEnvelope(data=report, meta=meta)


@router.post("/import", response_model=ResponseEnvelope[KnowledgePackSummary], status_code=201)
async def import_knowledge_pack(
    pack: UploadFile = File(description="Validated knowledge-pack ZIP"),
    service: AuditService = Depends(audit_service),
    meta: ResponseMeta = Depends(response_meta),
) -> ResponseEnvelope[KnowledgePackSummary]:
    try:
        filename = validate_upload_name(pack.filename or "unnamed")
    except ValueError as exc:
        await pack.close()
        raise ProblemError(
            status=422, title="Knowledge pack import failed", detail=str(exc)
        ) from exc
    if not filename.lower().endswith(".zip"):
        await pack.close()
        raise ProblemError(
            status=422, title="Knowledge pack import failed", detail="pack_file_must_be_zip"
        )
    content = await pack.read(service.limits.single_file_bytes + 1)
    await pack.close()
    if len(content) > service.limits.single_file_bytes:
        raise ProblemError(
            status=413,
            title="Knowledge pack import failed",
            detail="single_file_size_exceeded",
        )
    try:
        imported = service.pack_manager.import_archive(content)
    except ValueError as exc:
        raise ProblemError(
            status=422, title="Knowledge pack import failed", detail=str(exc)
        ) from exc
    return ResponseEnvelope(data=summary(imported, "valid"), meta=meta)


@router.post("/{pack_id}/activate", response_model=ResponseEnvelope[KnowledgePackSummary])
def activate_pack(
    pack_id: str,
    service: AuditService = Depends(audit_service),
    meta: ResponseMeta = Depends(response_meta),
) -> ResponseEnvelope[KnowledgePackSummary]:
    try:
        pack = service.pack_manager.set_active(pack_id, True)
    except ValueError as exc:
        raise ProblemError(status=404, title="Knowledge pack unavailable", detail=str(exc)) from exc
    return ResponseEnvelope(data=summary(pack, "valid"), meta=meta)


@router.post("/{pack_id}/deactivate", response_model=ResponseEnvelope[KnowledgePackSummary])
def deactivate_pack(
    pack_id: str,
    service: AuditService = Depends(audit_service),
    meta: ResponseMeta = Depends(response_meta),
) -> ResponseEnvelope[KnowledgePackSummary]:
    try:
        pack = service.pack_manager.set_active(pack_id, False)
    except ValueError as exc:
        raise ProblemError(status=404, title="Knowledge pack unavailable", detail=str(exc)) from exc
    return ResponseEnvelope(data=summary(pack, "valid"), meta=meta)


@router.delete("/{pack_id}", response_model=ResponseEnvelope[dict[str, bool]])
def remove_pack(
    pack_id: str,
    service: AuditService = Depends(audit_service),
    meta: ResponseMeta = Depends(response_meta),
) -> ResponseEnvelope[dict[str, bool]]:
    try:
        service.pack_manager.remove(pack_id)
    except ValueError as exc:
        raise ProblemError(
            status=422, title="Knowledge pack removal failed", detail=str(exc)
        ) from exc
    return ResponseEnvelope(data={"removed": True}, meta=meta)


@router.get("/{pack_id}/provenance", response_model=ResponseEnvelope[KnowledgePackManifest])
def pack_provenance(
    pack_id: str,
    service: AuditService = Depends(audit_service),
    meta: ResponseMeta = Depends(response_meta),
) -> ResponseEnvelope[KnowledgePackManifest]:
    pack = service.pack_manager.get(pack_id)
    if pack is None:
        raise ProblemError(status=404, title="Knowledge pack not found", detail=pack_id)
    return ResponseEnvelope(data=pack.manifest, meta=meta)


@router.get("/{pack_id}/validation-report")
def export_pack_validation_report(
    pack_id: str,
    service: AuditService = Depends(audit_service),
) -> Response:
    pack = service.pack_manager.get(pack_id)
    if pack is None:
        raise ProblemError(status=404, title="Knowledge pack not found", detail=pack_id)
    report = service.pack_loader.validate(pack.path)
    content = json.dumps(report.model_dump(mode="json"), indent=2).encode()
    return Response(
        content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{pack_id}-validation.json"'},
    )
