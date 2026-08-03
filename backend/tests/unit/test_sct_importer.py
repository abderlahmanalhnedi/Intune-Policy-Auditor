import stat
import zipfile
from pathlib import Path

import pytest

from intune_auditor.knowledge.importers.sct import SecurityComplianceToolkitImporter
from intune_auditor.knowledge.loader import KnowledgePackLoader
from intune_auditor.security.limits import ProcessingLimits

ROOT = Path(__file__).resolve().parents[3]


def test_sct_records_remain_pending_without_exact_intune_mapping(tmp_path: Path) -> None:
    output = tmp_path / "output"
    result = SecurityComplianceToolkitImporter(ProcessingLimits()).import_content(
        ROOT / "backend" / "tests" / "fixtures" / "sct",
        output,
        "Synthetic Windows Baseline",
        "0-test",
        "https://download.microsoft.com/synthetic-test",
    )
    assert result.pending_review_count == 2
    assert result.manifest.setting_count == 0
    assert result.manifest.status.value == "pending_review"
    assert KnowledgePackLoader().validate(output).valid


def write_sct_zip(path: Path, members: list[zipfile.ZipInfo | str]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for member in members:
            archive.writestr(
                member, b'<PolicyRules><Rule name="Example" value="1" /></PolicyRules>'
            )


def test_sct_zip_rejects_windows_paths_duplicate_names_and_executable_xml(
    tmp_path: Path,
) -> None:
    importer = SecurityComplianceToolkitImporter(ProcessingLimits())

    windows_path = tmp_path / "windows-path.zip"
    write_sct_zip(windows_path, ["C:/PolicyRules.xml"])
    with pytest.raises(ValueError, match="zip_path_traversal"):
        importer.import_content(
            windows_path,
            tmp_path / "windows-output",
            "Product",
            "1",
            "https://download.microsoft.com/example",
        )

    duplicate = tmp_path / "duplicate.zip"
    write_sct_zip(duplicate, ["PolicyRules.xml", "policyrules.xml"])
    with pytest.raises(ValueError, match="duplicate_sct_archive_member"):
        importer.import_content(
            duplicate,
            tmp_path / "duplicate-output",
            "Product",
            "1",
            "https://download.microsoft.com/example",
        )

    executable = tmp_path / "executable.zip"
    info = zipfile.ZipInfo("PolicyRules.xml")
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o755) << 16
    write_sct_zip(executable, [info])
    with pytest.raises(ValueError, match="executable_sct_archive_member"):
        importer.import_content(
            executable,
            tmp_path / "executable-output",
            "Product",
            "1",
            "https://download.microsoft.com/example",
        )


def test_sct_record_count_is_bounded(tmp_path: Path) -> None:
    source = tmp_path / "records.xml"
    source.write_bytes(
        b"<PolicyRules>" + b'<Rule name="Example" value="1" />' * 3 + b"</PolicyRules>"
    )
    importer = SecurityComplianceToolkitImporter(ProcessingLimits(maximum_settings=2))

    with pytest.raises(ValueError, match="maximum_sct_records_exceeded"):
        importer.import_content(
            source,
            tmp_path / "record-output",
            "Product",
            "1",
            "https://download.microsoft.com/example",
        )
