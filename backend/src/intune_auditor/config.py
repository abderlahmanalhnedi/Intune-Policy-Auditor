"""Environment-backed application configuration with safe local defaults."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from platformdirs import user_data_path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Tenant credentials are intentionally limited to public-client IDs."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="INTUNE_AUDITOR_",
        extra="ignore",
    )

    host: str = "127.0.0.1"
    port: int = Field(default=8765, ge=1, le=65535)
    log_level: str = "INFO"
    history_enabled: bool = False
    save_reports: bool = False
    retention_days: int = Field(default=30, ge=1, le=3650)
    tenant_id: str | None = None
    client_id: str | None = None
    data_dir_override: Path | None = None
    frontend_dist_override: Path | None = None

    @property
    def data_dir(self) -> Path:
        return self.data_dir_override or Path(
            user_data_path("IntunePolicyAuditor", appauthor=False)
        )

    @property
    def database_path(self) -> Path:
        return self.data_dir / "intune-policy-auditor.sqlite3"

    @property
    def token_cache_path(self) -> Path:
        return self.data_dir / "auth" / "msal-token-cache.bin"

    @property
    def frontend_dist(self) -> Path:
        if self.frontend_dist_override is not None:
            return self.frontend_dist_override
        return Path(__file__).resolve().parents[3] / "frontend" / "dist"


@lru_cache
def get_settings() -> Settings:
    return Settings()
