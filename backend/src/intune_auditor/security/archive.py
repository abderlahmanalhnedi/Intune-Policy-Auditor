"""In-memory ZIP inspection with path, type, count, and expansion safeguards."""

from __future__ import annotations

import io
import stat
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import PurePosixPath

from intune_auditor.security.filenames import validate_upload_name
from intune_auditor.security.limits import ProcessingLimits

_EXECUTABLE_SUFFIXES = {
    ".app",
    ".bat",
    ".bin",
    ".cmd",
    ".com",
    ".dll",
    ".dmg",
    ".exe",
    ".jar",
    ".js",
    ".msi",
    ".ps1",
    ".scr",
    ".sh",
}
_ARCHIVE_SUFFIXES = {".zip", ".7z", ".rar", ".tar", ".gz", ".bz2", ".xz"}


@dataclass(frozen=True, slots=True)
class ArchiveMember:
    filename: str
    content: bytes


def read_safe_zip(content: bytes, limits: ProcessingLimits) -> list[ArchiveMember]:
    members: list[ArchiveMember] = []
    expanded_total = 0
    seen_names: set[str] = set()
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except (zipfile.BadZipFile, OSError) as exc:
        raise ValueError("malformed_zip") from exc

    with archive:
        infos = archive.infolist()
        if len(infos) > limits.zip_file_count:
            raise ValueError("zip_file_count_exceeded")
        for info in infos:
            if info.is_dir():
                continue
            normalized = info.filename.replace("\\", "/")
            member_path = PurePosixPath(normalized)
            if (
                member_path.is_absolute()
                or ".." in member_path.parts
                or (member_path.parts and member_path.parts[0].endswith(":"))
            ):
                raise ValueError("zip_path_traversal")
            canonical_name = unicodedata.normalize("NFC", str(member_path)).casefold()
            if canonical_name in seen_names:
                raise ValueError("duplicate_archive_member")
            seen_names.add(canonical_name)
            if info.flag_bits & 0x1:
                raise ValueError("encrypted_archive_member")
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise ValueError("zip_symbolic_link")
            if mode and mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
                raise ValueError("executable_archive_member")
            leaf = validate_upload_name(member_path.name)
            suffix = PurePosixPath(leaf).suffix.lower()
            if suffix in _EXECUTABLE_SUFFIXES:
                raise ValueError("executable_archive_member")
            if suffix in _ARCHIVE_SUFFIXES and limits.nested_archive_depth == 0:
                raise ValueError("nested_archive_not_allowed")
            if suffix != ".json":
                raise ValueError("unsupported_archive_member")
            expanded_total += info.file_size
            if expanded_total > limits.expanded_zip_bytes:
                raise ValueError("expanded_zip_size_exceeded")
            ratio = info.file_size / max(info.compress_size, 1)
            if ratio > limits.compression_ratio:
                raise ValueError("zip_compression_ratio_exceeded")
            try:
                data = archive.read(info)
            except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
                raise ValueError("malformed_zip_member") from exc
            if len(data) != info.file_size:
                raise ValueError("zip_member_size_mismatch")
            members.append(ArchiveMember(filename=normalized, content=data))
    if not members:
        raise ValueError("empty_zip")
    return members
