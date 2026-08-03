from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from intune_auditor.api.dependencies import response_meta
from intune_auditor.api.response_models import ResponseEnvelope, ResponseMeta
from intune_auditor.version import APP_VERSION

router = APIRouter(prefix="/health", tags=["System"])


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
    offline_mode_available: bool


@router.get("", response_model=ResponseEnvelope[HealthResponse])
def health(meta: ResponseMeta = Depends(response_meta)) -> ResponseEnvelope[HealthResponse]:
    return ResponseEnvelope(
        data=HealthResponse(
            status="ok",
            version=APP_VERSION,
            timestamp=datetime.now(UTC),
            offline_mode_available=True,
        ),
        meta=meta,
    )
