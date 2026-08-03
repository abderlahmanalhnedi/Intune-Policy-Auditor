"""Configurable defensive limits for local processing."""

from pydantic import BaseModel, Field


class ProcessingLimits(BaseModel):
    single_file_bytes: int = Field(default=25 * 1024 * 1024, ge=1024)
    total_upload_bytes: int = Field(default=100 * 1024 * 1024, ge=1024)
    zip_file_count: int = Field(default=500, ge=1)
    expanded_zip_bytes: int = Field(default=200 * 1024 * 1024, ge=1024)
    compression_ratio: float = Field(default=100.0, ge=1)
    nested_archive_depth: int = Field(default=0, ge=0, le=3)
    json_nesting_depth: int = Field(default=80, ge=5, le=500)
    maximum_policies: int = Field(default=500, ge=1)
    maximum_settings: int = Field(default=10_000, ge=1)
    maximum_string_length: int = Field(default=100_000, ge=100)
    maximum_report_bytes: int = Field(default=50 * 1024 * 1024, ge=1024)


DEFAULT_LIMITS = ProcessingLimits()
