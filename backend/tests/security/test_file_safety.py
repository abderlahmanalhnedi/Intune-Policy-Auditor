import io
import stat
import zipfile

import pytest

from intune_auditor.security.archive import read_safe_zip
from intune_auditor.security.csv_safety import safe_csv_cell
from intune_auditor.security.html_safety import safe_html
from intune_auditor.security.json_safety import strict_json_loads
from intune_auditor.security.limits import ProcessingLimits
from intune_auditor.security.uploads import validate_uploads


def zip_bytes(name: str, content: bytes, compression: int = zipfile.ZIP_DEFLATED) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=compression) as archive:
        archive.writestr(name, content)
    return output.getvalue()


def test_safe_json_zip_is_read_in_memory() -> None:
    uploads = validate_uploads(
        [("export.zip", zip_bytes("policies/export.json", b'{"id":"p"}'))],
        ProcessingLimits(),
    )
    assert uploads[0].archive_member == "policies/export.json"
    assert uploads[0].content == b'{"id":"p"}'


def test_top_level_upload_count_is_bounded() -> None:
    with pytest.raises(ValueError, match="file_count_exceeded"):
        validate_uploads(
            [(f"{index}.json", b"{}") for index in range(3)],
            ProcessingLimits(zip_file_count=2),
        )


@pytest.mark.parametrize("name", ["../escape.json", "/absolute.json", "folder/../../escape.json"])
def test_zip_path_traversal_is_rejected(name: str) -> None:
    with pytest.raises(ValueError, match="zip_path_traversal"):
        read_safe_zip(zip_bytes(name, b"{}"), ProcessingLimits())


def test_nested_archive_is_rejected() -> None:
    with pytest.raises(ValueError, match="nested_archive_not_allowed"):
        read_safe_zip(zip_bytes("nested.zip", b"not-a-zip"), ProcessingLimits())


def test_excessive_compression_ratio_is_rejected() -> None:
    with pytest.raises(ValueError, match="zip_compression_ratio_exceeded"):
        read_safe_zip(
            zip_bytes("large.json", b" " * 100_000),
            ProcessingLimits(compression_ratio=2),
        )


def test_windows_absolute_archive_path_is_rejected() -> None:
    with pytest.raises(ValueError, match="zip_path_traversal"):
        read_safe_zip(zip_bytes("C:/outside.json", b"{}"), ProcessingLimits())


def test_executable_archive_mode_is_rejected_even_with_json_suffix() -> None:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        info = zipfile.ZipInfo("policy.json")
        info.create_system = 3
        info.external_attr = (stat.S_IFREG | 0o755) << 16
        archive.writestr(info, b"{}")
    with pytest.raises(ValueError, match="executable_archive_member"):
        read_safe_zip(output.getvalue(), ProcessingLimits())


def test_empty_and_case_duplicate_archives_are_rejected() -> None:
    empty = io.BytesIO()
    with zipfile.ZipFile(empty, "w"):
        pass
    with pytest.raises(ValueError, match="empty_zip"):
        read_safe_zip(empty.getvalue(), ProcessingLimits())

    duplicate = io.BytesIO()
    with zipfile.ZipFile(duplicate, "w") as archive:
        archive.writestr("Policy.json", b"{}")
        archive.writestr("policy.json", b"{}")
    with pytest.raises(ValueError, match="duplicate_archive_member"):
        read_safe_zip(duplicate.getvalue(), ProcessingLimits())


def test_equivalent_archive_paths_and_bad_crc_are_rejected() -> None:
    duplicate = io.BytesIO()
    with zipfile.ZipFile(duplicate, "w") as archive:
        archive.writestr("folder/policy.json", b"{}")
        archive.writestr("folder//policy.json", b"{}")
    with pytest.raises(ValueError, match="duplicate_archive_member"):
        read_safe_zip(duplicate.getvalue(), ProcessingLimits())

    damaged = bytearray(zip_bytes("policy.json", b"unique-payload", zipfile.ZIP_STORED))
    payload_offset = damaged.find(b"unique-payload")
    assert payload_offset >= 0
    damaged[payload_offset] ^= 0x01
    with pytest.raises(ValueError, match="malformed_zip_member"):
        read_safe_zip(bytes(damaged), ProcessingLimits())


@pytest.mark.parametrize("prefix", ["=", "+", "-", "@"])
def test_csv_formula_prefixes_are_escaped(prefix: str) -> None:
    assert safe_csv_cell(prefix + "SUM(A1)").startswith("'")


def test_html_is_escaped() -> None:
    assert (
        safe_html('<script>alert("x")</script>')
        == "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;"
    )


@pytest.mark.parametrize(
    "content",
    ['{"id":"first","id":"second"}', '{"value":NaN}', '{"value":Infinity}'],
)
def test_ambiguous_or_non_standard_json_is_rejected(content: str) -> None:
    with pytest.raises(ValueError, match=r"duplicate_json_key|non_finite_json_number"):
        strict_json_loads(content)


def test_json_decoder_recursion_is_reported_as_a_validation_error() -> None:
    content = "[" * 2_000 + "0" + "]" * 2_000
    with pytest.raises(ValueError, match="json_nesting_depth_exceeded"):
        strict_json_loads(content)


def test_json_depth_scanner_ignores_delimiters_inside_strings() -> None:
    assert strict_json_loads('{"literal":"[[[{{{\\""}') == {"literal": '[[[{{{"'}
