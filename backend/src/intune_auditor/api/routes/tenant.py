"""Backend-only device-code and allowlisted Graph retrieval endpoints."""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from intune_auditor.api.dependencies import response_meta
from intune_auditor.api.errors import ProblemError
from intune_auditor.api.response_models import ResponseEnvelope, ResponseMeta
from intune_auditor.graph.auth import AuthenticationResult, DeviceCodePrompt
from intune_auditor.graph.client import GraphCollectionResult, GraphRequestError
from intune_auditor.graph.service import TenantGraphService, TenantStatus

router = APIRouter(prefix="/tenant", tags=["Tenant Mode"])


class CompleteDeviceCode(BaseModel):
    flow_id: str


class SignOutResult(BaseModel):
    signed_out: bool
    token_cache_deleted: bool


def tenant_service(request: Request) -> TenantGraphService:
    return request.app.state.tenant_service  # type: ignore[no-any-return]


@router.get("/status", response_model=ResponseEnvelope[TenantStatus])
def status(
    service: TenantGraphService = Depends(tenant_service),
    meta: ResponseMeta = Depends(response_meta),
) -> ResponseEnvelope[TenantStatus]:
    return ResponseEnvelope(data=service.status(), meta=meta)


@router.post("/connect", response_model=ResponseEnvelope[DeviceCodePrompt])
@router.post("/device-code", response_model=ResponseEnvelope[DeviceCodePrompt])
def begin_device_code(
    service: TenantGraphService = Depends(tenant_service),
    meta: ResponseMeta = Depends(response_meta),
) -> ResponseEnvelope[DeviceCodePrompt]:
    try:
        prompt = service.begin()
    except ValueError as exc:
        raise ProblemError(
            status=409, title="Tenant connection unavailable", detail=str(exc)
        ) from exc
    return ResponseEnvelope(data=prompt, meta=meta)


@router.post("/device-code/complete", response_model=ResponseEnvelope[AuthenticationResult])
def complete_device_code(
    body: CompleteDeviceCode,
    service: TenantGraphService = Depends(tenant_service),
    meta: ResponseMeta = Depends(response_meta),
) -> ResponseEnvelope[AuthenticationResult]:
    try:
        result = service.complete(body.flow_id)
    except ValueError as exc:
        raise ProblemError(
            status=409, title="Tenant authentication failed", detail=str(exc)
        ) from exc
    return ResponseEnvelope(data=result, meta=meta)


@router.get("/retrieve/{operation}", response_model=ResponseEnvelope[GraphCollectionResult])
async def retrieve(
    operation: str,
    service: TenantGraphService = Depends(tenant_service),
    meta: ResponseMeta = Depends(response_meta),
) -> ResponseEnvelope[GraphCollectionResult]:
    try:
        result = await service.retrieve(operation)
    except (ValueError, GraphRequestError) as exc:
        raise ProblemError(status=502, title="Graph retrieval failed", detail=str(exc)) from exc
    return ResponseEnvelope(data=result, meta=meta)


@router.post("/signout", response_model=ResponseEnvelope[SignOutResult])
@router.post("/sign-out", response_model=ResponseEnvelope[SignOutResult], include_in_schema=False)
def sign_out(
    service: TenantGraphService = Depends(tenant_service),
    meta: ResponseMeta = Depends(response_meta),
) -> ResponseEnvelope[SignOutResult]:
    service.sign_out()
    return ResponseEnvelope(
        data=SignOutResult(signed_out=True, token_cache_deleted=True), meta=meta
    )
