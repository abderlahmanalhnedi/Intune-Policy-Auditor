"""Validate accepted-deviation files without persisting uploaded content."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, Field

from intune_auditor.api.dependencies import response_meta
from intune_auditor.api.errors import ProblemError
from intune_auditor.api.response_models import ResponseEnvelope, ResponseMeta
from intune_auditor.deviations.service import parse_deviations
from intune_auditor.security.filenames import validate_upload_name
from intune_auditor.security.limits import DEFAULT_LIMITS

router = APIRouter(prefix="/deviations", tags=["Accepted deviations"])


class DeviationValidationResult(BaseModel):
    valid: bool
    deviation_count: int = Field(ge=0)
    deviation_ids: list[str]


@router.post("/validate", response_model=ResponseEnvelope[DeviationValidationResult])
async def validate_deviations(
    deviations: Annotated[UploadFile, File(description="Accepted-deviation JSON file")],
    meta: ResponseMeta = Depends(response_meta),
) -> ResponseEnvelope[DeviationValidationResult]:
    try:
        filename = validate_upload_name(deviations.filename or "unnamed")
        if not filename.lower().endswith(".json"):
            raise ValueError("deviation_file_must_be_json")
        content = await deviations.read(DEFAULT_LIMITS.single_file_bytes + 1)
        if len(content) > DEFAULT_LIMITS.single_file_bytes:
            raise ValueError("single_file_size_exceeded")
        items = parse_deviations(content)
    except ValueError as exc:
        raise ProblemError(status=422, title="Deviation file rejected", detail=str(exc)) from exc
    finally:
        await deviations.close()
    return ResponseEnvelope(
        data=DeviationValidationResult(
            valid=True,
            deviation_count=len(items),
            deviation_ids=[item.deviation_id for item in items],
        ),
        meta=meta,
    )
