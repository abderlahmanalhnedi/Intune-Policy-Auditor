import type { ColumnDef } from "@tanstack/react-table";
import { ArrowLeft, CircleDot, ExternalLink } from "lucide-react";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import type { SettingEvaluation } from "../api/client";
import { usePreferences } from "../app/preferences";
import { DataTable } from "../components/DataTable";
import { ErrorState, LoadingState } from "../components/QueryState";
import { StatusBadge } from "../components/StatusBadge";
import { displayValue, localized } from "../features/audit/format";
import { useConflicts, usePolicy } from "../features/audit/hooks";

export function PolicyDetailPage() {
  const { auditId, policyId } = useParams<{ auditId: string; policyId: string }>();
  const { t, i18n } = useTranslation();
  const { mode } = usePreferences();
  const query = usePolicy(auditId, policyId);
  const conflictsQuery = useConflicts(auditId);
  const columns = useMemo<ColumnDef<SettingEvaluation>[]>(() => [
    { header: t("findings.alignment"), cell: ({ row }) => <StatusBadge status={row.original.effective_alignment_status} /> },
    { header: t("findings.setting"), accessorFn: (row) => row.observation.original_setting_id },
    { header: t("findings.configured"), cell: ({ row }) => <code>{displayValue(row.original.observation.canonical_value)}</code> },
    { header: t("findings.selected"), cell: ({ row }) => <code>{displayValue(row.original.microsoft_value)}</code> },
    { header: t("findings.confidence"), cell: ({ row }) => <StatusBadge status={row.original.evidence_confidence} /> },
  ], [t]);
  if (query.isLoading || conflictsQuery.isLoading) return <LoadingState />;
  if (query.isError || !query.data || conflictsQuery.isError || !conflictsQuery.data) {
    return <ErrorState error={query.error ?? conflictsQuery.error} />;
  }
  const data = query.data;
  const assignments = data.policy.assignments ?? [];
  const assignmentRisks = data.assignment_risks ?? [];
  const relatedConflicts = conflictsQuery.data.items.filter((conflict) => conflict.policy_a_id === policyId || conflict.policy_b_id === policyId);
  const filters = assignments.flatMap((assignment) => assignment.filter ? [assignment.filter] : []);
  const sources = data.settings.flatMap((item) => item.evidence ?? []).filter((source, index, all) => all.findIndex((candidate) => candidate.source_reference === source.source_reference) === index);
  const actions = [
    ...data.findings.map((finding) => localized(finding.recommended_action, i18n.language)),
    ...assignmentRisks.map((risk) => localized(risk.recommended_action, i18n.language)),
  ];
  return (
    <div className="content-page detail-page">
      <Link className="back-link" to={`/audit/${auditId}/policies`}><ArrowLeft size={16} aria-hidden />{t("navigation.policies")}</Link>
      <div className="page-heading"><div><p className="eyebrow">{t("policies.overview")}</p><h1>{data.policy.name}</h1><p className="page-intro">{data.policy.description}</p></div><StatusBadge status={data.runtime_evidence?.state ?? "unknown"} /></div>
      <section className="detail-summary"><div><span>{t("policies.platform")}</span><strong>{data.policy.platform}</strong></div><div><span>{t("policies.kind")}</span><strong>{data.policy.kind.replaceAll("_", " ")}</strong></div><div><span>{t("policies.settings")}</span><strong>{data.settings.length}</strong></div><div><span>{t("policies.assignments")}</span><strong>{assignments.length}</strong></div></section>
      <section className="panel"><h2>{t("policies.comparison")}</h2><DataTable data={data.settings} columns={columns} label={t("policies.comparison")} pageSize={20} /></section>
      <div className="detail-grid">
        <section className="panel"><h2>{t("policies.assignments")}</h2>{assignments.length ? <ul className="plain-list">{assignments.map((assignment, index) => <li key={`${assignment.target_id ?? assignment.target_type}-${String(index)}`}><CircleDot size={15} aria-hidden /><span><strong>{assignment.display_name ?? assignment.target_type}</strong><small>{assignment.scope}{assignment.filter ? ` · ${assignment.filter.mode} ${t("common.filter")}` : ""}</small></span></li>)}</ul> : <p>{t("common.noResults")}</p>}</section>
        <section className="panel"><h2>{t("common.filter")}</h2>{filters.length ? <ul className="plain-list">{filters.map((filter, index) => <li key={`${filter.filter_id ?? "filter"}-${String(index)}`}><span><strong>{filter.display_name ?? filter.filter_id ?? t("common.notAvailable")}</strong><small>{filter.mode} · {filter.platform} · {filter.definition_available ? t("common.yes") : t("common.no")}</small></span></li>)}</ul> : <p>{t("common.noResults")}</p>}</section>
        <section className="panel"><h2>{t("policies.assignmentRisks")}</h2>{assignmentRisks.length ? <ul className="plain-list">{assignmentRisks.map((risk) => <li key={risk.risk_id}><StatusBadge status={risk.severity} /><span><strong>{risk.risk_type.replaceAll("_", " ")}</strong><small>{localized(risk.explanation, i18n.language)}</small></span></li>)}</ul> : <p>{t("common.noResults")}</p>}</section>
        <section className="panel"><h2>{t("policies.conflicts")}</h2>{relatedConflicts.length ? <ul className="plain-list">{relatedConflicts.map((conflict) => <li key={conflict.conflict_id}><StatusBadge status={conflict.classification} /><span><strong>{conflict.policy_a_name} ↔ {conflict.policy_b_name}</strong><small>{localized(conflict.reasoning, i18n.language)}</small></span></li>)}</ul> : <p>{t("common.noResults")}</p>}</section>
        <section className="panel"><h2>{t("findings.next")}</h2>{actions.length ? <ul>{actions.map((action, index) => <li key={`${action}-${String(index)}`}>{action}</li>)}</ul> : <p>{t("common.noResults")}</p>}</section>
        <section className="panel"><h2>{t("findings.pilot")}</h2>{data.findings.length ? <ul>{data.findings.map((finding) => <li key={finding.finding_id}>{localized(finding.pilot_suggestion, i18n.language)}</li>)}</ul> : <p>{t("common.noResults")}</p>}</section>
        <section className="panel"><h2>{t("findings.rollback")}</h2>{data.findings.length ? <ul>{data.findings.map((finding) => <li key={finding.finding_id}>{localized(finding.rollback_suggestion, i18n.language)}</li>)}</ul> : <p>{t("common.noResults")}</p>}</section>
        {data.runtime_evidence ? <section className="panel"><h2>{t("findings.runtimeEvidence")}</h2><dl className="technical-list"><div><dt>{t("tenant.state")}</dt><dd><StatusBadge status={data.runtime_evidence.state} /></dd></div><div><dt>{t("findings.targeted")}</dt><dd>{data.runtime_evidence.targeted_count ?? "—"}</dd></div><div><dt>{t("findings.succeeded")}</dt><dd>{data.runtime_evidence.success_count ?? "—"}</dd></div><div><dt>{t("findings.errors")}</dt><dd>{data.runtime_evidence.error_count ?? "—"}</dd></div><div><dt>{t("findings.runtimeConflicts")}</dt><dd>{data.runtime_evidence.conflict_count ?? "—"}</dd></div><div><dt>{t("findings.pending")}</dt><dd>{data.runtime_evidence.pending_count ?? "—"}</dd></div><div><dt>{t("findings.apiVersion")}</dt><dd>{data.runtime_evidence.api_version ?? "—"}</dd></div></dl></section> : null}
        <section className="panel"><h2>{t("policies.sources")}</h2>{sources.length ? sources.map((source, index) => source.source_reference.startsWith("https://") ? <a className="source-link" href={source.source_reference} key={`${source.title}-${String(index)}`} rel="noreferrer" target="_blank">{source.title}<ExternalLink size={14} aria-hidden /></a> : <p key={`${source.title}-${String(index)}`}><strong>{source.title}</strong><br /><code>{source.source_reference}</code></p>) : <p>{t("common.notAvailable")}</p>}</section>
      </div>
      {mode === "expert" ? <section className="panel expert-panel"><h2>{t("policies.technical")}</h2><dl className="technical-list"><div><dt>{t("common.policyId")}</dt><dd><code>{data.policy.policy_id}</code></dd></div><div><dt>{t("common.source")}</dt><dd>{data.policy.source.filename}</dd></div><div><dt>SHA-256</dt><dd><code>{data.policy.source.sha256}</code></dd></div></dl></section> : null}
    </div>
  );
}
