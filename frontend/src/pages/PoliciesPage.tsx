import type { ColumnDef } from "@tanstack/react-table";
import { ExternalLink, Filter, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import type { PolicyEvaluation } from "../api/client";
import { DataTable } from "../components/DataTable";
import { ErrorState, LoadingState } from "../components/QueryState";
import { StatusBadge } from "../components/StatusBadge";
import { dominantAlignment, percent } from "../features/audit/format";
import { useAudit, usePolicies } from "../features/audit/hooks";

export function PoliciesPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const { t, i18n } = useTranslation();
  const query = usePolicies(auditId);
  const auditQuery = useAudit(auditId);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const columns = useMemo<ColumnDef<PolicyEvaluation>[]>(() => [
    { id: "status", header: t("policies.status"), cell: ({ row }) => <StatusBadge status={dominantAlignment(row.original.settings.map((item) => item.effective_alignment_status))} /> },
    { accessorFn: (row) => row.policy.name, id: "name", header: t("policies.name"), cell: ({ row }) => <Link className="table-link" to={`/audit/${auditId}/policies/${row.original.policy.policy_id}`}>{row.original.policy.name}<ExternalLink size={14} aria-hidden /></Link> },
    { accessorFn: (row) => row.policy.platform, id: "platform", header: t("policies.platform") },
    { accessorFn: (row) => row.policy.kind, id: "kind", header: t("policies.kind"), cell: ({ getValue }) => String(getValue()).replaceAll("_", " ") },
    { id: "assignments", header: t("policies.assignments"), cell: ({ row }) => row.original.policy.assignments?.length ?? 0 },
    { id: "settings", header: t("policies.settings"), cell: ({ row }) => row.original.settings.length },
    { id: "evidence", header: t("policies.evidence"), cell: ({ row }) => percent(row.original.settings.length ? row.original.settings.filter((item) => item.evidence_confidence === "exact").length / row.original.settings.length : null, i18n.language, t) },
    { id: "findings", header: t("policies.findings"), cell: ({ row }) => row.original.findings.length },
    { id: "conflicts", header: t("policies.conflicts"), cell: ({ row }) => auditQuery.data?.conflicts.filter((item) => item.policy_a_id === row.original.policy.policy_id || item.policy_b_id === row.original.policy.policy_id).length ?? "—" },
    { id: "runtime", header: t("policies.runtime"), cell: ({ row }) => <StatusBadge status={row.original.runtime_evidence?.state ?? "unknown"} /> },
  ], [auditId, auditQuery.data?.conflicts, i18n.language, t]);
  if (query.isLoading) return <LoadingState />;
  if (query.isError || !query.data) return <ErrorState error={query.error} />;
  const statuses = Array.from(new Set(query.data.items.map((item) => dominantAlignment(item.settings.map((setting) => setting.effective_alignment_status))))).sort();
  const filtered = query.data.items.filter((item) => item.policy.name.toLowerCase().includes(search.toLowerCase()) && (status === "all" || dominantAlignment(item.settings.map((setting) => setting.effective_alignment_status)) === status));
  return <div className="content-page"><div className="page-heading"><div><p className="eyebrow">{t("policies.eyebrow")}</p><h1>{t("policies.title")}</h1><p className="page-intro">{t("policies.intro")}</p></div></div><div className="table-toolbar"><label className="search-field"><Search size={18} aria-hidden /><span className="sr-only">{t("policies.search")}</span><input type="search" value={search} placeholder={t("policies.search")} onChange={(event) => setSearch(event.target.value)} /></label><label className="filter-control"><Filter size={17} aria-hidden /><span>{t("policies.status")}</span><select value={status} onChange={(event) => setStatus(event.target.value)}><option value="all">{t("findings.all")}</option>{statuses.map((option) => <option key={option} value={option}>{t(`status.${option}`, { defaultValue: option })}</option>)}</select></label></div><DataTable data={filtered} columns={columns} label={t("policies.title")} /></div>;
}
