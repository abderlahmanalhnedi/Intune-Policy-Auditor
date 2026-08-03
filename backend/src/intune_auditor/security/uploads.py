"""Validation of raw uploaded JSON and ZIP bytes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath

from intune_auditor.security.archive import read_safe_zip
from intune_auditor.security.filenames import validate_upload_name
from intune_auditor.security.limits import ProcessingLimits


@dataclass(frozen=True, slots=True)
class ValidatedUpload:
    filename: str
    content: bytes
    archive_member: str | None = None


def validate_uploads(
    uploads: list[tuple[str, bytes]],
    limits: ProcessingLimits,
) -> list[ValidatedUpload]:
    if not uploads:
        raise ValueError("no_files")
    if len(uploads) > limits.zip_file_count:
        raise ValueError("file_count_exceeded")
    total = sum(len(content) for _, content in uploads)
    if total > limits.total_upload_bytes:
        raise ValueError("total_upload_size_exceeded")

    validated: list[ValidatedUpload] = []
    for raw_name, content in uploads:
        filename = validate_upload_name(raw_name)
        if len(content) > limits.single_file_bytes:
            raise ValueError("single_file_size_exceeded")
        if not content:
            raise ValueError("empty_file")
        suffix = PurePath(filename).suffix.lower()
        if suffix == ".json":
            validated.append(ValidatedUpload(filename=filename, content=content))
        elif suffix == ".zip":
            for member in read_safe_zip(content, limits):
                validated.append(
                    ValidatedUpload(
                        filename=filename,
                        archive_member=member.filename,
                        content=member.content,
                    )
                )
        else:
            raise ValueError("unsupported_file_type")
    return validated
