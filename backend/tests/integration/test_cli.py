from pathlib import Path

from typer.testing import CliRunner

from intune_auditor.cli.main import app

ROOT = Path(__file__).resolve().parents[3]
runner = CliRunner()


def test_cli_audit_uses_shared_offline_service(tmp_path: Path) -> None:
    output = tmp_path / "audit.json"
    result = runner.invoke(
        app,
        [
            "audit",
            str(ROOT / "samples" / "policies"),
            "--deviations",
            str(ROOT / "organization" / "accepted-deviations.example.json"),
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 0, result.output
    assert '"audit"' in output.read_text(encoding="utf-8")


def test_validate_pack_exit_codes() -> None:
    valid = runner.invoke(
        app,
        ["validate-pack", str(ROOT / "knowledge-packs" / "synthetic" / "test-baseline")],
    )
    assert valid.exit_code == 0
    assert '"valid": true' in valid.output


def test_fail_on_confirmed_conflict_returns_three(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "audit",
            str(ROOT / "samples" / "policies"),
            "--output",
            str(tmp_path / "audit.json"),
            "--fail-on",
            "confirmed-conflict",
        ],
    )
    assert result.exit_code == 3
