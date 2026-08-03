"""CLI facade over the same application services used by the web API."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer

from intune_auditor.application.audit_service import AuditService
from intune_auditor.domain.enums import FindingSeverity
from intune_auditor.domain.models import AuditConfiguration, AuditResult
from intune_auditor.knowledge.importers.sct import SecurityComplianceToolkitImporter
from intune_auditor.knowledge.loader import KnowledgePackLoader
from intune_auditor.reporting.service import ReportService
from intune_auditor.security.limits import DEFAULT_LIMITS
from intune_auditor.version import APP_VERSION

app = typer.Typer(
    name="intune-auditor",
    help="Evidence-based, read-only auditing for exported Intune policies.",
    no_args_is_help=True,
)


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _input_files(path: Path) -> list[tuple[str, bytes]]:
    if path.is_file():
        return [(path.name, path.read_bytes())]
    if path.is_dir():
        candidates = [
            item
            for item in sorted(path.rglob("*"))
            if item.is_file() and item.suffix.lower() in {".json", ".zip"}
        ]
        if not candidates:
            raise ValueError("no_supported_input_files")
        return [(str(item.relative_to(path)), item.read_bytes()) for item in candidates]
    raise ValueError("input_path_not_found")


def _service_and_pack(knowledge_pack: Path | None) -> tuple[AuditService, str]:
    root = _repository_root()
    if knowledge_pack is None:
        return AuditService(root), "synthetic.test-baseline"
    if not knowledge_pack.is_dir():
        raise ValueError("knowledge_pack_must_be_a_directory")
    pack = KnowledgePackLoader().load(knowledge_pack)
    return AuditService(root, extra_pack_paths=[knowledge_pack]), pack.manifest.pack_id


def _threshold_reached(result: AuditResult, fail_on: str) -> bool:
    if fail_on == "never":
        return False
    if fail_on == "confirmed-conflict":
        return any(item.confidence.value == "confirmed" for item in result.conflicts)
    rank = {
        FindingSeverity.NONE: 0,
        FindingSeverity.INFORMATION: 1,
        FindingSeverity.LOW: 2,
        FindingSeverity.MEDIUM: 3,
        FindingSeverity.HIGH: 4,
        FindingSeverity.CRITICAL: 5,
    }
    minimum = FindingSeverity.CRITICAL if fail_on == "critical" else FindingSeverity.HIGH
    return any(rank[item.severity] >= rank[minimum] for item in result.findings)


@app.command()
def audit(
    path: Annotated[Path, typer.Argument(help="JSON file, ZIP, or directory to audit")],
    knowledge_pack: Annotated[
        Path | None,
        typer.Option("--knowledge-pack", help="Validated knowledge-pack directory"),
    ] = None,
    deviations: Annotated[
        Path | None,
        typer.Option("--deviations", help="Accepted-deviations JSON file"),
    ] = None,
    language: Annotated[str, typer.Option(help="Report language: de or en")] = "en",
    report_format: Annotated[
        str,
        typer.Option("--format", help="json, html, markdown, csv, or pdf"),
    ] = "json",
    output: Annotated[
        Path | None,
        typer.Option("--output", help="Output file; stdout when omitted"),
    ] = None,
    exact_only: Annotated[
        bool,
        typer.Option("--exact-only/--no-exact-only", help="Require exact deterministic matching"),
    ] = True,
    fail_on: Annotated[
        str,
        typer.Option(help="critical, high, confirmed-conflict, or never"),
    ] = "never",
) -> None:
    """Audit exported policies without contacting Microsoft Graph."""

    if language not in {"de", "en"}:
        raise typer.BadParameter("must be de or en", param_hint="--language")
    format_map = {
        "json": "json",
        "html": "html",
        "markdown": "markdown",
        "csv": "findings-csv",
        "pdf": "pdf",
    }
    if report_format not in format_map:
        raise typer.BadParameter("must be json, html, markdown, csv, or pdf", param_hint="--format")
    if fail_on not in {"critical", "high", "confirmed-conflict", "never"}:
        raise typer.BadParameter(
            "must be critical, high, confirmed-conflict, or never", param_hint="--fail-on"
        )
    try:
        service, pack_id = _service_and_pack(knowledge_pack)
        configuration = AuditConfiguration(
            language=language,
            active_pack_ids=[pack_id],
            exact_only=exact_only,
        )
        result = service.audit_uploads(
            _input_files(path),
            configuration,
            deviation_path=deviations,
        )
        report = ReportService(service.limits).render(result, format_map[report_format], language)
    except (OSError, ValueError) as exc:
        typer.echo(f"Audit failed: {exc}", err=True)
        raise typer.Exit(code=2) from exc

    if output is None:
        sys.stdout.buffer.write(report.content)
        if not report.content.endswith(b"\n") and report.media_type != "application/pdf":
            sys.stdout.buffer.write(b"\n")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(report.content)
        typer.echo(f"Wrote {output}", err=True)

    if _threshold_reached(result, fail_on):
        raise typer.Exit(code=3)


@app.command("validate-pack")
def validate_pack(
    path: Annotated[Path, typer.Argument(help="Knowledge-pack directory")],
) -> None:
    """Validate schemas, hashes, identifiers, ordering, and evidence metadata."""

    if not path.exists() or not path.is_dir():
        typer.echo("Knowledge pack path is not a directory.", err=True)
        raise typer.Exit(code=2)
    report = KnowledgePackLoader().validate(path)
    typer.echo(report.model_dump_json(indent=2))
    if not report.valid:
        raise typer.Exit(code=1)


@app.command("import-sct")
def import_sct(
    input_path: Annotated[
        Path,
        typer.Option("--input", help="SCT XML file, directory, or ZIP"),
    ],
    output_path: Annotated[
        Path,
        typer.Option("--output", help="New knowledge-pack directory"),
    ],
    product: Annotated[str, typer.Option(help="Product named by the supplied toolkit")],
    version: Annotated[str, typer.Option(help="Toolkit/baseline version")],
    source_reference: Annotated[
        str,
        typer.Option(help="Official source URL for the user-supplied toolkit"),
    ],
) -> None:
    """Import SCT records conservatively into a pending-review pack."""

    try:
        result = SecurityComplianceToolkitImporter(DEFAULT_LIMITS).import_content(
            input_path,
            output_path,
            product,
            version,
            source_reference,
        )
    except (OSError, ValueError) as exc:
        typer.echo(f"Import failed: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(result.model_dump_json(indent=2))


@app.command()
def version() -> None:
    """Print the application version."""

    typer.echo(APP_VERSION)


if __name__ == "__main__":
    app()
