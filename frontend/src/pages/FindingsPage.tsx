import type { ColumnDef } from "@tanstack/react-table";
import { ExternalLink, Filter } from "lucide-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import type { Finding } from "../api/client";
import { DataTable } from "../components/DataTable";
import { ErrorState, LoadingState } from "../components/QueryState";
import { StatusBadge } from "../components/StatusBadge";
import { displayValue, localized } from "../features/audit/format";
import { useFindings } from "../features/audit/hooks";

export function FindingsPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const { t, i18n } = useTranslation();
  const query = useFindings(auditId);
  const [filter, setFilter] = useState("all");
  const columns = useMemo<ColumnDef<Finding>[]>(() => {
    const items: ColumnDef<Finding>[] = [
      { header: t("findings.severity"), cell: ({ row }) => <StatusBadge status={row.original.severity} /> },
      { header: t("findings.type"), accessorFn: (row) => row.finding_type, cell: ({ getValue }) => String(getValue()).replaceAll("_", " ") },
      { header: t("findings.policy"), accessorKey: "policy_name" },
      { header: t("findings.setting"), cell: ({ row }) => <Link className="table-link" to={`/audit/${auditId}/findings/${row.original.finding_id}`}>{localized(row.original.setting_name, i18n.language)}<ExternalLink size={14} aria-hidden /></Link> },
      { header: t("findings.configured"), cell: ({ row }) => <code>{displayValue(row.original.configured_value)}</code> },
      { header: t("findings.selected"), cell: ({ row }) => <code>{displayValue(row.original.microsoft_value)}</code> },
      { header: t("findings.alignment"), cell: ({ row }) => <StatusBadge status={row.original.alignment} /> },
      { header: t("findings.confidence"), cell: ({ row }) => <StatusBadge status={row.original.evidence_confidence} /> },
      { header: t("findings.scope"), cell: ({ row }) => row.original.affected_device_count !== null && row.original.affected_device_count !== undefined ? String(row.original.affected_device_count) : row.original.assignments.map((assignment) => assignment.display_name ?? assignment.target_type).join(", ") || t("common.notAvailable") },
      { header: t("findings.deviation"), cell: ({ row }) => row.original.deviation_state ? <StatusBadge status={row.original.deviation_state} /> : "—" },
    ];
    if (filter === "not_evaluable") {
      items.push(
        { header: t("findings.reason"), cell: ({ row }) => localized(row.original.explanation, i18n.language) },
        { header: t("findings.availableEvidence"), cell: ({ row }) => row.original.evidence.map((source) => source.title).join(", ") || t("common.notAvailable") },
        { header: t("findings.missingEvidence"), cell: ({ row }) => (row.original.not_evaluable_reasons ?? []).map((reason) => t(`reasons.${reason}`, { defaultValue: reason.replaceAll("_", " ") })).join("; ") || t("common.notAvailable") },
        { header: t("findings.suggestedResolution"), cell: ({ row }) => localized(row.original.recommended_action, i18n.language) },
      );
    }
    return items;
  }, [auditId, filter, i18n.language, t]);
  if (query.isLoading) return <LoadingState />;
  if (query.isError || !query.data) return <ErrorState error={query.error} />;
  const options = ["all", "critical", "high", "medium", "low", "information", "not_evaluable"];
  const filtered = query.data.items.filter((item) => filter === "all" || (filter === "not_evaluable" ? item.alignment === "not_evaluable" : item.severity === filter));
  return <div className="content-page"><div className="page-heading"><div><p className="eyebrow">{t("findings.eyebrow")}</p><h1>{t("findings.title")}</h1><p className="page-intro">{t("findings.intro")}</p></div></div><label className="filter-control"><Filter size={17} aria-hidden /><span>{t("findings.filter")}</span><select value={filter} onChange={(event) => setFilter(event.target.value)}>{options.map((option) => <option key={option} value={option}>{option === "all" ? t("findings.all") : t(`status.${option}`)}</option>)}</select></label><DataTable data={filtered} columns={columns} label={t("findings.title")} /></div>;
}
