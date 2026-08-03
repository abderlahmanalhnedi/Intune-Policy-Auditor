"""Optional tenant service boundary; Offline Mode has no dependency on this object."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from intune_auditor.graph.auth import (
    AuthenticationResult,
    DeviceCodeAuthenticator,
    DeviceCodePrompt,
)
from intune_auditor.graph.client import AsyncGraphClient, GraphCollectionResult
from intune_auditor.graph.operations import GRAPH_OPERATIONS, READ_CONFIGURATION_SCOPE


class TenantStatus(BaseModel):
    configured: bool
    authenticated: bool
    requested_scopes: list[str]
    granted_scopes: list[str]
    account_name: str | None = None
    operations: dict[str, str]
    last_retrieval_at: datetime | None = None
    implementation_state: str = "safe_skeleton"
    limitations: list[str] = Field(default_factory=list)


class TenantGraphService:
    def __init__(self, tenant_id: str | None, client_id: str | None, cache_path: Path) -> None:
        self.configured = bool(tenant_id and client_id)
        self.authenticator = (
            DeviceCodeAuthenticator(tenant_id, client_id, cache_path)
            if tenant_id and client_id
            else None
        )
        self.client = (
            AsyncGraphClient(self.authenticator.access_token)
            if self.authenticator is not None
            else None
        )
        self.last_retrieval_at: datetime | None = None

    def status(self) -> TenantStatus:
        auth = (
            self.authenticator.status()
            if self.authenticator is not None
            else AuthenticationResult(authenticated=False, granted_scopes=[])
        )
        return TenantStatus(
            configured=self.configured,
            authenticated=auth.authenticated,
            requested_scopes=[READ_CONFIGURATION_SCOPE],
            granted_scopes=auth.granted_scopes,
            account_name=auth.account_name,
            operations={
                name: operation.api_version for name, operation in GRAPH_OPERATIONS.items()
            },
            last_retrieval_at=self.last_retrieval_at,
            limitations=[
                "Tenant responses are isolated from offline domain models until adapter validation.",
                "No live tenant was used during automated validation.",
            ],
        )

    def begin(self) -> DeviceCodePrompt:
        if self.authenticator is None:
            raise ValueError("tenant_mode_not_configured")
        return self.authenticator.begin()

    def complete(self, flow_id: str) -> AuthenticationResult:
        if self.authenticator is None:
            raise ValueError("tenant_mode_not_configured")
        return self.authenticator.complete(flow_id)

    async def retrieve(self, operation: str) -> GraphCollectionResult:
        if self.client is None:
            raise ValueError("tenant_mode_not_configured")
        result = await self.client.fetch_collection(operation)
        self.last_retrieval_at = result.retrieved_at
        return result

    def sign_out(self) -> None:
        if self.authenticator is not None:
            self.authenticator.sign_out()
