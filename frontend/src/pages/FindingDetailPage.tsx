import { ArrowLeft, Check, CircleHelp, ExternalLink } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { usePreferences } from "../app/preferences";
import { ErrorState, LoadingState } from "../components/QueryState";
import { StatusBadge } from "../components/StatusBadge";
import { displayValue, localized } from "../features/audit/format";
import { useAudit, useFinding } from "../features/audit/hooks";

export function FindingDetailPage() {
  const { auditId, findingId } = useParams<{ auditId: string; findingId: string }>();
  const { t, i18n } = useTranslation();
  const { mode } = usePreferences();
  const query = useFinding(auditId, findingId);
  const auditQuery = useAudit(auditId);
  if (query.isLoading || auditQuery.isLoading) return <LoadingState />;
  if (query.isError || !query.data || auditQuery.isError || !auditQuery.data) {
    return <ErrorState error={query.error ?? auditQuery.error} />;
  }
  const item = query.data;
  const relatedConflicts = auditQuery.data.conflicts.filter(
    (conflict) => conflict.canonical_setting_id === item.setting_id && (conflict.policy_a_id === item.policy_id || conflict.policy_b_id === item.policy_id),
  );
  const guided = [
    [t("findings.whatFound"), localized(item.explanation, i18n.language)],
    [t("findings.whyImportant"), localized(item.why_it_matters, i18n.language)],
    [t("findings.recommendation"), displayValue(item.microsoft_value)],
    [t("findings.current"), displayValue(item.configured_value)],
    [t("findings.confirmed"), item.evidence_confidence === "exact" && item.alignment !== "not_evaluable" && item.evidence.some((source) => source.is_official) ? t("common.yes") : t("common.no")],
    [t("findings.affected"), item.affected_device_count !== null && item.affected_device_count !== undefined ? String(item.affected_device_count) : item.assignments.map((assignment) => assignment.display_name ?? assignment.target_type).join(", ") || t("common.notAvailable")],
    [t("findings.next"), localized(item.recommended_action, i18n.language)],
    [t("findings.pilot"), localized(item.pilot_suggestion, i18n.language)],
    [t("findings.rollback"), localized(item.rollback_suggestion, i18n.language)],
    [t("findings.certainty"), t(`status.${item.evidence_confidence}`)],
    [t("findings.source"), item.evidence.map((source) => source.title).join(", ") || t("common.notAvailable")],
  ];
  const deviationDays = item.accepted_deviation
    ? Math.ceil((new Date(`${item.accepted_deviation.valid_until}T23:59:59Z`).getTime() - Date.now()) / 86_400_000)
    : null;
  return (
    <div className="content-page detail-page">
      <Link className="back-link" to={`/audit/${auditId}/findings`}><ArrowLeft size={16} aria-hidden />{t("navigation.findings")}</Link>
      <div className="finding-hero">
        <div><p className="eyebrow">{t("findings.judgment")}</p><h1>{localized(item.title, i18n.language)}</h1><div className="badge-row"><StatusBadge status={item.severity} /><StatusBadge status={item.alignment} /><StatusBadge status={item.evidence_confidence} /></div></div>
        <div className="value-comparison"><div><span>{t("findings.current")}</span><strong>{displayValue(item.configured_value)}</strong></div><div className="comparison-arrow" aria-hidden>→</div><div><span>{t("findings.recommendation")}</span><strong>{displayValue(item.microsoft_value)}</strong></div></div>
      </div>
      <section className="guided-grid">
        {guided.map(([question, answer]) => <article className="guided-answer" key={question}><CircleHelp size={18} aria-hidden /><div><h2>{question}</h2><p>{answer}</p></div></article>)}
      </section>
      <div className="detail-grid">
        <section className="panel"><h2>{t("findings.userImpact")}</h2><p>{localized(item.user_impact, i18n.language)}</p></section>
        <section className="panel"><h2>{t("findings.businessImpact")}</h2><p>{localized(item.business_impact, i18n.language)}</p></section>
        <section className="panel"><h2>{t("findings.applicability")}</h2><StatusBadge status={item.applicability} /></section>
        <section className="panel"><h2>{t("policies.assignments")}</h2>{item.assignments.length ? <ul className="plain-list">{item.assignments.map((assignment, index) => <li key={`${assignment.target_id ?? assignment.target_type}-${String(index)}`}><span><strong>{assignment.display_name ?? assignment.target_type}</strong><small>{assignment.scope}{assignment.filter ? ` · ${assignment.filter.mode}: ${assignment.filter.display_name ?? assignment.filter.filter_id ?? t("common.notAvailable")}` : ""}</small></span></li>)}</ul> : <p>{t("common.notAvailable")}</p>}</section>
        <section className="panel"><h2>{t("findings.relatedConflicts")}</h2>{relatedConflicts.length ? <ul className="plain-list">{relatedConflicts.map((conflict) => <li key={conflict.conflict_id}><StatusBadge status={conflict.classification} /><span>{conflict.policy_a_name} ↔ {conflict.policy_b_name}</span></li>)}</ul> : <p>{t("common.noResults")}</p>}</section>
        <section className="panel">
          <h2>{t("findings.source")}</h2>
          <dl className="technical-list"><div><dt>{t("common.baseline")}</dt><dd>{item.baseline_product ?? "—"} · {item.baseline_version ?? "—"}</dd></div><div><dt>{t("findings.verificationDate")}</dt><dd>{item.verification_date ? new Intl.DateTimeFormat(i18n.language, { dateStyle: "medium" }).format(new Date(`${item.verification_date}T00:00:00`)) : "—"}</dd></div></dl>
          {item.evidence.length ? item.evidence.map((source, index) => source.source_reference.startsWith("https://") ? <a className="source-link" href={source.source_reference} key={`${source.title}-${String(index)}`} rel="noreferrer" target="_blank">{source.title}<ExternalLink size={14} aria-hidden /></a> : <p key={`${source.title}-${String(index)}`}><strong>{source.title}</strong><br /><code>{source.source_reference}</code></p>) : <p>{t("common.notAvailable")}</p>}
        </section>
        {(item.not_evaluable_reasons ?? []).length ? <section className="panel"><h2>{t("findings.missingEvidence")}</h2><ul className="reason-summary">{(item.not_evaluable_reasons ?? []).map((reason) => <li key={reason}><span>{t(`reasons.${reason}`, { defaultValue: reason.replaceAll("_", " ") })}</span></li>)}</ul><h3>{t("findings.suggestedResolution")}</h3><p>{localized(item.recommended_action, i18n.language)}</p></section> : null}
        {item.runtime_evidence ? <section className="panel"><h2>{t("findings.runtimeEvidence")}</h2><dl className="technical-list"><div><dt>{t("tenant.state")}</dt><dd><StatusBadge status={item.runtime_evidence.state} /></dd></div><div><dt>{t("findings.targeted")}</dt><dd>{item.runtime_evidence.targeted_count ?? "—"}</dd></div><div><dt>{t("findings.succeeded")}</dt><dd>{item.runtime_evidence.success_count ?? "—"}</dd></div><div><dt>{t("findings.errors")}</dt><dd>{item.runtime_evidence.error_count ?? "—"}</dd></div><div><dt>{t("findings.runtimeConflicts")}</dt><dd>{item.runtime_evidence.conflict_count ?? "—"}</dd></div><div><dt>{t("findings.pending")}</dt><dd>{item.runtime_evidence.pending_count ?? "—"}</dd></div><div><dt>{t("findings.runtimeNotApplicable")}</dt><dd>{item.runtime_evidence.not_applicable_count ?? "—"}</dd></div><div><dt>{t("findings.apiVersion")}</dt><dd>{item.runtime_evidence.api_version ?? "—"}</dd></div><div><dt>{t("findings.reported")}</dt><dd>{item.runtime_evidence.report_timestamp ? new Intl.DateTimeFormat(i18n.language, { dateStyle: "medium", timeStyle: "short" }).format(new Date(item.runtime_evidence.report_timestamp)) : "—"}</dd></div><div><dt>{t("common.source")}</dt><dd>{item.runtime_evidence.source?.title ?? "—"}</dd></div></dl></section> : null}
        {item.accepted_deviation ? <section className="panel"><h2>{t("findings.acceptedDetails")}</h2><dl className="technical-list"><div><dt>{t("findings.rawStatus")}</dt><dd><StatusBadge status={item.raw_alignment ?? item.alignment} /></dd></div><div><dt>{t("findings.effectiveStatus")}</dt><dd><StatusBadge status={item.alignment} /></dd></div><div><dt>{t("findings.owner")}</dt><dd>{item.accepted_deviation.owner}</dd></div><div><dt>{t("findings.approver")}</dt><dd>{item.accepted_deviation.approver}</dd></div><div><dt>{t("findings.ticket")}</dt><dd>{item.accepted_deviation.ticket}</dd></div><div><dt>{t("findings.validity")}</dt><dd>{item.accepted_deviation.valid_from} – {item.accepted_deviation.valid_until}</dd></div><div><dt>{t("findings.daysRemaining")}</dt><dd>{deviationDays}</dd></div><div><dt>{t("findings.reason")}</dt><dd>{item.accepted_deviation.reason}</dd></div></dl></section> : null}
      </div>
      <section className="panel trace-panel"><h2>{t("findings.whyConclusion")}</h2><p>{t("findings.trace")}</p><ol className="trace-list">{item.decision_trace.map((step) => <li key={`${String(step.order)}-${step.gate}`}><span className={`trace-marker ${step.outcome === "fail" ? "trace-fail" : ""}`}>{step.outcome === "fail" ? <CircleHelp size={15} aria-hidden /> : <Check size={15} aria-hidden />}</span><div><strong>{step.gate.replaceAll("_", " ")}</strong><StatusBadge status={step.outcome} /><p>{localized(step.explanation, i18n.language)}</p></div></li>)}</ol></section>
      {mode === "expert" ? <section className="panel expert-panel"><h2>{t("policies.technical")}</h2><dl className="technical-list"><div><dt>{t("common.settingId")}</dt><dd><code>{item.setting_id}</code></dd></div><div><dt>{t("common.policyId")}</dt><dd><code>{item.policy_id}</code></dd></div><div><dt>{t("findings.rawStatus")}</dt><dd>{item.raw_alignment ?? item.alignment}</dd></div><div><dt>{t("findings.effectiveStatus")}</dt><dd>{item.alignment}</dd></div><div><dt>{t("findings.applicability")}</dt><dd>{item.applicability}</dd></div></dl></section> : null}
    </div>
  );
}
