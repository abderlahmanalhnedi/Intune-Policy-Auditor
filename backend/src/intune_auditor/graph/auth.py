"""Backend-only MSAL device-code authentication and protected token-cache lifecycle."""

from __future__ import annotations

import os
from contextlib import suppress
from pathlib import Path
from threading import RLock
from typing import Any, cast
from urllib.parse import urlparse
from uuid import uuid4

import msal  # type: ignore[import-untyped]
from pydantic import BaseModel, Field, field_validator

from intune_auditor.graph.operations import READ_CONFIGURATION_SCOPE


class DeviceCodePrompt(BaseModel):
    flow_id: str
    user_code: str
    verification_uri: str
    message: str
    expires_in: int = Field(gt=0)
    interval: int = Field(gt=0)

    @field_validator("verification_uri")
    @classmethod
    def microsoft_https_uri(cls, value: str) -> str:
        parsed = urlparse(value)
        host = (parsed.hostname or "").lower()
        allowed = host in {"microsoft.com", "aka.ms"} or host.endswith(
            (".microsoft.com", ".microsoftonline.com")
        )
        if parsed.scheme != "https" or not allowed:
            raise ValueError("verification_uri must be an official Microsoft HTTPS URL")
        return value


class AuthenticationResult(BaseModel):
    authenticated: bool
    granted_scopes: list[str]
    account_name: str | None = None


class DeviceCodeAuthenticator:
    """The device-code secret and access tokens never cross the backend boundary."""

    def __init__(self, tenant_id: str, client_id: str, cache_path: Path) -> None:
        self.cache_path = cache_path
        self.cache = msal.SerializableTokenCache()
        if cache_path.is_file():
            self.cache.deserialize(cache_path.read_text(encoding="utf-8"))
        self.application = msal.PublicClientApplication(
            client_id,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
            token_cache=self.cache,
        )
        self.scopes = [f"https://graph.microsoft.com/{READ_CONFIGURATION_SCOPE}"]
        self._flows: dict[str, dict[str, Any]] = {}
        self._lock = RLock()
        self._granted_scopes: list[str] = []

    def begin(self) -> DeviceCodePrompt:
        flow = cast(dict[str, Any], self.application.initiate_device_flow(scopes=self.scopes))
        if "user_code" not in flow:
            raise ValueError(str(flow.get("error_description", "device_code_flow_failed")))
        flow_id = str(uuid4())
        with self._lock:
            self._flows[flow_id] = flow
        return DeviceCodePrompt(
            flow_id=flow_id,
            user_code=str(flow["user_code"]),
            verification_uri=str(flow.get("verification_uri", "https://microsoft.com/devicelogin")),
            message=str(flow.get("message", "Complete device-code authentication.")),
            expires_in=int(flow.get("expires_in", 900)),
            interval=max(int(flow.get("interval", 5)), 1),
        )

    def complete(self, flow_id: str) -> AuthenticationResult:
        with self._lock:
            flow = self._flows.pop(flow_id, None)
        if flow is None:
            raise ValueError("device_code_flow_not_found_or_already_consumed")
        result = cast(dict[str, Any], self.application.acquire_token_by_device_flow(flow=flow))
        if "access_token" not in result:
            raise ValueError(str(result.get("error_description", "authentication_failed")))
        scope = str(result.get("scope", ""))
        self._granted_scopes = sorted(item for item in scope.split() if item)
        self._persist_cache()
        account = result.get("id_token_claims")
        account_name = str(account.get("preferred_username")) if isinstance(account, dict) else None
        return AuthenticationResult(
            authenticated=True,
            granted_scopes=self._granted_scopes,
            account_name=account_name,
        )

    def access_token(self) -> str:
        accounts = self.application.get_accounts()
        if not accounts:
            raise ValueError("graph_authentication_required")
        result = cast(
            dict[str, Any] | None,
            self.application.acquire_token_silent(self.scopes, account=accounts[0]),
        )
        if not result or "access_token" not in result:
            raise ValueError("graph_authentication_required")
        self._persist_cache()
        return str(result["access_token"])

    def status(self) -> AuthenticationResult:
        accounts = self.application.get_accounts()
        name = str(accounts[0].get("username")) if accounts else None
        return AuthenticationResult(
            authenticated=bool(accounts),
            granted_scopes=self._granted_scopes,
            account_name=name,
        )

    def sign_out(self) -> None:
        with self._lock:
            self._flows.clear()
            for account in self.application.get_accounts():
                self.application.remove_account(account)
            self.cache = msal.SerializableTokenCache()
            self.application.token_cache = self.cache
            self._granted_scopes = []
        with suppress(FileNotFoundError):
            self.cache_path.unlink()

    def _persist_cache(self) -> None:
        if not self.cache.has_state_changed:
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(self.cache.serialize(), encoding="utf-8")
        with suppress(OSError):
            os.chmod(self.cache_path, 0o600)
