import { AlertTriangle, ArrowRight, FileSearch, Layers3, Network, ShieldCheck } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { ErrorState, LoadingState } from "../components/QueryState";
import { StatusBadge } from "../components/StatusBadge";
import { localized, percent } from "../features/audit/format";
import { useDashboard } from "../features/audit/hooks";

export function DashboardPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const { t, i18n } = useTranslation();
  const query = useDashboard(auditId);
  if (query.isLoading) return <LoadingState />;
  if (query.isError || !query.data) return <ErrorState error={query.error} />;
  const data = query.data;
  const alignmentData = Object.entries(data.alignment_counts).filter(([, value]) => value > 0).map(([name, value]) => ({ name: t(`status.${name}`, { defaultValue: name }), value }));
  const severityData = Object.entries(data.severity_counts).filter(([, value]) => value > 0).map(([name, value]) => ({ name: t(`status.${name}`, { defaultValue: name }), value }));
  const policyHealthData = Object.entries(data.policy_health_counts).filter(([, value]) => value > 0).map(([name, value]) => ({
    name: t(name === "aligned" ? "dashboard.healthAligned" : name === "review" ? "dashboard.healthReview" : name === "action_required" ? "dashboard.healthAction" : "dashboard.healthInsufficient"),
    value,
  }));
  const notEvaluableReasons = Object.entries(data.not_evaluable_reasons).sort((left, right) => right[1] - left[1]);
  const metrics = [
    { label: t("dashboard.policies"), value: data.policy_count, icon: FileSearch },
    { label: t("dashboard.settings"), value: data.setting_count, icon: Layers3 },
    { label: t("dashboard.evaluable"), value: data.evaluable_count, icon: ShieldCheck, tone: "success" },
    { label: t("dashboard.notEvaluable"), value: data.not_evaluable_count, icon: AlertTriangle, tone: "unknown" },
    { label: t("dashboard.confirmedIssues"), value: data.confirmed_issues, icon: AlertTriangle, tone: data.confirmed_issues ? "danger" : "success" },
    { label: t("dashboard.conflicts"), value: data.confirmed_conflicts, icon: Network, tone: data.confirmed_conflicts ? "danger" : "success" },
    { label: t("dashboard.exactCoverage"), value: percent(data.exact_evidence_coverage, i18n.language, t), icon: ShieldCheck },
    { label: t("dashboard.assignmentCoverage"), value: percent(data.assignment_analysis_coverage, i18n.language, t), icon: Network },
    ...(data.runtime_success_rate === null ? [] : [{ label: t("dashboard.runtimeSuccess"), value: percent(data.runtime_success_rate, i18n.language, t), icon: ShieldCheck, tone: "success" }]),
  ];
  return (
    <div className="content-page dashboard-page">
      {data.is_synthetic ? <div className="synthetic-banner"><AlertTriangle size={18} aria-hidden /><strong>{t("app.synthetic")}</strong></div> : null}
      <div className="page-heading"><div><p className="eyebrow">{t("dashboard.eyebrow")}</p><h1>{t("dashboard.title")}</h1></div><Link className="secondary-action" to="/audit/new">{t("foundation.start")}</Link></div>
      <section className="decision-panel">
        <div><div className="badge-row"><StatusBadge status={data.decision} /><span>{t("dashboard.evidenceBadge")}:</span><StatusBadge status={data.evidence_quality} /></div><h2>{localized(data.reason, i18n.language)}</h2><p>{t("dashboard.uncertainty")}</p></div>
        <div className="next-action"><span>{t("dashboard.nextAction")}</span><strong>{localized(data.next_action, i18n.language)}</strong></div>
      </section>
      <section className="metric-grid" aria-label={t("dashboard.evidence")}>{metrics.map((metric) => <article className={`metric-card ${metric.tone ? `metric-${metric.tone}` : ""}`} key={metric.label}><span><metric.icon size={18} aria-hidden />{metric.label}</span><strong>{metric.value}</strong></article>)}</section>
      <div className="dashboard-grid">
        <section className="panel chart-panel"><h2>{t("dashboard.alignment")}</h2><p className="chart-alternative sr-only">{alignmentData.map((item) => `${item.name}: ${String(item.value)}`).join(", ")}</p><div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><BarChart data={alignmentData} layout="vertical" margin={{ left: 12, right: 20 }}><CartesianGrid strokeDasharray="3 3" horizontal={false} opacity={0.25} /><XAxis type="number" allowDecimals={false} /><YAxis type="category" dataKey="name" width={128} tick={{ fontSize: 11 }} /><Tooltip /><Bar dataKey="value" fill="#4f46e5" radius={[0, 5, 5, 0]} /></BarChart></ResponsiveContainer></div></section>
        <section className="panel chart-panel"><h2>{t("dashboard.severity")}</h2><p className="chart-alternative sr-only">{severityData.map((item) => `${item.name}: ${String(item.value)}`).join(", ")}</p><div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><BarChart data={severityData} margin={{ left: 0, right: 12 }}><CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.25} /><XAxis dataKey="name" tick={{ fontSize: 11 }} /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="value" fill="#0891b2" radius={[5, 5, 0, 0]} /></BarChart></ResponsiveContainer></div></section>
        <section className="panel chart-panel"><h2>{t("dashboard.policyHealth")}</h2><p className="chart-alternative sr-only">{policyHealthData.map((item) => `${item.name}: ${String(item.value)}`).join(", ")}</p><div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><BarChart data={policyHealthData} layout="vertical" margin={{ left: 12, right: 20 }}><CartesianGrid strokeDasharray="3 3" horizontal={false} opacity={0.25} /><XAxis type="number" allowDecimals={false} /><YAxis type="category" dataKey="name" width={128} tick={{ fontSize: 11 }} /><Tooltip /><Bar dataKey="value" fill="#7c3aed" radius={[0, 5, 5, 0]} /></BarChart></ResponsiveContainer></div></section>
      </div>
      <section className="panel action-panel"><h2>{t("dashboard.notEvaluableSummary")}</h2>{notEvaluableReasons.length ? <ul className="reason-summary">{notEvaluableReasons.map(([reason, count]) => <li key={reason}><span>{t(`reasons.${reason}`, { defaultValue: reason.replaceAll("_", " ") })}</span><strong>{count}</strong></li>)}</ul> : <p>{t("common.noResults")}</p>}</section>
      <section className="panel action-panel"><h2>{t("dashboard.topActions")}</h2>{data.top_actions.length ? <ol className="action-list">{data.top_actions.map((finding) => <li key={finding.finding_id}><StatusBadge status={finding.severity} /><div><strong>{localized(finding.title, i18n.language)}</strong><span>{finding.policy_name}</span></div><Link to={`/audit/${auditId}/findings/${finding.finding_id}`} aria-label={t("common.details")}><ArrowRight size={18} aria-hidden /></Link></li>)}</ol> : <p>{t("dashboard.noActions")}</p>}</section>
    </div>
  );
}
