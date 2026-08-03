"""Sanitized HTML, PDF, Markdown, JSON, and CSV reports from typed audit results."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape

from jinja2 import BaseLoader, Environment, select_autoescape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from intune_auditor.domain.enums import AlignmentStatus
from intune_auditor.domain.models import AuditResult, ReportMetadata
from intune_auditor.security.csv_safety import safe_csv_cell
from intune_auditor.security.filenames import safe_report_filename
from intune_auditor.security.limits import ProcessingLimits
from intune_auditor.version import APP_VERSION, AUDIT_SCHEMA_VERSION, REPORT_SCHEMA_VERSION

_DISCLAIMER = {
    "de": "Dieses Projekt ist unabhängig und weder mit Microsoft verbunden noch von Microsoft unterstützt.",
    "en": "This project is independent and is not affiliated with or endorsed by Microsoft.",
}


def _safe_markdown_cell(value: object) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("|", "\\|")
        .replace("\r", " ")
        .replace("\n", " ")
    )


@dataclass(frozen=True, slots=True)
class RenderedReport:
    content: bytes
    media_type: str
    filename: str


class ReportService:
    def __init__(self, limits: ProcessingLimits) -> None:
        self.limits = limits

    def metadata(self, audit: AuditResult, language: str = "en") -> ReportMetadata:
        language = "de" if language == "de" else "en"
        generated_at = datetime.now(UTC)
        runtime_timestamps = [
            policy.runtime_evidence.report_timestamp
            for policy in audit.policies
            if policy.runtime_evidence is not None
            and policy.runtime_evidence.report_timestamp is not None
        ]
        latest_runtime = max(runtime_timestamps) if runtime_timestamps else None
        if latest_runtime is not None and latest_runtime.tzinfo is None:
            latest_runtime = latest_runtime.replace(tzinfo=UTC)
        limitations = (
            [
                "Exportierte Richtlinienabsicht belegt keine erfolgreiche Bereitstellung.",
                "Unbekannte Einstellungen und Werte sind nicht bewertbar.",
                "Synthetische Packs sind keine Microsoft-Empfehlungen.",
            ]
            if language == "de"
            else [
                "Exported policy intent does not prove successful deployment.",
                "Unknown settings and values are not evaluable.",
                "Synthetic packs are not Microsoft recommendations.",
            ]
        )
        return ReportMetadata(
            generated_at=generated_at,
            application_version=APP_VERSION,
            audit_schema_version=AUDIT_SCHEMA_VERSION,
            report_schema_version=REPORT_SCHEMA_VERSION,
            selected_pack_ids=[item.pack_id for item in audit.selected_pack_manifests],
            selected_pack_versions=[
                item.baseline_version for item in audit.selected_pack_manifests
            ],
            pack_hashes=[item.data_sha256 for item in audit.selected_pack_manifests],
            verification_dates=[item.verified_at for item in audit.selected_pack_manifests],
            audit_mode=audit.mode,
            runtime_data_age_seconds=max(int((generated_at - latest_runtime).total_seconds()), 0)
            if latest_runtime is not None
            else None,
            limitations=limitations,
            independent_project_disclaimer=_DISCLAIMER[language],
        )

    def render(
        self, audit: AuditResult, report_format: str, language: str = "en"
    ) -> RenderedReport:
        language = "de" if language == "de" else "en"
        renderers = {
            "json": self._json,
            "html": self._html,
            "technical-html": self._technical_html,
            "markdown": self._markdown,
            "findings-csv": self._findings_csv,
            "conflicts-csv": self._conflicts_csv,
            "not-evaluable-csv": self._not_evaluable_csv,
            "provenance-json": self._provenance_json,
            "pdf": self._pdf,
        }
        renderer = renderers.get(report_format)
        if renderer is None:
            raise ValueError("unsupported_report_format")
        report = renderer(audit, language)
        if len(report.content) > self.limits.maximum_report_bytes:
            raise ValueError("maximum_report_size_exceeded")
        return report

    def _json(self, audit: AuditResult, language: str) -> RenderedReport:
        payload = {
            "metadata": self.metadata(audit, language).model_dump(mode="json"),
            "audit": audit.model_dump(mode="json"),
        }
        return self._bytes(
            json.dumps(payload, ensure_ascii=False, indent=2), "application/json", "audit", "json"
        )

    def _html(self, audit: AuditResult, language: str) -> RenderedReport:
        template = Environment(
            loader=BaseLoader(), autoescape=select_autoescape(default=True)
        ).from_string(
            """<!doctype html><html lang="{{ language }}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Intune Policy Auditor</title><style>body{font-family:system-ui,sans-serif;max-width:1100px;margin:40px auto;padding:0 24px;color:#172033}header{border-bottom:3px solid #4338ca;padding-bottom:18px}.notice{background:#f2efff;border:1px solid #c7c2ff;padding:12px 16px;border-radius:8px}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:10px;border-bottom:1px solid #dce2ec;text-align:left;vertical-align:top}th{background:#f5f7fb}footer{margin-top:40px;color:#5d687b;font-size:12px}@media print{body{margin:0}.notice{break-inside:avoid}}</style></head><body><header><h1>Intune Policy Auditor</h1><p>{{ decision }}</p></header>{% if synthetic %}<p class="notice"><strong>{{ synthetic_label }}</strong></p>{% endif %}<h2>{{ summary_label }}</h2><p>{{ policies }}: {{ audit.policies|length }} · {{ findings }}: {{ audit.findings|length }} · {{ conflicts }}: {{ audit.conflicts|length }}</p><dl><dt>App / API schema / report schema</dt><dd>{{ metadata.application_version }} / {{ metadata.audit_schema_version }} / {{ metadata.report_schema_version }}</dd><dt>Mode</dt><dd>{{ metadata.audit_mode.value }}</dd><dt>Pack IDs / versions</dt><dd>{{ metadata.selected_pack_ids|join(', ') or '—' }} / {{ metadata.selected_pack_versions|join(', ') or '—' }}</dd><dt>Pack SHA-256</dt><dd>{{ metadata.pack_hashes|join(', ') or '—' }}</dd><dt>Verification dates</dt><dd>{{ metadata.verification_dates|join(', ') or '—' }}</dd><dt>Runtime data age (seconds)</dt><dd>{{ metadata.runtime_data_age_seconds if metadata.runtime_data_age_seconds is not none else '—' }}</dd></dl><h2>{{ findings }}</h2><table><thead><tr><th>{{ severity }}</th><th>{{ policy }}</th><th>{{ setting }}</th><th>{{ alignment }}</th><th>{{ evidence }}</th></tr></thead><tbody>{% for item in audit.findings %}<tr><td>{{ item.severity.value }}</td><td>{{ item.policy_name }}</td><td>{{ item.setting_name[language] }}</td><td>{{ item.alignment.value }}</td><td>{{ item.evidence_confidence.value }}</td></tr>{% endfor %}</tbody></table><h2>{{ limitations }}</h2><ul>{% for item in metadata.limitations %}<li>{{ item }}</li>{% endfor %}</ul><footer><p>{{ metadata.independent_project_disclaimer }}</p><p>{{ metadata.generated_at.isoformat() }} · v{{ metadata.application_version }} · schema {{ metadata.report_schema_version }}</p></footer></body></html>"""
        )
        labels = (
            {
                "summary_label": "Zusammenfassung",
                "policies": "Richtlinien",
                "findings": "Ergebnisse",
                "conflicts": "Konflikte",
                "severity": "Schweregrad",
                "policy": "Richtlinie",
                "setting": "Einstellung",
                "alignment": "Ausrichtung",
                "evidence": "Evidenz",
                "limitations": "Einschränkungen",
                "synthetic_label": "Synthetische Demodaten – keine offizielle Microsoft-Baseline",
            }
            if language == "de"
            else {
                "summary_label": "Summary",
                "policies": "Policies",
                "findings": "Findings",
                "conflicts": "Conflicts",
                "severity": "Severity",
                "policy": "Policy",
                "setting": "Setting",
                "alignment": "Alignment",
                "evidence": "Evidence",
                "limitations": "Limitations",
                "synthetic_label": "Synthetic demonstration data – not an official Microsoft baseline",
            }
        )
        body = template.render(
            language=language,
            audit=audit,
            metadata=self.metadata(audit, language),
            decision=audit.decision.title[language],
            synthetic=audit.is_synthetic,
            **labels,
        )
        return self._bytes(body, "text/html; charset=utf-8", "executive-audit", "html")

    def _technical_html(self, audit: AuditResult, language: str) -> RenderedReport:
        metadata = self.metadata(audit, language)
        template = Environment(
            loader=BaseLoader(), autoescape=select_autoescape(default=True)
        ).from_string(
            """<!doctype html><html lang="{{ language }}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Intune Policy Auditor — {{ title }}</title><style>body{font-family:system-ui,sans-serif;max-width:1300px;margin:32px auto;padding:0 20px;color:#172033}code,pre{font-family:ui-monospace,monospace}pre{white-space:pre-wrap;background:#f5f7fb;padding:12px;border:1px solid #dce2ec}table{border-collapse:collapse;width:100%;font-size:12px}th,td{padding:8px;border:1px solid #dce2ec;text-align:left;vertical-align:top}th{background:#0b1b35;color:#fff}.policy{break-before:auto;margin-top:28px}footer{margin-top:36px;color:#5d687b;font-size:12px}@media print{body{margin:0}.policy{break-inside:avoid}}</style></head><body><h1>Intune Policy Auditor — {{ title }}</h1><p>{{ audit.decision.title[language] }}</p><h2>{{ metadata_heading }}</h2><pre>{{ metadata_json }}</pre>{% for policy in audit.policies %}<section class="policy"><h2>{{ policy.policy.name }}</h2><p><code>{{ policy.policy.policy_id }}</code> · {{ policy.policy.platform.value }} · {{ policy.policy.kind.value }}</p><table><thead><tr><th>Setting ID</th><th>{{ configured }}</th><th>{{ selected }}</th><th>{{ alignment }}</th><th>{{ reasons }}</th><th>{{ trace }}</th></tr></thead><tbody>{% for item in policy.settings %}<tr><td><code>{{ item.observation.canonical_setting_id }}</code></td><td>{{ item.observation.display_value }}</td><td>{{ item.microsoft_value }}</td><td>{{ item.effective_alignment_status.value }}</td><td>{{ item.not_evaluable_reasons|join(', ') }}</td><td>{% for step in item.trace %}{{ step.order }}. {{ step.gate }} → {{ step.outcome }}{% if not loop.last %}<br>{% endif %}{% endfor %}</td></tr>{% endfor %}</tbody></table></section>{% endfor %}<footer><p>{{ metadata.independent_project_disclaimer }}</p></footer></body></html>"""
        )
        labels = (
            {
                "title": "Technischer Bericht",
                "metadata_heading": "Berichtsmetadaten",
                "configured": "Konfiguriert",
                "selected": "Ausgewählter Wert",
                "alignment": "Ausrichtung",
                "reasons": "Gründe",
                "trace": "Entscheidungsschritte",
            }
            if language == "de"
            else {
                "title": "Technical report",
                "metadata_heading": "Report metadata",
                "configured": "Configured",
                "selected": "Selected value",
                "alignment": "Alignment",
                "reasons": "Reasons",
                "trace": "Decision trace",
            }
        )
        body = template.render(
            audit=audit,
            language=language,
            metadata=metadata,
            metadata_json=json.dumps(
                metadata.model_dump(mode="json"), ensure_ascii=False, indent=2
            ),
            **labels,
        )
        return self._bytes(body, "text/html; charset=utf-8", "technical-audit", "html")

    def _markdown(self, audit: AuditResult, language: str) -> RenderedReport:
        metadata = self.metadata(audit, language)
        lines = ["# Intune Policy Auditor", "", f"**{audit.decision.title[language]}**", ""]
        if audit.is_synthetic:
            lines.extend(
                [
                    "> Synthetische Demodaten – keine offizielle Microsoft-Baseline"
                    if language == "de"
                    else "> Synthetic demonstration data – not an official Microsoft baseline",
                    "",
                ]
            )
        metadata_heading = "Berichtsmetadaten" if language == "de" else "Report metadata"
        lines.extend(
            [
                f"## {metadata_heading}",
                "",
                "```json",
                json.dumps(metadata.model_dump(mode="json"), ensure_ascii=False, indent=2),
                "```",
                "",
            ]
        )
        findings_heading = "Ergebnisse" if language == "de" else "Findings"
        severity_heading = "Schweregrad" if language == "de" else "Severity"
        policy_heading = "Richtlinie" if language == "de" else "Policy"
        setting_heading = "Einstellung" if language == "de" else "Setting"
        alignment_heading = "Ausrichtung" if language == "de" else "Alignment"
        lines.extend(
            [
                f"## {findings_heading}",
                "",
                f"| {severity_heading} | {policy_heading} | {setting_heading} | {alignment_heading} |",
                "|---|---|---|---|",
            ]
        )
        for item in audit.findings:
            cells = [
                item.severity.value,
                item.policy_name,
                item.setting_name[language],
                item.alignment.value,
            ]
            lines.append("| " + " | ".join(_safe_markdown_cell(cell) for cell in cells) + " |")
        lines.extend(["", "## Einschränkungen" if language == "de" else "## Limitations", ""])
        lines.extend(f"- {item}" for item in metadata.limitations)
        lines.extend(["", f"_{metadata.independent_project_disclaimer}_", ""])
        return self._bytes(
            "\n".join(lines), "text/markdown; charset=utf-8", "technical-audit", "md"
        )

    def _findings_csv(self, audit: AuditResult, language: str) -> RenderedReport:
        metadata = json.dumps(
            self.metadata(audit, language).model_dump(mode="json"), ensure_ascii=False
        )
        rows = [
            [
                item.finding_id,
                item.severity.value,
                item.finding_type.value,
                item.policy_name,
                item.setting_name[language],
                item.configured_value,
                item.microsoft_value,
                item.alignment.value,
                item.evidence_confidence.value,
                metadata,
            ]
            for item in audit.findings
        ]
        if not rows:
            rows = [[None] * 9 + [metadata]]
        return self._csv(
            [
                "finding_id",
                "severity",
                "type",
                "policy",
                "setting",
                "configured_value",
                "selected_value",
                "alignment",
                "evidence_confidence",
                "report_metadata_json",
            ],
            rows,
            "findings",
        )

    def _conflicts_csv(self, audit: AuditResult, language: str) -> RenderedReport:
        metadata = json.dumps(
            self.metadata(audit, language).model_dump(mode="json"), ensure_ascii=False
        )
        rows = [
            [
                item.conflict_id,
                item.classification,
                item.confidence.value,
                item.canonical_setting_id,
                item.policy_a_name,
                item.policy_a_value,
                item.policy_b_name,
                item.policy_b_value,
                item.overlap_result,
                metadata,
            ]
            for item in audit.conflicts
        ]
        if not rows:
            rows = [[None] * 9 + [metadata]]
        return self._csv(
            [
                "conflict_id",
                "classification",
                "confidence",
                "setting",
                "policy_a",
                "value_a",
                "policy_b",
                "value_b",
                "overlap",
                "report_metadata_json",
            ],
            rows,
            "conflicts",
        )

    def _not_evaluable_csv(self, audit: AuditResult, language: str) -> RenderedReport:
        metadata = json.dumps(
            self.metadata(audit, language).model_dump(mode="json"), ensure_ascii=False
        )
        rows: list[list[object]] = []
        for policy in audit.policies:
            for item in policy.settings:
                if item.effective_alignment_status is AlignmentStatus.NOT_EVALUABLE:
                    rows.append(
                        [
                            policy.policy.name,
                            item.observation.original_setting_id,
                            ",".join(item.not_evaluable_reasons),
                            item.observation.technical_json_path,
                            metadata,
                        ]
                    )
        if not rows:
            rows = [[None] * 4 + [metadata]]
        return self._csv(
            ["policy", "setting", "reasons", "json_path", "report_metadata_json"],
            rows,
            "not-evaluable",
        )

    def _provenance_json(self, audit: AuditResult, language: str) -> RenderedReport:
        payload = {
            "metadata": self.metadata(audit, language).model_dump(mode="json"),
            "knowledge_packs": [
                manifest.model_dump(mode="json") for manifest in audit.selected_pack_manifests
            ],
        }
        return self._bytes(
            json.dumps(payload, ensure_ascii=False, indent=2),
            "application/json",
            "knowledge-provenance",
            "json",
        )

    def _pdf(self, audit: AuditResult, language: str) -> RenderedReport:
        output = io.BytesIO()
        document = SimpleDocTemplate(
            output,
            pagesize=A4,
            rightMargin=16 * mm,
            leftMargin=16 * mm,
            topMargin=16 * mm,
            bottomMargin=16 * mm,
            title="Intune Policy Auditor",
            author="Intune Policy Auditor",
        )
        styles = getSampleStyleSheet()
        story: list[Flowable] = [
            Paragraph("Intune Policy Auditor", styles["Title"]),
            Paragraph(escape(audit.decision.title[language]), styles["Heading2"]),
            Paragraph(escape(audit.decision.reason[language]), styles["BodyText"]),
            Spacer(1, 6 * mm),
        ]
        if audit.is_synthetic:
            synthetic = (
                "Synthetische Demodaten - keine offizielle Microsoft-Baseline"
                if language == "de"
                else "Synthetic demonstration data - not an official Microsoft baseline"
            )
            story.extend(
                [Paragraph(f"<b>{escape(synthetic)}</b>", styles["BodyText"]), Spacer(1, 4 * mm)]
            )
        headings = ["Severity", "Policy", "Setting", "Alignment"]
        if language == "de":
            headings = ["Schweregrad", "Richtlinie", "Einstellung", "Ausrichtung"]
        table_data: list[list[object]] = [list(headings)]
        for finding in audit.findings:
            table_data.append(
                [
                    finding.severity.value,
                    Paragraph(escape(finding.policy_name), styles["BodyText"]),
                    Paragraph(escape(finding.setting_name[language]), styles["BodyText"]),
                    finding.alignment.value,
                ]
            )
        table = Table(table_data, colWidths=[24 * mm, 54 * mm, 70 * mm, 34 * mm], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b1b35")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dce2ec")),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#f5f7fb")],
                    ),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.extend([table, Spacer(1, 6 * mm)])
        metadata = self.metadata(audit, language)
        metadata_heading = "Berichtsmetadaten" if language == "de" else "Report metadata"
        story.append(Paragraph(metadata_heading, styles["Heading3"]))
        metadata_lines = [
            f"App / audit schema / report schema: {metadata.application_version} / "
            f"{metadata.audit_schema_version} / {metadata.report_schema_version}",
            f"Mode: {metadata.audit_mode.value}",
            f"Pack IDs: {', '.join(metadata.selected_pack_ids) or '—'}",
            f"Pack versions: {', '.join(metadata.selected_pack_versions) or '—'}",
            f"Pack SHA-256: {', '.join(metadata.pack_hashes) or '—'}",
            "Verification dates: "
            + (", ".join(item.isoformat() for item in metadata.verification_dates) or "—"),
            "Runtime data age (seconds): "
            + (
                str(metadata.runtime_data_age_seconds)
                if metadata.runtime_data_age_seconds is not None
                else "—"
            ),
        ]
        for line in metadata_lines:
            story.append(Paragraph(escape(line), styles["BodyText"]))
        story.append(
            Paragraph("Einschränkungen" if language == "de" else "Limitations", styles["Heading3"])
        )
        for limitation in metadata.limitations:
            story.append(Paragraph(f"• {escape(limitation)}", styles["BodyText"]))
        story.extend(
            [
                Spacer(1, 4 * mm),
                Paragraph(escape(metadata.independent_project_disclaimer), styles["Italic"]),
                Paragraph(
                    escape(
                        f"{'Erstellt' if language == 'de' else 'Generated'} "
                        f"{metadata.generated_at.isoformat()} · v{metadata.application_version} "
                        f"· report schema {metadata.report_schema_version}"
                    ),
                    styles["BodyText"],
                ),
            ]
        )
        document.build(story)
        return RenderedReport(
            content=output.getvalue(),
            media_type="application/pdf",
            filename=safe_report_filename("technical-audit", "pdf"),
        )

    def _csv(
        self,
        headers: Sequence[str],
        rows: Iterable[Sequence[object]],
        name: str,
    ) -> RenderedReport:
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerows([[safe_csv_cell(cell) for cell in row] for row in rows])
        return self._bytes(output.getvalue(), "text/csv; charset=utf-8", name, "csv")

    @staticmethod
    def _bytes(text: str, media_type: str, name: str, suffix: str) -> RenderedReport:
        return RenderedReport(
            content=text.encode("utf-8"),
            media_type=media_type,
            filename=safe_report_filename(name, suffix),
        )
