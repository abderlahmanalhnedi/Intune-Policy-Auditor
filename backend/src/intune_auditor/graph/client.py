"""Bounded Graph collection client with retries, pagination, caching, and partial failures."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from pydantic import BaseModel, Field

from intune_auditor.domain.models import JsonValue
from intune_auditor.graph.operations import GraphOperation, require_read_operation

TokenProvider = Callable[[], str]
Sleep = Callable[[float], Awaitable[None]]


class GraphFailure(BaseModel):
    operation: str
    page: int = Field(ge=1)
    status_code: int | None = None
    reason: str
    correlation_id: str


class GraphCollectionResult(BaseModel):
    operation: str
    api_version: str
    retrieved_at: datetime
    items: list[dict[str, JsonValue]]
    failures: list[GraphFailure] = Field(default_factory=list)
    partial: bool = False
    correlation_ids: list[str]
    from_cache: bool = False


class GraphRequestError(RuntimeError):
    def __init__(self, reason: str, status_code: int | None, correlation_id: str) -> None:
        super().__init__(reason)
        self.reason = reason
        self.status_code = status_code
        self.correlation_id = correlation_id


class AsyncGraphClient:
    def __init__(
        self,
        token_provider: TokenProvider,
        *,
        timeout_seconds: float = 20,
        max_retries: int = 3,
        maximum_pages: int = 100,
        cache_ttl_seconds: int = 300,
        sleep: Sleep = asyncio.sleep,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.token_provider = token_provider
        self.timeout = httpx.Timeout(timeout_seconds)
        self.max_retries = max_retries
        self.maximum_pages = maximum_pages
        self.cache_ttl_seconds = cache_ttl_seconds
        self.sleep = sleep
        self.transport = transport
        self._cache: dict[str, tuple[float, GraphCollectionResult]] = {}

    async def fetch_collection(self, operation_name: str) -> GraphCollectionResult:
        operation = require_read_operation(operation_name)
        cached = self._cache.get(operation_name)
        now = time.monotonic()
        if cached and now - cached[0] <= self.cache_ttl_seconds:
            return cached[1].model_copy(update={"from_cache": True})

        token = self.token_provider()
        if not token:
            raise ValueError("graph_authentication_required")
        url = f"https://graph.microsoft.com{operation.path}"
        items: list[dict[str, JsonValue]] = []
        failures: list[GraphFailure] = []
        correlation_ids: list[str] = []
        visited_urls: set[str] = set()
        page = 1
        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            while url:
                if url in visited_urls:
                    failures.append(
                        GraphFailure(
                            operation=operation.name,
                            page=page,
                            reason="pagination_cycle_detected",
                            correlation_id=correlation_ids[-1] if correlation_ids else "none",
                        )
                    )
                    break
                visited_urls.add(url)
                if page > self.maximum_pages:
                    failures.append(
                        GraphFailure(
                            operation=operation.name,
                            page=page,
                            reason="maximum_page_count_exceeded",
                            correlation_id=correlation_ids[-1] if correlation_ids else "none",
                        )
                    )
                    break
                try:
                    payload, correlation_id = await self._request_page(
                        client, operation, url, token
                    )
                except GraphRequestError as exc:
                    if not items:
                        raise
                    failures.append(
                        GraphFailure(
                            operation=operation.name,
                            page=page,
                            status_code=exc.status_code,
                            reason=exc.reason,
                            correlation_id=exc.correlation_id,
                        )
                    )
                    break
                correlation_ids.append(correlation_id)
                values = payload.get("value")
                if not isinstance(values, list):
                    raise GraphRequestError("invalid_collection_shape", None, correlation_id)
                for value in values:
                    if isinstance(value, dict):
                        items.append({str(key): item for key, item in value.items()})
                next_link = payload.get("@odata.nextLink")
                if next_link is None:
                    url = ""
                elif isinstance(next_link, str) and self._safe_next_link(next_link):
                    url = next_link
                else:
                    failures.append(
                        GraphFailure(
                            operation=operation.name,
                            page=page,
                            reason="unsafe_or_invalid_next_link",
                            correlation_id=correlation_id,
                        )
                    )
                    break
                page += 1

        result = GraphCollectionResult(
            operation=operation.name,
            api_version=operation.api_version,
            retrieved_at=datetime.now(UTC),
            items=items,
            failures=failures,
            partial=bool(failures),
            correlation_ids=correlation_ids,
        )
        self._cache[operation_name] = (now, result)
        return result

    async def _request_page(
        self,
        client: httpx.AsyncClient,
        operation: GraphOperation,
        url: str,
        token: str,
    ) -> tuple[dict[str, Any], str]:
        correlation_id = str(uuid4())
        for attempt in range(self.max_retries + 1):
            try:
                response = await client.request(
                    operation.method,
                    url,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json",
                        "client-request-id": correlation_id,
                        "return-client-request-id": "true",
                    },
                )
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt >= self.max_retries:
                    raise GraphRequestError(
                        "graph_network_or_timeout_error", None, correlation_id
                    ) from exc
                await self.sleep(min(2**attempt, 30))
                continue
            if response.status_code < 400:
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise GraphRequestError(
                        "invalid_graph_json", response.status_code, correlation_id
                    ) from exc
                if not isinstance(payload, dict):
                    raise GraphRequestError(
                        "invalid_graph_json", response.status_code, correlation_id
                    )
                return payload, correlation_id
            if response.status_code in {429, 503, 504} and attempt < self.max_retries:
                retry_after = response.headers.get("Retry-After")
                try:
                    delay = float(retry_after) if retry_after is not None else float(2**attempt)
                except ValueError:
                    delay = float(2**attempt)
                await self.sleep(min(max(delay, 0), 30))
                continue
            raise GraphRequestError(
                f"graph_http_{response.status_code}", response.status_code, correlation_id
            )
        raise GraphRequestError("graph_retry_exhausted", None, correlation_id)

    @staticmethod
    def _safe_next_link(url: str) -> bool:
        parsed = urlparse(url)
        return (
            parsed.scheme == "https"
            and parsed.hostname == "graph.microsoft.com"
            and (parsed.path.startswith("/v1.0/") or parsed.path.startswith("/beta/"))
        )
