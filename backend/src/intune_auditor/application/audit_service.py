"""Shared offline audit use case with bounded ephemeral result storage."""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from threading import RLock
from uuid import uuid4

from intune_auditor.assignments.engine import analyze_assignment_risks
from intune_auditor.conflicts.engine import ConflictEngine
from intune_auditor.deviations.service import load_deviations
from intune_auditor.domain.enums import (
    AlignmentStatus,
    ApplicabilityState,
    AuditMode,
    EvidenceConfidence,
    EvidenceType,
    FindingSeverity,
    FindingType,
    RuntimeState,
)
from intune_auditor.domain.models import (
    AuditConfiguration,
    AuditPreview,
    AuditPreviewPolicy,
    AuditResult,
    DecisionTraceStep,
    EvidenceSource,
    Finding,
    RuntimeEvidence,
)
from intune_auditor.evaluation.engine import EvaluationEngine
from intune_auditor.evaluation.metrics import coverage_metrics, overall_decision
from intune_auditor.knowledge.loader import KnowledgePackLoader, LoadedKnowledgePack
from intune_auditor.knowledge.manager import KnowledgePackManager
from intune_auditor.parsing.service import PolicyParser
from intune_auditor.persistence.database import Database
from intune_auditor.security.limits import DEFAULT_LIMITS, ProcessingLimits
from intune_auditor.security.uploads import ValidatedUpload, validate_uploads


def _text(de: str, en: str) -> dict[str, str]:
    return {"de": de, "en": en}


class AuditStore:
    """Bounded in-memory store; raw uploads are never retained."""

    def __init__(self, maximum: int = 20) -> None:
        self.maximum = maximum
        self._items: OrderedDict[str, AuditResult] = OrderedDict()
        self._lock = RLock()

    def put(self, result: AuditResult) -> None:
        with self._lock:
            self._items[result.audit_id] = result
            self._items.move_to_end(result.audit_id)
            while len(self._items) > self.maximum:
                self._items.popitem(last=False)

    def get(self, audit_id: str) -> AuditResult | None:
        with self._lock:
            result = self._items.get(audit_id)
            if result is not None:
                self._items.move_to_end(audit_id)
            return result

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


class AuditService:
    def __init__(
        self,
        repository_root: Path,
        limits: ProcessingLimits = DEFAULT_LIMITS,
        database: Database | None = None,
        data_dir: Path | None = None,
        extra_pack_paths: list[Path] | None = None,
        retention_days: int = 30,
        history_enabled: bool = False,
        save_reports: bool = False,
    ) -> None:
        self.repository_root = repository_root
        self.limits = limits
        self.pack_loader = KnowledgePackLoader()
        self.database = database
        self.data_dir = data_dir or repository_root / "tmp" / "application-data"
        self.retention_days = retention_days
        self.history_enabled = history_enabled
        self.save_reports = save_reports
        self.store = AuditStore()
        self.pack_manager = KnowledgePackManager(
            repository_root,
            self.data_dir,
            limits,
            database,
            extra_pack_paths,
        )

    @property
    def synthetic_pack_path(self) -> Path:
        return self.repository_root / "knowledge-packs" / "synthetic" / "test-baseline"

    def installed_packs(self) -> list[LoadedKnowledgePack]:
        return self.pack_manager.list()

    def audit_uploads(
        self,
        uploads: list[tuple[str, bytes]],
        configuration: AuditConfiguration,
        deviation_path: Path | None = None,
        *,
        mode: AuditMode = AuditMode.OFFLINE,
        synthetic: bool = False,
        on_date: date | None = None,
    ) -> AuditResult:
        validated = validate_uploads(uploads, self.limits)
        return self.audit_validated(
            validated,
            configuration,
            deviation_path,
            mode=mode,
            synthetic=synthetic,
            on_date=on_date,
        )

    def preview_uploads(self, uploads: list[tuple[str, bytes]]) -> AuditPreview:
        """Parse bounded uploads for wizard scope confirmation without retaining content."""

        parsed = PolicyParser(self.limits).parse(validate_uploads(uploads, self.limits))
        return AuditPreview(
            policy_count=len(parsed.policies),
            setting_count=sum(len(policy.settings) for policy in parsed.policies),
            policies=[
                AuditPreviewPolicy(
                    policy_id=policy.policy_id,
                    name=policy.name,
                    platform=policy.platform,
                    kind=policy.kind,
                    setting_count=len(policy.settings),
                )
                for policy in parsed.policies
            ],
            diagnostics=parsed.diagnostics,
            input_sha256=parsed.input_sha256,
            parser_version=parsed.parser_version,
        )

    def audit_validated(
        self,
        sources: list[ValidatedUpload],
        configuration: AuditConfiguration,
        deviation_path: Path | None = None,
        *,
        mode: AuditMode = AuditMode.OFFLINE,
        synthetic: bool = False,
        on_date: date | None = None,
    ) -> AuditResult:
        parser_result = PolicyParser(self.limits).parse(sources)
        packs = self._select_packs(configuration.active_pack_ids)
        deviations = load_deviations(deviation_path) if deviation_path else []
        evaluation_engine = EvaluationEngine(packs)
        policies = []
        for policy in parser_result.policies:
            policy = policy.model_copy(update={"is_synthetic": synthetic or policy.is_synthetic})
            policy_evaluation = evaluation_engine.evaluate_policy(
                policy, deviations, on_date or date.today(), configuration.context
            )
            risks = analyze_assignment_risks(
                policy,
                high_impact=any(
                    finding.severity in {FindingSeverity.CRITICAL, FindingSeverity.HIGH}
                    for finding in policy_evaluation.findings
                ),
            )
            policy_evaluation = policy_evaluation.model_copy(update={"assignment_risks": risks})
            if synthetic and policy.policy_id == "demo-firewall-exception":
                runtime = self._synthetic_runtime_evidence()
                runtime_finding = self._runtime_finding(policy_evaluation, runtime)
                policy_evaluation = policy_evaluation.model_copy(
                    update={
                        "runtime_evidence": runtime,
                        "findings": [*policy_evaluation.findings, runtime_finding],
                    }
                )
            policies.append(policy_evaluation)
        conflicts = ConflictEngine().analyze(policies)
        metrics = coverage_metrics(policies, conflicts)
        decision = overall_decision(policies, conflicts, metrics)
        findings = [finding for policy in policies for finding in policy.findings]
        risks = [risk for policy in policies for risk in policy.assignment_risks]
        result = AuditResult(
            audit_id=str(uuid4()),
            created_at=datetime.now(UTC),
            mode=mode,
            is_synthetic=synthetic or any(policy.policy.is_synthetic for policy in policies),
            configuration=configuration,
            policies=policies,
            findings=findings,
            conflicts=conflicts,
            assignment_risks=risks,
            diagnostics=parser_result.diagnostics,
            coverage=metrics,
            decision=decision,
            selected_pack_manifests=[pack.manifest for pack in packs],
        )
        self.store.put(result)
        self._persist_summary_if_enabled(result)
        return result

    def preferences(self) -> dict[str, object]:
        defaults: dict[str, object] = {
            "history_enabled": self.history_enabled,
            "retention_days": self.retention_days,
            "save_reports": self.save_reports,
            "automatic_cleanup": True,
        }
        if self.database is None:
            return defaults
        stored = self.database.get_setting("local_preferences", {})
        return {**defaults, **stored} if isinstance(stored, dict) else defaults

    def save_report_copy(self, filename: str, content: bytes) -> Path | None:
        if not bool(self.preferences()["save_reports"]):
            return None
        target_dir = self.data_dir / "reports"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / filename
        target.write_bytes(content)
        return target

    def _persist_summary_if_enabled(self, result: AuditResult) -> None:
        if self.database is None or not bool(self.preferences()["history_enabled"]):
            return
        retention_value = self.preferences()["retention_days"]
        retention = retention_value if isinstance(retention_value, int) else self.retention_days
        self.database.delete_expired_audits(datetime.now(UTC))
        self.database.save_audit_summary(
            result.audit_id,
            result.created_at,
            result.created_at + timedelta(days=retention),
            result.mode.value,
            {
                "decision": result.decision.status.value,
                "policy_count": len(result.policies),
                "finding_count": len(result.findings),
                "conflict_count": len(result.conflicts),
                "synthetic": result.is_synthetic,
            },
        )

    def demonstration_audit(self, language: str = "de") -> AuditResult:
        sample_dir = self.repository_root / "samples" / "policies"
        uploads = [(path.name, path.read_bytes()) for path in sorted(sample_dir.glob("*.json"))]
        configuration = AuditConfiguration(
            language=language,
            active_pack_ids=["synthetic.test-baseline"],
            exact_only=True,
        )
        return self.audit_uploads(
            uploads,
            configuration,
            self.repository_root / "organization" / "accepted-deviations.example.json",
            mode=AuditMode.DEMO,
            synthetic=True,
            on_date=date(2026, 8, 3),
        )

    def get(self, audit_id: str) -> AuditResult | None:
        if audit_id == "demo":
            return self.demonstration_audit()
        return self.store.get(audit_id)

    def cache_key(
        self,
        input_sha256: str,
        packs: list[LoadedKnowledgePack],
        deviation_hash: str | None,
        configuration: AuditConfiguration | None = None,
    ) -> str:
        from intune_auditor.version import (  # local import avoids a long module constant list
            AUDIT_SCHEMA_VERSION,
            COMPARISON_ENGINE_VERSION,
            PARSER_VERSION,
        )

        payload = {
            "input_sha256": input_sha256,
            "parser_version": PARSER_VERSION,
            "audit_schema_version": AUDIT_SCHEMA_VERSION,
            "packs": [(pack.manifest.pack_id, pack.manifest.data_sha256) for pack in packs],
            "deviation_hash": deviation_hash,
            "comparison_engine_version": COMPARISON_ENGINE_VERSION,
            "analysis_configuration": {
                "exact_only": configuration.exact_only,
                "context": configuration.context.model_dump(mode="json"),
                "organization_requirements": [
                    item.model_dump(mode="json") for item in configuration.organization_requirements
                ],
            }
            if configuration is not None
            else None,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def _select_packs(self, pack_ids: list[str]) -> list[LoadedKnowledgePack]:
        installed = {pack.manifest.pack_id: pack for pack in self.installed_packs() if pack.active}
        selected = [installed[pack_id] for pack_id in pack_ids if pack_id in installed]
        if pack_ids and len(selected) != len(set(pack_ids)):
            raise ValueError("missing_baseline")
        return selected

    @staticmethod
    def _synthetic_runtime_evidence() -> RuntimeEvidence:
        source = EvidenceSource(
            evidence_type=EvidenceType.MICROSOFT_RUNTIME_REPORT,
            title="Synthetic runtime report — not tenant data",
            source_reference="urn:intune-policy-auditor:synthetic:runtime",
            source_domain="local.synthetic",
            verified_at=date(2026, 8, 3),
            confidence=EvidenceConfidence.EXACT,
            is_official=False,
        )
        return RuntimeEvidence(
            state=RuntimeState.ERROR,
            targeted_count=24,
            success_count=20,
            error_count=4,
            conflict_count=0,
            pending_count=0,
            not_applicable_count=0,
            report_timestamp=datetime(2026, 8, 3, 8, tzinfo=UTC),
            source=source,
            api_version="synthetic",
        )

    @staticmethod
    def _runtime_finding(policy_evaluation: object, runtime: RuntimeEvidence) -> Finding:
        policy = policy_evaluation.policy  # type: ignore[attr-defined]
        trace = [
            DecisionTraceStep(
                order=1,
                gate="runtime_state",
                outcome="error",
                explanation=_text(
                    "Der synthetische Laufzeitbericht enthält Fehler.",
                    "The synthetic runtime report contains errors.",
                ),
            )
        ]
        return Finding(
            finding_id=f"runtime-{policy.policy_id}",
            severity=FindingSeverity.MEDIUM,
            finding_type=FindingType.RUNTIME_ERROR,
            policy_id=policy.policy_id,
            policy_name=policy.name,
            setting_id="runtime:deployment",
            setting_name=_text("Laufzeitstatus", "Runtime status"),
            configured_value="error",
            alignment=AlignmentStatus.NOT_EVALUABLE,
            title=_text(
                "Laufzeitfehler erfordern Untersuchung", "Runtime errors require investigation"
            ),
            explanation=_text(
                "Richtlinienabsicht und tatsächliche Bereitstellung werden getrennt bewertet.",
                "Policy intent and actual deployment are evaluated separately.",
            ),
            why_it_matters=_text(
                "Vier synthetische Geräte melden einen Fehler.",
                "Four synthetic devices report an error.",
            ),
            user_impact=_text(
                "Betroffene Geräte erhalten die beabsichtigte Konfiguration möglicherweise nicht.",
                "Affected devices may not receive the intended configuration.",
            ),
            business_impact=_text(
                "Die angenommene Abdeckung kann von der tatsächlichen Bereitstellung abweichen.",
                "Assumed coverage may differ from actual deployment.",
            ),
            recommended_action=_text(
                "Fehlercodes und betroffene Geräte im schreibgeschützten Bericht prüfen.",
                "Review error codes and affected devices in the read-only report.",
            ),
            pilot_suggestion=_text(
                "Fehler zuerst in der Pilotgruppe reproduzieren.",
                "Reproduce errors in the pilot group first.",
            ),
            rollback_suggestion=_text(
                "Keine automatische Änderung; genehmigten Rollbackplan verwenden.",
                "No automatic change; use the approved rollback plan.",
            ),
            evidence_confidence=EvidenceConfidence.EXACT,
            evidence=[runtime.source] if runtime.source else [],
            baseline_product=None,
            baseline_version=None,
            verification_date=date(2026, 8, 3),
            decision_trace=trace,
            assignments=policy.assignments,
            applicability=ApplicabilityState.UNKNOWN,
            runtime_evidence=runtime,
        )
