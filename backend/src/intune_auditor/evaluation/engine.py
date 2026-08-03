"""Evidence-gated setting evaluation and finding construction."""

from __future__ import annotations

from datetime import date
from typing import Final
from uuid import NAMESPACE_URL, uuid5

from intune_auditor.applicability.engine import evaluate_applicability
from intune_auditor.deviations.service import match_deviation
from intune_auditor.domain.enums import (
    AlignmentStatus,
    ApplicabilityState,
    EvidenceConfidence,
    FindingSeverity,
    FindingType,
    KnowledgePackStatus,
    Scope,
)
from intune_auditor.domain.models import (
    AcceptedDeviation,
    AuditContext,
    DecisionTraceStep,
    Finding,
    KnowledgeSetting,
    PolicyDocument,
    PolicyEvaluation,
    SettingEvaluation,
    SettingObservation,
)
from intune_auditor.evaluation.value_comparators import canonicalize_value, compare_values
from intune_auditor.knowledge.loader import (
    LoadedKnowledgePack,
    exact_official_evidence_allowed,
)

_NON_FINDING: Final = {AlignmentStatus.ALIGNED, AlignmentStatus.NOT_APPLICABLE}


def _text(de: str, en: str) -> dict[str, str]:
    return {"de": de, "en": en}


class EvaluationEngine:
    def __init__(self, packs: list[LoadedKnowledgePack]) -> None:
        self.packs = [pack for pack in packs if pack.active]
        self._settings: dict[str, list[tuple[KnowledgeSetting, LoadedKnowledgePack]]] = {}
        self._aliases: dict[str, list[tuple[KnowledgeSetting, LoadedKnowledgePack]]] = {}
        for pack in self.packs:
            for setting in pack.settings:
                canonical_key = setting.canonical_setting_id.casefold()
                self._settings.setdefault(canonical_key, []).append((setting, pack))
                for alias in setting.aliases:
                    self._aliases.setdefault(alias.casefold(), []).append((setting, pack))

    def evaluate_policy(
        self,
        policy: PolicyDocument,
        deviations: list[AcceptedDeviation],
        on_date: date,
        context: AuditContext | None = None,
    ) -> PolicyEvaluation:
        evaluations: list[SettingEvaluation] = []
        findings: list[Finding] = []
        for observation in policy.settings:
            evaluation, setting, deviation = self.evaluate_setting(
                observation, deviations, on_date, context or AuditContext()
            )
            evaluations.append(evaluation)
            if evaluation.effective_alignment_status not in _NON_FINDING:
                findings.append(self._finding(policy, evaluation, setting, deviation))
        return PolicyEvaluation(policy=policy, settings=evaluations, findings=findings)

    def evaluate_setting(
        self,
        observation: SettingObservation,
        deviations: list[AcceptedDeviation],
        on_date: date,
        context: AuditContext | None = None,
    ) -> tuple[SettingEvaluation, KnowledgeSetting | None, AcceptedDeviation | None]:
        trace: list[DecisionTraceStep] = []
        context = context or AuditContext()

        def step(gate: str, outcome: str, de: str, en: str) -> None:
            trace.append(
                DecisionTraceStep(
                    order=len(trace) + 1, gate=gate, outcome=outcome, explanation=_text(de, en)
                )
            )

        step(
            "parsed_observation",
            "pass",
            "Die Beobachtung ist typisiert.",
            "The observation is typed.",
        )
        canonical_key = observation.canonical_setting_id.casefold()
        canonical_matches = self._settings.get(canonical_key, [])
        alias_collisions = self._aliases.get(canonical_key, [])
        if len(canonical_matches) > 1 or alias_collisions:
            step(
                "exact_identifier",
                "fail",
                "Die ID ist in den ausgewählten Packs nicht eindeutig.",
                "The identifier is ambiguous across the selected packs.",
            )
            return (
                self._not_evaluable(
                    observation,
                    ["ambiguous_setting_id", "unresolved_baseline_version"],
                    trace,
                ),
                None,
                None,
            )
        match = canonical_matches[0] if canonical_matches else None
        match_type = "exact_canonical_id"
        if match is None:
            original_key = observation.original_setting_id.casefold()
            alias_matches = self._aliases.get(original_key, [])
            canonical_collisions = self._settings.get(original_key, [])
            if len(alias_matches) > 1 or (alias_matches and canonical_collisions):
                step(
                    "exact_identifier",
                    "fail",
                    "Die Alias-ID ist in den ausgewählten Packs nicht eindeutig.",
                    "The alias is ambiguous across the selected packs.",
                )
                return (
                    self._not_evaluable(
                        observation,
                        ["ambiguous_setting_id", "unresolved_baseline_version"],
                        trace,
                    ),
                    None,
                    None,
                )
            match = alias_matches[0] if alias_matches else None
            match_type = "explicit_pack_alias"
        if match is None:
            step(
                "exact_identifier",
                "fail",
                "Keine exakte ID oder validierte Alias-ID gefunden.",
                "No exact ID or validated alias was found.",
            )
            return (
                self._not_evaluable(
                    observation, ["unknown_setting_id", "setting_not_in_selected_baseline"], trace
                ),
                None,
                None,
            )
        setting, pack = match
        step(
            "exact_identifier",
            "pass",
            f"Treffer über {match_type}.",
            f"Matched through {match_type}.",
        )
        if observation.platform != setting.platform:
            step(
                "platform_compatibility",
                "fail",
                "Die Plattformen stimmen nicht überein.",
                "Platforms do not match.",
            )
            return self._not_evaluable(observation, ["platform_ambiguous"], trace), setting, None
        step("platform_compatibility", "pass", "Die Plattform stimmt überein.", "Platform matches.")
        if not self._scope_compatible(observation.scope, setting.scope):
            step(
                "scope_compatibility",
                "fail",
                "Die Bereiche sind nicht kompatibel.",
                "Scopes are incompatible.",
            )
            return self._not_evaluable(observation, ["scope_ambiguous"], trace), setting, None
        step("scope_compatibility", "pass", "Der Bereich ist kompatibel.", "Scope is compatible.")
        applicability = evaluate_applicability(setting.applicability, observation, context)
        if applicability.state is ApplicabilityState.NOT_APPLICABLE:
            step(
                "applicability",
                "not_applicable",
                "Eine belegte Anwendbarkeitsregel schließt das Ziel aus.",
                "A sourced applicability rule excludes the target.",
            )
            alignment = (
                AlignmentStatus.UNSUPPORTED
                if setting.applicability.unsupported
                else AlignmentStatus.NOT_APPLICABLE
            )
            return (
                SettingEvaluation(
                    observation=observation,
                    raw_alignment_status=alignment,
                    effective_alignment_status=alignment,
                    microsoft_value=setting.baseline_value,
                    baseline_product=pack.manifest.product,
                    baseline_version=pack.manifest.baseline_version,
                    evidence=setting.evidence_sources,
                    evidence_confidence=EvidenceConfidence.EXACT,
                    applicability=ApplicabilityState.NOT_APPLICABLE,
                    applicability_reasons=applicability.reasons,
                    trace=trace,
                ),
                setting,
                None,
            )
        if applicability.state is ApplicabilityState.UNKNOWN:
            step(
                "applicability",
                "unknown",
                "Erforderliche Zielinformationen fehlen; Anwendbarkeit bleibt unbekannt.",
                "Required target facts are missing; applicability remains unknown.",
            )
            return (
                self._not_evaluable(
                    observation,
                    ["applicability_unknown", *applicability.reasons],
                    trace,
                    setting,
                    pack,
                    applicability.reasons,
                ),
                setting,
                None,
            )
        step(
            "applicability",
            "applicable",
            "Die belegten Regeln sind anwendbar.",
            "Sourced rules are applicable.",
        )
        exact_evidence = (
            any(
                source.confidence is EvidenceConfidence.EXACT for source in setting.evidence_sources
            )
            if pack.manifest.status is KnowledgePackStatus.SYNTHETIC
            else pack.manifest.status is KnowledgePackStatus.VERIFIED
            and any(
                exact_official_evidence_allowed(pack.manifest.vendor, source)
                for source in setting.evidence_sources
            )
        )
        if not exact_evidence:
            step(
                "evidence",
                "fail",
                "Eine exakte zulässige Quelle fehlt.",
                "Exact allowed evidence is missing.",
            )
            return (
                self._not_evaluable(observation, ["missing_official_source"], trace, setting, pack),
                setting,
                None,
            )
        step("evidence", "pass", "Die Pack-Quelle ist vorhanden.", "Pack evidence is present.")
        configured, error = canonicalize_value(
            observation.canonical_value, setting.value_definition
        )
        if error is not None:
            step(
                "value_semantics",
                "fail",
                "Der konfigurierte Wert ist nicht eindeutig interpretierbar.",
                "Configured value semantics are unknown.",
            )
            return self._not_evaluable(observation, [error], trace, setting, pack), setting, None
        step(
            "value_semantics",
            "pass",
            "Der konfigurierte Wert wurde exakt interpretiert.",
            "Configured value was interpreted exactly.",
        )
        raw_status = compare_values(configured, setting.baseline_value, setting.comparison_rule)
        if raw_status is AlignmentStatus.NOT_EVALUABLE:
            step(
                "comparison",
                "fail",
                "Die Vergleichsregel konnte den Wert nicht ordnen.",
                "The comparison rule could not evaluate the value.",
            )
            return (
                self._not_evaluable(observation, ["unsupported_comparison"], trace, setting, pack),
                setting,
                None,
            )
        step(
            "comparison",
            raw_status.value,
            "Die explizite Vergleichsregel wurde angewendet.",
            "The explicit comparison rule was applied.",
        )
        effective_status: AlignmentStatus = raw_status
        deviation = None
        deviation_status, deviation = match_deviation(
            deviations,
            setting.canonical_setting_id,
            observation.source_policy_id,
            configured,
            on_date,
        )
        if deviation_status is not None:
            effective_status = deviation_status
            step(
                "organizational_deviation",
                deviation_status.value,
                "Eine wertgenaue organisatorische Abweichung wurde gefunden.",
                "A value-specific organizational deviation was found.",
            )
        else:
            step(
                "organizational_deviation",
                "none",
                "Keine passende Abweichung verändert das Ergebnis.",
                "No matching deviation changes the result.",
            )
        step(
            "effective_alignment",
            effective_status.value,
            "Der Rohstatus bleibt in der Entscheidung sichtbar.",
            "The raw status remains visible in the decision.",
        )
        return (
            SettingEvaluation(
                observation=observation,
                raw_alignment_status=raw_status,
                effective_alignment_status=effective_status,
                microsoft_value=setting.baseline_value,
                baseline_product=pack.manifest.product,
                baseline_version=pack.manifest.baseline_version,
                evidence=setting.evidence_sources,
                evidence_confidence=EvidenceConfidence.EXACT,
                applicability=ApplicabilityState.APPLICABLE,
                applicability_reasons=applicability.reasons,
                trace=trace,
            ),
            setting,
            deviation,
        )

    @staticmethod
    def _scope_compatible(observed: Scope, expected: Scope) -> bool:
        if Scope.UNKNOWN in {observed, expected}:
            return False
        return observed == expected or Scope.BOTH in {observed, expected}

    @staticmethod
    def _not_evaluable(
        observation: SettingObservation,
        reasons: list[str],
        trace: list[DecisionTraceStep],
        setting: KnowledgeSetting | None = None,
        pack: LoadedKnowledgePack | None = None,
        applicability_reasons: list[str] | None = None,
    ) -> SettingEvaluation:
        return SettingEvaluation(
            observation=observation,
            raw_alignment_status=AlignmentStatus.NOT_EVALUABLE,
            effective_alignment_status=AlignmentStatus.NOT_EVALUABLE,
            microsoft_value=setting.baseline_value if setting else None,
            baseline_product=pack.manifest.product if pack else None,
            baseline_version=pack.manifest.baseline_version if pack else None,
            evidence=setting.evidence_sources if setting else [],
            evidence_confidence=EvidenceConfidence.UNKNOWN,
            applicability=ApplicabilityState.UNKNOWN,
            applicability_reasons=applicability_reasons or [],
            not_evaluable_reasons=reasons,
            trace=trace,
        )

    def _finding(
        self,
        policy: PolicyDocument,
        evaluation: SettingEvaluation,
        setting: KnowledgeSetting | None,
        deviation: AcceptedDeviation | None,
    ) -> Finding:
        status = evaluation.effective_alignment_status
        if status is AlignmentStatus.EXPIRED_DEVIATION:
            finding_type = FindingType.EXPIRED_DEVIATION
            severity = FindingSeverity.MEDIUM
        elif status is AlignmentStatus.NOT_EVALUABLE:
            finding_type = FindingType.INSUFFICIENT_EVIDENCE
            severity = FindingSeverity.INFORMATION
        else:
            finding_type = FindingType.BASELINE_DEVIATION
            severity = (
                setting.severity_if_less_restrictive
                if status is AlignmentStatus.LESS_RESTRICTIVE and setting
                else FindingSeverity.INFORMATION
            )
        finding_pack = next(
            (pack for pack in self.packs if evaluation.baseline_product == pack.manifest.product),
            None,
        )
        if severity in {FindingSeverity.CRITICAL, FindingSeverity.HIGH} and (
            finding_pack is None
            or finding_pack.manifest.status is KnowledgePackStatus.SYNTHETIC
            or not any(
                exact_official_evidence_allowed(finding_pack.manifest.vendor, source)
                for source in evaluation.evidence
            )
        ):
            severity = FindingSeverity.MEDIUM
        display_name = (
            setting.display_name
            if setting
            else _text(
                evaluation.observation.original_setting_id,
                evaluation.observation.original_setting_id,
            )
        )
        title = _text(
            f"{display_name['de']}: {status.value}",
            f"{display_name['en']}: {status.value.replace('_', ' ')}",
        )
        if status is AlignmentStatus.NOT_EVALUABLE:
            explanation = _text(
                "Die erforderliche Evidenz ist unvollständig. Die Einstellung wird nicht als sicher bewertet.",
                "Required evidence is incomplete. The setting is not labelled safe.",
            )
        elif status is AlignmentStatus.MORE_RESTRICTIVE:
            explanation = _text(
                "Der Wert ist nach der expliziten Regel strenger. Das ist nicht automatisch besser.",
                "The explicit rule proves a more restrictive value. That is not automatically better.",
            )
        elif status is AlignmentStatus.ACCEPTED_DEVIATION:
            explanation = _text(
                "Die Abweichung ist aktuell akzeptiert; der Rohunterschied bleibt sichtbar.",
                "The deviation is currently accepted; the raw difference remains visible.",
            )
        elif status is AlignmentStatus.EXPIRED_DEVIATION:
            explanation = _text(
                "Die organisatorische Akzeptanz ist abgelaufen und muss überprüft werden.",
                "The organizational acceptance has expired and requires review.",
            )
        else:
            explanation = _text(
                "Der konfigurierte Wert weicht nach der dokumentierten Regel ab.",
                "The configured value differs under the documented rule.",
            )
        impact_less = (
            setting.impact_less_restrictive if setting else _text("Nicht bekannt.", "Unknown.")
        )
        impact_more = (
            setting.impact_more_restrictive if setting else _text("Nicht bekannt.", "Unknown.")
        )
        why = impact_less if status is AlignmentStatus.LESS_RESTRICTIVE else impact_more
        return Finding(
            finding_id=str(
                uuid5(
                    NAMESPACE_URL, f"finding:{evaluation.observation.observation_id}:{status.value}"
                )
            ),
            severity=severity,
            finding_type=finding_type,
            policy_id=policy.policy_id,
            policy_name=policy.name,
            setting_id=evaluation.observation.canonical_setting_id,
            setting_name=display_name,
            configured_value=evaluation.observation.canonical_value,
            microsoft_value=evaluation.microsoft_value,
            alignment=status,
            raw_alignment=evaluation.raw_alignment_status,
            title=title,
            explanation=explanation,
            why_it_matters=why,
            user_impact=impact_more
            if status is AlignmentStatus.MORE_RESTRICTIVE
            else _text("Vor der Änderung im Pilot prüfen.", "Validate in a pilot before changing."),
            business_impact=_text(
                "Eine Änderung kann Sicherheits-, Betriebs- oder Supportziele berühren.",
                "A change may affect security, operations, or support objectives.",
            ),
            recommended_action=_text(
                "Evidenz und Organisationskontext prüfen; Änderung nicht automatisch ausrollen.",
                "Review evidence and organizational context; do not deploy automatically.",
            ),
            pilot_suggestion=_text(
                "Mit einer repräsentativen, begrenzten Gerätegruppe testen.",
                "Test with a limited representative device group.",
            ),
            rollback_suggestion=_text(
                "Vorherigen Export sichern und die Änderung über den genehmigten Intune-Prozess zurücknehmen.",
                "Retain the prior export and revert through the approved Intune process.",
            ),
            evidence_confidence=evaluation.evidence_confidence,
            evidence=evaluation.evidence,
            baseline_product=evaluation.baseline_product,
            baseline_version=evaluation.baseline_version,
            verification_date=evaluation.evidence[0].verified_at if evaluation.evidence else None,
            decision_trace=evaluation.trace,
            assignments=policy.assignments,
            deviation_state=status.value if deviation else None,
            accepted_deviation=deviation,
            applicability=evaluation.applicability,
            not_evaluable_reasons=evaluation.not_evaluable_reasons,
        )
