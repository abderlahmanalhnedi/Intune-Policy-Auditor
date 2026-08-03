"""Transparent coverage metrics and overall deterministic decision gates."""

from __future__ import annotations

from intune_auditor.domain.enums import (
    AlignmentStatus,
    ConflictConfidence,
    DecisionStatus,
    FindingSeverity,
    RuntimeState,
)
from intune_auditor.domain.models import (
    ConflictResult,
    CoverageMetrics,
    DecisionResult,
    DecisionTraceStep,
    PolicyEvaluation,
)
from intune_auditor.knowledge.loader import exact_official_evidence_allowed


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def coverage_metrics(
    policies: list[PolicyEvaluation], conflicts: list[ConflictResult]
) -> CoverageMetrics:
    settings = [evaluation for policy in policies for evaluation in policy.settings]
    total = len(settings)
    evaluable = sum(
        item.effective_alignment_status is not AlignmentStatus.NOT_EVALUABLE for item in settings
    )
    exact_technical = sum(
        item.observation.extraction_confidence.value == "exact" for item in settings
    )
    exact_ids = sum("unknown_setting_id" not in item.not_evaluable_reasons for item in settings)
    exact_values = sum(item.evidence_confidence.value == "exact" for item in settings)
    official_baselines = sum(
        any(exact_official_evidence_allowed("Microsoft", source) for source in item.evidence)
        for item in settings
    )
    documented = sum(bool(item.evidence) for item in settings)
    assigned_policies = sum(bool(policy.policy.assignments) for policy in policies)
    conflict_candidates = len(conflicts)
    analyzable_conflicts = sum(item.overlap_result != "missing_filter_data" for item in conflicts)
    runtime_policies = sum(policy.runtime_evidence is not None for policy in policies)
    return CoverageMetrics(
        parser_coverage=_ratio(exact_technical, total),
        technical_extraction_confidence=_ratio(exact_technical, total),
        exact_setting_coverage=_ratio(exact_ids, total),
        exact_value_semantic_coverage=_ratio(exact_values, total),
        microsoft_baseline_coverage=_ratio(official_baselines, total)
        if official_baselines
        else None,
        documentation_coverage=_ratio(documented, total),
        assignment_analysis_coverage=_ratio(assigned_policies, len(policies)),
        conflict_analysis_coverage=_ratio(analyzable_conflicts, conflict_candidates),
        runtime_evidence_coverage=_ratio(runtime_policies, len(policies))
        if runtime_policies
        else None,
        evaluable_settings=evaluable,
        not_evaluable_settings=total - evaluable,
    )


def overall_decision(
    policies: list[PolicyEvaluation],
    conflicts: list[ConflictResult],
    coverage: CoverageMetrics,
) -> DecisionResult:
    findings = [finding for policy in policies for finding in policy.findings]
    traces: list[DecisionTraceStep] = []

    def step(gate: str, outcome: str, de: str, en: str) -> None:
        traces.append(
            DecisionTraceStep(
                order=len(traces) + 1, gate=gate, outcome=outcome, explanation={"de": de, "en": en}
            )
        )

    runtime_errors = any(
        policy.runtime_evidence
        and policy.runtime_evidence.state in {RuntimeState.ERROR, RuntimeState.CONFLICT}
        for policy in policies
    )
    confirmed_conflicts = [
        item for item in conflicts if item.confidence is ConflictConfidence.CONFIRMED
    ]
    blocking_findings = [
        item
        for item in findings
        if item.severity in {FindingSeverity.CRITICAL, FindingSeverity.HIGH}
    ]
    expired = [item for item in findings if item.alignment is AlignmentStatus.EXPIRED_DEVIATION]
    low_evidence = (
        coverage.exact_setting_coverage is None
        or coverage.exact_setting_coverage < 0.5
        or coverage.exact_value_semantic_coverage is None
        or coverage.exact_value_semantic_coverage < 0.5
    )

    step(
        "runtime_evidence",
        "fail" if runtime_errors else "pass",
        "Laufzeitfehler wurden gefunden."
        if runtime_errors
        else "Kein belegter Laufzeitfehler blockiert die Entscheidung.",
        "Runtime errors were found."
        if runtime_errors
        else "No sourced runtime error blocks the decision.",
    )
    step(
        "confirmed_conflicts",
        "fail" if confirmed_conflicts else "pass",
        "Bestätigte Konflikte wurden gefunden."
        if confirmed_conflicts
        else "Keine bestätigten Konflikte wurden gefunden.",
        "Confirmed conflicts were found."
        if confirmed_conflicts
        else "No confirmed conflicts were found.",
    )
    step(
        "blocking_findings",
        "fail" if blocking_findings else "pass",
        "Mindestens ein belastbarer hoher Befund blockiert."
        if blocking_findings
        else "Kein hoher oder kritischer Befund blockiert.",
        "At least one substantiated high finding blocks."
        if blocking_findings
        else "No high or critical finding blocks.",
    )
    step(
        "evidence_coverage",
        "fail" if low_evidence else "pass",
        "Die exakte Abdeckung reicht nicht für eine Pilotentscheidung."
        if low_evidence
        else "Die Mindestabdeckung für die weitere Prüfung ist vorhanden.",
        "Exact coverage is insufficient for a pilot decision."
        if low_evidence
        else "Minimum coverage for further review is available.",
    )

    if runtime_errors:
        status = DecisionStatus.RUNTIME_REMEDIATION_REQUIRED
        reason = {
            "de": "Laufzeitevidenz enthält Fehler oder Konflikte.",
            "en": "Runtime evidence contains errors or conflicts.",
        }
        next_action = {
            "de": "Laufzeitfehler vor einer Konfigurationsänderung untersuchen.",
            "en": "Investigate runtime errors before configuration changes.",
        }
    elif confirmed_conflicts or blocking_findings:
        status = DecisionStatus.CHANGES_REQUIRED_BEFORE_PILOT
        reason = {
            "de": "Bestätigte Konflikte oder belastbare blockierende Befunde wurden gefunden.",
            "en": "Confirmed conflicts or substantiated blocking findings were found.",
        }
        next_action = {
            "de": "Konfliktzuweisungen prüfen und einen genehmigten Änderungsplan erstellen.",
            "en": "Review conflicting assignments and create an approved change plan.",
        }
    elif low_evidence:
        status = DecisionStatus.INSUFFICIENT_EVIDENCE
        reason = {
            "de": "Wesentliche Einstellungen sind nicht exakt bewertbar.",
            "en": "Material settings are not exactly evaluable.",
        }
        next_action = {
            "de": "Fehlende IDs, Wertsemantik und Quellen ergänzen; noch keinen Pilot starten.",
            "en": "Resolve missing IDs, value semantics, and sources; do not start a pilot yet.",
        }
    elif expired:
        status = DecisionStatus.MANUAL_REVIEW_REQUIRED
        reason = {
            "de": "Mindestens eine akzeptierte Abweichung ist abgelaufen.",
            "en": "At least one accepted deviation has expired.",
        }
        next_action = {
            "de": "Abweichung neu bewerten oder die Konfiguration ändern.",
            "en": "Reassess the deviation or change the configuration.",
        }
    elif any(item.alignment is AlignmentStatus.ACCEPTED_DEVIATION for item in findings):
        status = DecisionStatus.ALIGNED_WITH_ACCEPTED_DEVIATIONS
        reason = {
            "de": "Abweichungen sind aktiv akzeptiert; Rohunterschiede bleiben sichtbar.",
            "en": "Differences are actively accepted; raw differences remain visible.",
        }
        next_action = {
            "de": "Ablaufdaten überwachen und regelmäßig neu bewerten.",
            "en": "Monitor expiry dates and reassess periodically.",
        }
    elif not findings:
        status = DecisionStatus.ALIGNED_WITH_SELECTED_BASELINE
        reason = {
            "de": "Alle bewertbaren Einstellungen entsprechen dem ausgewählten Pack.",
            "en": "All evaluable settings match the selected pack.",
        }
        next_action = {
            "de": "Mit Organisationskontext und Pilotvalidierung fortfahren.",
            "en": "Continue with organizational context and pilot validation.",
        }
    else:
        status = DecisionStatus.PILOT_RECOMMENDED
        reason = {
            "de": "Es bestehen nicht blockierende, belegte Unterschiede.",
            "en": "Non-blocking evidenced differences remain.",
        }
        next_action = {
            "de": "Änderungen in einer begrenzten repräsentativen Gruppe testen.",
            "en": "Test changes in a limited representative group.",
        }
    blockers = [trace.gate for trace in traces if trace.outcome == "fail"]
    warnings = (
        ["synthetic_demonstration_data"]
        if any(policy.policy.is_synthetic for policy in policies)
        else []
    )
    titles = {
        DecisionStatus.ALIGNED_WITH_SELECTED_BASELINE: {
            "de": "Entspricht der ausgewählten Baseline",
            "en": "Aligned with selected baseline",
        },
        DecisionStatus.ALIGNED_WITH_ACCEPTED_DEVIATIONS: {
            "de": "Entspricht mit akzeptierten Abweichungen",
            "en": "Aligned with accepted deviations",
        },
        DecisionStatus.CHANGES_REQUIRED_BEFORE_PILOT: {
            "de": "Änderungen vor einem Pilot erforderlich",
            "en": "Changes required before pilot",
        },
        DecisionStatus.PILOT_RECOMMENDED: {
            "de": "Pilot empfohlen",
            "en": "Pilot recommended",
        },
        DecisionStatus.MANUAL_REVIEW_REQUIRED: {
            "de": "Manuelle Prüfung erforderlich",
            "en": "Manual review required",
        },
        DecisionStatus.INSUFFICIENT_EVIDENCE: {
            "de": "Unzureichende Evidenz",
            "en": "Insufficient evidence",
        },
        DecisionStatus.RUNTIME_REMEDIATION_REQUIRED: {
            "de": "Laufzeitfehler untersuchen",
            "en": "Runtime remediation required",
        },
    }
    return DecisionResult(
        status=status,
        title=titles[status],
        reason=reason,
        blocking_conditions=blockers,
        nonblocking_warnings=warnings,
        next_action=next_action,
        evidence_summary={
            "de": f"{coverage.evaluable_settings} Einstellungen bewertbar, {coverage.not_evaluable_settings} nicht bewertbar.",
            "en": f"{coverage.evaluable_settings} settings evaluable, {coverage.not_evaluable_settings} not evaluable.",
        },
        failed_gates=blockers,
        decision_trace=traces,
    )
