"""Offline audit, result navigation, and report endpoints."""

from __future__ import annotations

import json
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from intune_auditor.api.dependencies import response_meta
from intune_auditor.api.errors import ProblemError
from intune_auditor.api.response_models import PaginatedResponse, ResponseEnvelope, ResponseMeta
from intune_auditor.application.audit_service import AuditService
from intune_auditor.domain.enums import (
    AlignmentStatus,
    ConflictConfidence,
    EvidenceConfidence,
    FindingSeverity,
)
from intune_auditor.domain.models import (
    AuditConfiguration,
    AuditContext,
    AuditPreview,
    AuditResult,
    ConflictResult,
    Finding,
    PolicyEvaluation,
)
from intune_auditor.organization.requirements import parse_requirements
from intune_auditor.reporting.service import ReportService
from intune_auditor.security.filenames import validate_upload_name
from intune_auditor.security.json_safety import strict_json_loads

router = APIRouter(prefix="/audits", tags=["Audits"])


def audit_service(request: Request) -> AuditService:
    return request.app.state.audit_service  # type: ignore[no-any-return]


def require_audit(audit_id: str, service: AuditService) -> AuditResult:
    result = service.get(audit_id)
    if result is None:
        raise ProblemError(
            status=404,
            title="Audit not found",
            detail="The requested audit is not available in this session.",
        )
    return result


@contextmanager
def deviation_path(upload: UploadFile | None, content: bytes | None) -> Iterator[Path | None]:
    if upload is None or content is None:
        yield None
        return
    with tempfile.TemporaryDirectory(prefix="ipa-deviation-") as directory:
        path = Path(directory) / "deviations.json"
        path.write_bytes(content)
        yield path


class DashboardSummary(BaseModel):
    decision: str
    reason: dict[str, str]
    next_action: dict[str, str]
    is_synthetic: bool
    policy_count: int = Field(ge=0)
    setting_count: int = Field(ge=0)
    evaluable_count: int = Field(ge=0)
    not_evaluable_count: int = Field(ge=0)
    confirmed_issues: int = Field(ge=0)
    confirmed_conflicts: int = Field(ge=0)
    alignment_counts: dict[str, int]
    severity_counts: dict[str, int]
    exact_evidence_coverage: float | None
    assignment_analysis_coverage: float | None
    runtime_success_rate: float | None = Field(default=None, ge=0, le=1)
    runtime_success_count: int | None = Field(default=None, ge=0)
    runtime_targeted_count: int | None = Field(default=None, ge=0)
    evidence_quality: EvidenceConfidence
    policy_health_counts: dict[str, int]
    not_evaluable_reasons: dict[str, int]
    top_actions: list[Finding]


@router.post("/demo", response_model=ResponseEnvelope[AuditResult], status_code=201)
def create_demo_audit(
    language: Annotated[str, Query(pattern="^(de|en)$")] = "de",
    service: AuditService = Depends(audit_service),
    meta: ResponseMeta = Depends(response_meta),
) -> ResponseEnvelope[AuditResult]:
    return ResponseEnvelope(data=service.demonstration_audit(language), meta=meta)


@router.post("/preview", response_model=ResponseEnvelope[AuditPreview])
async def preview_offline_audit(
    files: Annotated[
        list[UploadFile], File(description="Intune JSON exports or safe ZIP archives")
    ],
    service: AuditService = Depends(audit_service),
    meta: ResponseMeta = Depends(response_meta),
) -> ResponseEnvelope[AuditPreview]:
    try:
        uploads = [
            (
                upload.filename or "unnamed",
                await upload.read(service.limits.single_file_bytes + 1),
            )
            for upload in files
        ]
        preview = service.preview_uploads(uploads)
    except ValueError as exc:
        raise ProblemError(status=422, title="Audit preview rejected", detail=str(exc)) from exc
    finally:
        for upload in files:
            await upload.close()
    return ResponseEnvelope(data=preview, meta=meta)


@router.post("", response_model=ResponseEnvelope[AuditResult], status_code=201)
async def create_offline_audit(
    files: Annotated[
        list[UploadFile], File(description="Intune JSON exports or safe ZIP archives")
    ],
    knowledge_pack_ids: Annotated[str, Form()] = '["synthetic.test-baseline"]',
    language: Annotated[str, Form(pattern="^(de|en)$")] = "de",
    deviations: Annotated[UploadFile | None, File()] = None,
    organization_requirements: Annotated[UploadFile | None, File()] = None,
    audit_context: Annotated[str, Form()] = "{}",
    service: AuditService = Depends(audit_service),
    meta: ResponseMeta = Depends(response_meta),
) -> ResponseEnvelope[AuditResult]:
    uploads: list[tuple[str, bytes]] = []
    try:
        for upload in files:
            content = await upload.read(service.limits.single_file_bytes + 1)
            uploads.append((upload.filename or "unnamed", content))
        deviation_content = (
            await deviations.read(service.limits.single_file_bytes + 1) if deviations else None
        )
        requirement_content = (
            await organization_requirements.read(service.limits.single_file_bytes + 1)
            if organization_requirements
            else None
        )
        for context_upload, context_content in (
            (deviations, deviation_content),
            (organization_requirements, requirement_content),
        ):
            if context_upload is None or context_content is None:
                continue
            filename = validate_upload_name(context_upload.filename or "unnamed")
            if Path(filename).suffix.lower() != ".json":
                raise ValueError("context_file_must_be_json")
            if len(context_content) > service.limits.single_file_bytes:
                raise ValueError("single_file_size_exceeded")
        parsed_pack_ids = strict_json_loads(knowledge_pack_ids)
        if not isinstance(parsed_pack_ids, list) or not all(
            isinstance(item, str) for item in parsed_pack_ids
        ):
            raise ValueError("invalid_pack_selection")
        parsed_context = strict_json_loads(audit_context)
        if not isinstance(parsed_context, dict):
            raise ValueError("invalid_audit_context")
        configuration = AuditConfiguration(
            language=language,
            active_pack_ids=parsed_pack_ids,
            context=AuditContext.model_validate(parsed_context),
            organization_requirements=parse_requirements(requirement_content)
            if requirement_content is not None
            else [],
        )
        with deviation_path(deviations, deviation_content) as path:
            result = service.audit_uploads(uploads, configuration, path)
    except (ValueError, json.JSONDecodeError) as exc:
        raise ProblemError(status=422, title="Audit input rejected", detail=str(exc)) from exc
    finally:
        for upload in files:
            await upload.close()
        if deviations:
            await deviations.close()
        if organization_requirements:
            await organization_requirements.close()
    return ResponseEnvelope(data=result, meta=meta)


@router.get("/{audit_id}", response_model=ResponseEnvelope[AuditResult])
def get_audit(
    audit_id: str,
    service: AuditService = Depends(audit_service),
    meta: ResponseMeta = Depends(response_meta),
) -> ResponseEnvelope[AuditResult]:
    return ResponseEnvelope(data=require_audit(audit_id, service), meta=meta)


@router.get("/{audit_id}/dashboard", response_model=ResponseEnvelope[DashboardSummary])
def dashboard(
    audit_id: str,
    service: AuditService = Depends(audit_service),
    meta: ResponseMeta = Depends(response_meta),
) -> ResponseEnvelope[DashboardSummary]:
    audit = require_audit(audit_id, service)
    alignment_counts = {status.value: 0 for status in AlignmentStatus}
    for policy in audit.policies:
        for evaluation in policy.settings:
            alignment_counts[evaluation.effective_alignment_status.value] += 1
    severity_counts = {severity.value: 0 for severity in FindingSeverity}
    for finding in audit.findings:
        severity_counts[finding.severity.value] += 1
    severity_order = {
        FindingSeverity.CRITICAL: 0,
        FindingSeverity.HIGH: 1,
        FindingSeverity.MEDIUM: 2,
        FindingSeverity.LOW: 3,
        FindingSeverity.INFORMATION: 4,
        FindingSeverity.NONE: 5,
    }
    top_actions = sorted(audit.findings, key=lambda item: severity_order[item.severity])[:5]
    runtime_items = [
        policy.runtime_evidence for policy in audit.policies if policy.runtime_evidence is not None
    ]
    runtime_success = sum(item.success_count or 0 for item in runtime_items)
    runtime_targeted = sum(item.targeted_count or 0 for item in runtime_items)
    quality_inputs = [
        value
        for value in (
            audit.coverage.exact_setting_coverage,
            audit.coverage.exact_value_semantic_coverage,
            audit.coverage.documentation_coverage,
        )
        if value is not None
    ]
    quality_floor = min(quality_inputs) if len(quality_inputs) == 3 else None
    evidence_quality = (
        EvidenceConfidence.EXACT
        if quality_floor == 1
        else EvidenceConfidence.STRONG
        if quality_floor is not None and quality_floor >= 0.75
        else EvidenceConfidence.PARTIAL
        if quality_floor is not None and quality_floor > 0
        else EvidenceConfidence.UNKNOWN
    )
    confirmed_conflict_policies = {
        policy_id
        for conflict in audit.conflicts
        if conflict.confidence is ConflictConfidence.CONFIRMED
        for policy_id in (conflict.policy_a_id, conflict.policy_b_id)
    }
    conflict_policies = {
        policy_id
        for conflict in audit.conflicts
        for policy_id in (conflict.policy_a_id, conflict.policy_b_id)
    }
    policy_health_counts = {
        "aligned": 0,
        "review": 0,
        "action_required": 0,
        "insufficient_evidence": 0,
    }
    not_evaluable_reasons: dict[str, int] = {}
    for policy in audit.policies:
        policy_id = policy.policy.policy_id
        if policy_id in confirmed_conflict_policies or any(
            finding.severity in {FindingSeverity.CRITICAL, FindingSeverity.HIGH}
            for finding in policy.findings
        ):
            policy_health_counts["action_required"] += 1
        elif any(
            setting.effective_alignment_status is AlignmentStatus.NOT_EVALUABLE
            for setting in policy.settings
        ):
            policy_health_counts["insufficient_evidence"] += 1
        elif policy.findings or policy.assignment_risks or policy_id in conflict_policies:
            policy_health_counts["review"] += 1
        else:
            policy_health_counts["aligned"] += 1
        for setting in policy.settings:
            for reason in setting.not_evaluable_reasons:
                not_evaluable_reasons[reason] = not_evaluable_reasons.get(reason, 0) + 1
    summary = DashboardSummary(
        decision=audit.decision.status.value,
        reason=audit.decision.reason,
        next_action=audit.decision.next_action,
        is_synthetic=audit.is_synthetic,
        policy_count=len(audit.policies),
        setting_count=sum(len(policy.settings) for policy in audit.policies),
        evaluable_count=audit.coverage.evaluable_settings,
        not_evaluable_count=audit.coverage.not_evaluable_settings,
        confirmed_issues=sum(
            finding.severity in {FindingSeverity.CRITICAL, FindingSeverity.HIGH}
            for finding in audit.findings
        ),
        confirmed_conflicts=sum(
            item.confidence is ConflictConfidence.CONFIRMED for item in audit.conflicts
        ),
        alignment_counts=alignment_counts,
        severity_counts=severity_counts,
        exact_evidence_coverage=audit.coverage.exact_setting_coverage,
        assignment_analysis_coverage=audit.coverage.assignment_analysis_coverage,
        runtime_success_rate=runtime_success / runtime_targeted if runtime_targeted else None,
        runtime_success_count=runtime_success if runtime_items else None,
        runtime_targeted_count=runtime_targeted if runtime_items else None,
        evidence_quality=evidence_quality,
        policy_health_counts=policy_health_counts,
        not_evaluable_reasons=not_evaluable_reasons,
        top_actions=top_actions,
    )
    return ResponseEnvelope(data=summary, meta=meta)


@router.get(
    "/{audit_id}/policies", response_model=ResponseEnvelope[PaginatedResponse[PolicyEvaluation]]
)
def policies(
    audit_id: str,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    search: str | None = None,
    sort_by: Literal["name", "platform", "kind"] | None = None,
    sort_order: Literal["asc", "desc"] = "asc",
    service: AuditService = Depends(audit_service),
    meta: ResponseMeta = Depends(response_meta),
) -> ResponseEnvelope[PaginatedResponse[PolicyEvaluation]]:
    audit = require_audit(audit_id, service)
    items = audit.policies
    if search:
        needle = search.casefold()
        items = [item for item in items if needle in item.policy.name.casefold()]
    if sort_by:
        policy_sorters = {
            "name": lambda item: item.policy.name.casefold(),
            "platform": lambda item: item.policy.platform.value,
            "kind": lambda item: item.policy.kind.value,
        }
        items = sorted(items, key=policy_sorters[sort_by], reverse=sort_order == "desc")
    start = (page - 1) * page_size
    return ResponseEnvelope(
        data=PaginatedResponse(
            items=items[start : start + page_size], total=len(items), page=page, page_size=page_size
        ),
        meta=meta,
    )


@router.get("/{audit_id}/policies/{policy_id}", response_model=ResponseEnvelope[PolicyEvaluation])
def policy_detail(
    audit_id: str,
    policy_id: str,
    service: AuditService = Depends(audit_service),
    meta: ResponseMeta = Depends(response_meta),
) -> ResponseEnvelope[PolicyEvaluation]:
    audit = require_audit(audit_id, service)
    item = next((policy for policy in audit.policies if policy.policy.policy_id == policy_id), None)
    if item is None:
        raise ProblemError(
            status=404, title="Policy not found", detail="The policy is not part of this audit."
        )
    return ResponseEnvelope(data=item, meta=meta)


@router.get("/{audit_id}/findings", response_model=ResponseEnvelope[PaginatedResponse[Finding]])
def findings(
    audit_id: str,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    severity: FindingSeverity | None = None,
    alignment: AlignmentStatus | None = None,
    search: str | None = None,
    sort_by: Literal["severity", "policy", "alignment", "type"] | None = None,
    sort_order: Literal["asc", "desc"] = "asc",
    service: AuditService = Depends(audit_service),
    meta: ResponseMeta = Depends(response_meta),
) -> ResponseEnvelope[PaginatedResponse[Finding]]:
    audit = require_audit(audit_id, service)
    items = [
        item
        for item in audit.findings
        if (severity is None or item.severity is severity)
        and (alignment is None or item.alignment is alignment)
    ]
    if search:
        needle = search.casefold()
        items = [
            item
            for item in items
            if needle in item.policy_name.casefold()
            or any(needle in label.casefold() for label in item.setting_name.values())
        ]
    if sort_by:
        finding_sorters = {
            "severity": lambda item: item.severity.value,
            "policy": lambda item: item.policy_name.casefold(),
            "alignment": lambda item: item.alignment.value,
            "type": lambda item: item.finding_type.value,
        }
        items = sorted(items, key=finding_sorters[sort_by], reverse=sort_order == "desc")
    start = (page - 1) * page_size
    return ResponseEnvelope(
        data=PaginatedResponse(
            items=items[start : start + page_size], total=len(items), page=page, page_size=page_size
        ),
        meta=meta,
    )


@router.get("/{audit_id}/findings/{finding_id}", response_model=ResponseEnvelope[Finding])
def finding_detail(
    audit_id: str,
    finding_id: str,
    service: AuditService = Depends(audit_service),
    meta: ResponseMeta = Depends(response_meta),
) -> ResponseEnvelope[Finding]:
    audit = require_audit(audit_id, service)
    item = next((finding for finding in audit.findings if finding.finding_id == finding_id), None)
    if item is None:
        raise ProblemError(
            status=404, title="Finding not found", detail="The finding is not part of this audit."
        )
    return ResponseEnvelope(data=item, meta=meta)


@router.get(
    "/{audit_id}/conflicts", response_model=ResponseEnvelope[PaginatedResponse[ConflictResult]]
)
def conflicts(
    audit_id: str,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    confidence: ConflictConfidence | None = None,
    sort_by: Literal["confidence", "classification", "setting"] | None = None,
    sort_order: Literal["asc", "desc"] = "asc",
    service: AuditService = Depends(audit_service),
    meta: ResponseMeta = Depends(response_meta),
) -> ResponseEnvelope[PaginatedResponse[ConflictResult]]:
    audit = require_audit(audit_id, service)
    items = [
        item for item in audit.conflicts if confidence is None or item.confidence is confidence
    ]
    if sort_by:
        conflict_sorters = {
            "confidence": lambda item: item.confidence.value,
            "classification": lambda item: item.classification,
            "setting": lambda item: item.canonical_setting_id,
        }
        items = sorted(items, key=conflict_sorters[sort_by], reverse=sort_order == "desc")
    start = (page - 1) * page_size
    return ResponseEnvelope(
        data=PaginatedResponse(
            items=items[start : start + page_size], total=len(items), page=page, page_size=page_size
        ),
        meta=meta,
    )


@router.get("/{audit_id}/reports")
def report_catalog(
    audit_id: str,
    service: AuditService = Depends(audit_service),
    meta: ResponseMeta = Depends(response_meta),
) -> ResponseEnvelope[dict[str, list[str]]]:
    require_audit(audit_id, service)
    return ResponseEnvelope(
        data={
            "formats": [
                "html",
                "technical-html",
                "markdown",
                "json",
                "findings-csv",
                "conflicts-csv",
                "not-evaluable-csv",
                "provenance-json",
                "pdf",
            ]
        },
        meta=meta,
    )


@router.get("/{audit_id}/reports/{report_format}")
def download_report(
    audit_id: str,
    report_format: str,
    language: Annotated[str, Query(pattern="^(de|en)$")] = "en",
    service: AuditService = Depends(audit_service),
) -> Response:
    audit = require_audit(audit_id, service)
    try:
        report = ReportService(service.limits).render(audit, report_format, language)
    except ValueError as exc:
        raise ProblemError(status=422, title="Report unavailable", detail=str(exc)) from exc
    service.save_report_copy(report.filename, report.content)
    return Response(
        content=report.content,
        media_type=report.media_type,
        headers={"Content-Disposition": f'attachment; filename="{report.filename}"'},
    )
