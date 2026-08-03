import type { ColumnDef } from "@tanstack/react-table";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import type { ConflictResult } from "../api/client";
import { DataTable } from "../components/DataTable";
import { ErrorState, LoadingState } from "../components/QueryState";
import { StatusBadge } from "../components/StatusBadge";
import { displayValue, localized } from "../features/audit/format";
import { useConflicts } from "../features/audit/hooks";

export function ConflictsPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const { t, i18n } = useTranslation();
  const query = useConflicts(auditId);
  const columns = useMemo<ColumnDef<ConflictResult>[]>(() => [
    { header: t("conflicts.class"), cell: ({ row }) => <StatusBadge status={row.original.classification} /> },
    { header: t("conflicts.confidence"), cell: ({ row }) => <StatusBadge status={row.original.confidence} /> },
    { header: t("conflicts.setting"), accessorKey: "canonical_setting_id", cell: ({ getValue }) => <code>{String(getValue())}</code> },
    { header: t("conflicts.policyA"), accessorKey: "policy_a_name" },
    { header: t("conflicts.valueA"), cell: ({ row }) => <code>{displayValue(row.original.policy_a_value)}</code> },
    { header: t("conflicts.assignmentsA"), cell: ({ row }) => row.original.assignments_a.map((assignment) => `${assignment.display_name ?? assignment.target_type}${assignment.filter ? ` (${assignment.filter.mode}: ${assignment.filter.display_name ?? assignment.filter.filter_id ?? t("common.notAvailable")})` : ""}`).join("; ") || t("common.notAvailable") },
    { header: t("conflicts.policyB"), accessorKey: "policy_b_name" },
    { header: t("conflicts.valueB"), cell: ({ row }) => <code>{displayValue(row.original.policy_b_value)}</code> },
    { header: t("conflicts.assignmentsB"), cell: ({ row }) => row.original.assignments_b.map((assignment) => `${assignment.display_name ?? assignment.target_type}${assignment.filter ? ` (${assignment.filter.mode}: ${assignment.filter.display_name ?? assignment.filter.filter_id ?? t("common.notAvailable")})` : ""}`).join("; ") || t("common.notAvailable") },
    { header: t("conflicts.overlap"), cell: ({ row }) => <div className="reason-cell"><strong>{row.original.overlap_result.replaceAll("_", " ")}</strong><span>{localized(row.original.reasoning, i18n.language)}</span></div> },
    { header: t("conflicts.affectedDevices"), cell: ({ row }) => row.original.affected_device_count ?? t("common.notAvailable") },
    { header: t("conflicts.action"), cell: ({ row }) => localized(row.original.recommended_action, i18n.language) },
  ], [i18n.language, t]);
  if (query.isLoading) return <LoadingState />;
  if (query.isError || !query.data) return <ErrorState error={query.error} />;
  const groups = ["confirmed", "probable", "possible", "none"] as const;
  return <div className="content-page"><div className="page-heading"><div><p className="eyebrow">{t("conflicts.eyebrow")}</p><h1>{t("conflicts.title")}</h1><p className="page-intro">{t("conflicts.intro")}</p></div></div><div className="conflict-summary">{groups.map((group) => <div key={group}><StatusBadge status={group} /><strong>{query.data.items.filter((item) => item.confidence === group).length}</strong></div>)}</div><DataTable data={query.data.items} columns={columns} label={t("conflicts.title")} /></div>;
}
