from fastapi import APIRouter, Depends
from pydantic import BaseModel

from intune_auditor.api.dependencies import response_meta
from intune_auditor.api.response_models import ResponseEnvelope, ResponseMeta
from intune_auditor.version import (
    API_VERSION,
    APP_VERSION,
    AUDIT_SCHEMA_VERSION,
    KNOWLEDGE_PACK_SCHEMA_VERSION,
    REPORT_SCHEMA_VERSION,
)

router = APIRouter(prefix="/version", tags=["System"])


class VersionResponse(BaseModel):
    application: str
    api: str
    audit_schema: str
    knowledge_pack_schema: str
    report_schema: str


@router.get("", response_model=ResponseEnvelope[VersionResponse])
def version(meta: ResponseMeta = Depends(response_meta)) -> ResponseEnvelope[VersionResponse]:
    return ResponseEnvelope(
        data=VersionResponse(
            application=APP_VERSION,
            api=API_VERSION,
            audit_schema=AUDIT_SCHEMA_VERSION,
            knowledge_pack_schema=KNOWLEDGE_PACK_SCHEMA_VERSION,
            report_schema=REPORT_SCHEMA_VERSION,
        ),
        meta=meta,
    )
