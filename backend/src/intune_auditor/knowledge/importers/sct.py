"""Conservative importer for user-supplied SCT PolicyRules XML content.

Raw PolicyRules records do not contain exact Intune canonical identifiers. They are
therefore preserved for review and never promoted into recommendations.
"""

from __future__ import annotations

import hashlib
import json
import stat
import unicodedata
import zipfile
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

from defusedxml import ElementTree
from pydantic import BaseModel, Field

from intune_auditor.domain.enums import EvidenceType, KnowledgePackStatus, Platform
from intune_auditor.domain.models import KnowledgePackManifest, KnowledgeProvenance
from intune_auditor.knowledge.loader import KnowledgePackLoader, official_reference_allowed
from intune_auditor.security.limits import ProcessingLimits
from intune_auditor.version import APP_VERSION, KNOWLEDGE_PACK_SCHEMA_VERSION

_SUPPORTED_SUFFIXES = {".xml"}
_REJECTED_SUFFIXES = {
    ".app",
    ".bat",
    ".cmd",
    ".dll",
    ".exe",
    ".js",
    ".msi",
    ".ps1",
    ".sh",
    ".zip",
}


@dataclass(frozen=True, slots=True)
class SourceRecord:
    filename: str
    content: bytes


class ImportDiagnostic(BaseModel):
    source_file: str
    code: str
    severity: str
    reason: str
    record_count: int = Field(ge=0)


class SctImportResult(BaseModel):
    output_path: Path
    manifest: KnowledgePackManifest
    diagnostics: list[ImportDiagnostic]
    pending_review_count: int = Field(ge=0)

    model_config = {"arbitrary_types_allowed": True}


class SecurityComplianceToolkitImporter:
    def __init__(self, limits: ProcessingLimits) -> None:
        self.limits = limits

    def import_content(
        self,
        input_path: Path,
        output_path: Path,
        product: str,
        version: str,
        source_reference: str,
    ) -> SctImportResult:
        records, unsupported_files = self._read_input(input_path)
        if not records:
            raise ValueError("no_supported_sct_files")
        if output_path.exists() and (not output_path.is_dir() or any(output_path.iterdir())):
            raise ValueError("output_directory_not_empty")
        pending: list[dict[str, str]] = []
        diagnostics: list[ImportDiagnostic] = [
            ImportDiagnostic(
                source_file=filename,
                code="unsupported_file",
                severity="warning",
                reason="The file format is not supported and was not parsed.",
                record_count=0,
            )
            for filename in unsupported_files
        ]
        input_hashes: list[str] = []
        for record in records:
            digest = hashlib.sha256(record.content).hexdigest()
            input_hashes.append(digest)
            extracted = self._parse_policy_rules(record)
            if len(pending) + len(extracted) > self.limits.maximum_settings:
                raise ValueError("maximum_sct_records_exceeded")
            pending.extend(extracted)
            diagnostics.append(
                ImportDiagnostic(
                    source_file=record.filename,
                    code="ambiguous_intune_mapping",
                    severity="warning",
                    reason=(
                        "PolicyRules metadata was preserved for manual review; no exact Intune "
                        "canonical identifier was inferred."
                    ),
                    record_count=len(extracted),
                )
            )
        settings_bytes = b"[]\n"
        data_hash = hashlib.sha256(settings_bytes).hexdigest()
        schema_hash = hashlib.sha256(
            KnowledgePackLoader.bundled_setting_schema().read_bytes()
        ).hexdigest()
        parsed_source = urlparse(source_reference)
        source_domain = (parsed_source.hostname or "").lower()
        if not official_reference_allowed(source_reference):
            raise ValueError("source_reference_must_be_official_url")
        safe_product = "".join(char.lower() if char.isalnum() else "-" for char in product).strip(
            "-"
        )
        safe_version = "".join(char.lower() if char.isalnum() else "-" for char in version).strip(
            "-"
        )
        pack_id = f"microsoft.sct.{safe_product}.{safe_version}"
        manifest = KnowledgePackManifest(
            schema_version=KNOWLEDGE_PACK_SCHEMA_VERSION,
            pack_id=pack_id,
            vendor="Microsoft",
            product=product,
            baseline_name=f"{product} Security Compliance Toolkit import",
            baseline_version=version,
            platform=Platform.WINDOWS,
            source_type=EvidenceType.MICROSOFT_SECURITY_COMPLIANCE_TOOLKIT,
            source_title=f"User-supplied SCT content for {product}",
            source_domain=source_domain,
            source_reference=source_reference,
            published_at=None,
            verified_at=date.today(),
            imported_at=datetime.now(UTC),
            data_sha256=data_hash,
            schema_sha256=schema_hash,
            application_version=APP_VERSION,
            status=KnowledgePackStatus.PENDING_REVIEW,
            setting_count=0,
            exact_value_count=0,
            notes=[
                "No raw SCT record was promoted to an Intune recommendation.",
                f"{len(pending)} records require explicit canonical mapping review.",
            ],
            settings_file="settings.json",
            provenance=KnowledgeProvenance(
                input_files=[record.filename for record in records],
                input_sha256=input_hashes,
                importer_version=APP_VERSION,
                notes=["User-supplied content; Microsoft archive is not redistributed."],
            ),
        )
        output_path.mkdir(parents=True, exist_ok=True)
        (output_path / "settings.json").write_bytes(settings_bytes)
        (output_path / "manifest.json").write_text(
            manifest.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )
        (output_path / "pending-review.json").write_text(
            json.dumps(pending, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (output_path / "import-diagnostics.json").write_text(
            json.dumps(
                [item.model_dump(mode="json") for item in diagnostics],
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return SctImportResult(
            output_path=output_path,
            manifest=manifest,
            diagnostics=diagnostics,
            pending_review_count=len(pending),
        )

    def _read_input(self, path: Path) -> tuple[list[SourceRecord], list[str]]:
        if path.is_symlink():
            raise ValueError("sct_symbolic_link")
        if path.is_dir():
            all_files = [item for item in sorted(path.rglob("*")) if item.is_file()]
            if any(item.is_symlink() for item in all_files):
                raise ValueError("sct_symbolic_link")
            if len(all_files) > self.limits.zip_file_count:
                raise ValueError("sct_file_count_exceeded")
            if any(item.suffix.lower() in _REJECTED_SUFFIXES for item in all_files):
                raise ValueError("unsafe_sct_file_type")
            files = [item for item in all_files if item.suffix.lower() in _SUPPORTED_SUFFIXES]
            total = sum(item.stat().st_size for item in all_files)
            if total > self.limits.expanded_zip_bytes:
                raise ValueError("expanded_sct_size_exceeded")
            if any(item.stat().st_size > self.limits.single_file_bytes for item in files):
                raise ValueError("single_file_size_exceeded")
            return (
                [SourceRecord(str(item.relative_to(path)), item.read_bytes()) for item in files],
                [str(item.relative_to(path)) for item in all_files if item not in files],
            )
        if path.suffix.lower() == ".zip":
            return self._read_zip(path)
        if path.is_file() and path.suffix.lower() in _SUPPORTED_SUFFIXES:
            if path.stat().st_size > self.limits.single_file_bytes:
                raise ValueError("single_file_size_exceeded")
            return [SourceRecord(path.name, path.read_bytes())], []
        raise ValueError("unsupported_sct_input")

    def _read_zip(self, path: Path) -> tuple[list[SourceRecord], list[str]]:
        if path.stat().st_size > self.limits.single_file_bytes:
            raise ValueError("single_file_size_exceeded")
        records: list[SourceRecord] = []
        unsupported: list[str] = []
        expanded = 0
        seen_names: set[str] = set()
        try:
            archive = zipfile.ZipFile(path)
        except (zipfile.BadZipFile, OSError) as exc:
            raise ValueError("malformed_sct_zip") from exc
        with archive:
            infos = archive.infolist()
            if len(infos) > self.limits.zip_file_count:
                raise ValueError("sct_file_count_exceeded")
            for info in infos:
                if info.is_dir():
                    continue
                member = PurePosixPath(info.filename.replace("\\", "/"))
                if (
                    member.is_absolute()
                    or ".." in member.parts
                    or (member.parts and member.parts[0].endswith(":"))
                ):
                    raise ValueError("zip_path_traversal")
                normalized_name = unicodedata.normalize("NFC", str(member)).casefold()
                if normalized_name in seen_names:
                    raise ValueError("duplicate_sct_archive_member")
                seen_names.add(normalized_name)
                if info.flag_bits & 0x1:
                    raise ValueError("encrypted_sct_archive_member")
                mode = info.external_attr >> 16
                if stat.S_ISLNK(mode):
                    raise ValueError("zip_symbolic_link")
                if mode and mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
                    raise ValueError("executable_sct_archive_member")
                expanded += info.file_size
                if expanded > self.limits.expanded_zip_bytes:
                    raise ValueError("expanded_zip_size_exceeded")
                if info.file_size / max(info.compress_size, 1) > self.limits.compression_ratio:
                    raise ValueError("zip_compression_ratio_exceeded")
                if info.file_size > self.limits.single_file_bytes:
                    raise ValueError("single_file_size_exceeded")
                if member.suffix.lower() in _SUPPORTED_SUFFIXES:
                    try:
                        content = archive.read(info)
                    except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
                        raise ValueError("malformed_sct_zip_member") from exc
                    records.append(SourceRecord(str(member), content))
                elif member.suffix.lower() in _REJECTED_SUFFIXES:
                    raise ValueError("unsafe_sct_file_type")
                else:
                    unsupported.append(str(member))
        return records, unsupported

    def _parse_policy_rules(self, record: SourceRecord) -> list[dict[str, str]]:
        upper = record.content.upper()
        if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
            raise ValueError("unsafe_xml_declaration")
        try:
            root = ElementTree.fromstring(record.content)
        except ElementTree.ParseError as exc:
            raise ValueError(f"malformed_sct_xml:{record.filename}") from exc
        pending: list[dict[str, str]] = []
        for element in root.iter():
            attributes = {key.lower(): value for key, value in element.attrib.items()}
            name = attributes.get("name") or attributes.get("displayname") or attributes.get("id")
            value = attributes.get("value") or (element.text or "").strip()
            if name:
                pending.append(
                    {
                        "source_file": record.filename,
                        "source_element": element.tag.split("}")[-1],
                        "source_name": name,
                        "source_value": value,
                        "mapping_status": "pending_review",
                        "reason": "missing_exact_intune_canonical_identifier",
                    }
                )
                if len(pending) > self.limits.maximum_settings:
                    raise ValueError("maximum_sct_records_exceeded")
        return pending
