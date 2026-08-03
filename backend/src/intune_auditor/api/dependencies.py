"""FastAPI dependency helpers."""

from fastapi import Request

from intune_auditor.api.response_models import ResponseMeta


def response_meta(request: Request) -> ResponseMeta:
    return ResponseMeta(request_id=str(request.state.request_id))
