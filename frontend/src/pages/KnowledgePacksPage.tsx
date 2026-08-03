import type { ColumnDef } from "@tanstack/react-table";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Box, Download, ExternalLink, Power, Trash2, Upload } from "lucide-react";
import { useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  getKnowledgePacks,
  importKnowledgePack,
  removeKnowledgePack,
  setKnowledgePackActive,
  validateKnowledgePack,
  type KnowledgePackSummary,
} from "../api/client";
import { DataTable } from "../components/DataTable";
import { ErrorState, LoadingState } from "../components/QueryState";
import { StatusBadge } from "../components/StatusBadge";

export function KnowledgePacksPage() {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const input = useRef<HTMLInputElement>(null);
  const validationInput = useRef<HTMLInputElement>(null);
  const [message, setMessage] = useState<string | null>(null);
  const query = useQuery({ queryKey: ["knowledge-packs"], queryFn: getKnowledgePacks });
  const refresh = async () => queryClient.invalidateQueries({ queryKey: ["knowledge-packs"] });
  const importMutation = useMutation({
    mutationFn: async (file: File) => {
      const validation = await validateKnowledgePack(file);
      if (!validation.valid) throw new Error(t("knowledge.invalid"));
      return importKnowledgePack(file);
    },
    onSuccess: async () => { setMessage(t("knowledge.imported")); await refresh(); },
    onError: (error) => setMessage(error instanceof Error ? error.message : t("common.unknownError")),
  });
  const validationMutation = useMutation({
    mutationFn: validateKnowledgePack,
    onSuccess: (report) => setMessage(report.valid ? t("knowledge.validationPassed") : t("knowledge.validationFailed")),
    onError: (error) => setMessage(error instanceof Error ? error.message : t("common.unknownError")),
  });
  const stateMutation = useMutation({
    mutationFn: ({ packId, active }: { packId: string; active: boolean }) => setKnowledgePackActive(packId, active),
    onSuccess: refresh,
    onError: (error) => setMessage(error instanceof Error ? error.message : t("common.unknownError")),
  });
  const removeMutation = useMutation({
    mutationFn: removeKnowledgePack,
    onSuccess: refresh,
    onError: (error) => setMessage(error instanceof Error ? error.message : t("common.unknownError")),
  });
  const columns = useMemo<ColumnDef<KnowledgePackSummary>[]>(() => [
    { header: t("knowledge.name"), cell: ({ row }) => <div className="pack-name"><Box size={18} aria-hidden /><span><strong>{row.original.name}</strong><small>{row.original.product}</small></span></div> },
    { header: t("knowledge.vendor"), accessorKey: "vendor" },
    { header: t("knowledge.version"), accessorKey: "version" },
    { header: t("knowledge.platform"), accessorKey: "platform" },
    { header: t("knowledge.status"), cell: ({ row }) => <StatusBadge status={row.original.status} /> },
    { header: t("knowledge.verified"), cell: ({ row }) => new Intl.DateTimeFormat(i18n.language, { dateStyle: "medium" }).format(new Date(`${row.original.verification_date}T00:00:00`)) },
    { header: t("knowledge.source"), cell: ({ row }) => row.original.source.startsWith("https://") ? <a className="source-link table-source-link" href={row.original.source} rel="noreferrer" target="_blank">{row.original.source}<ExternalLink size={14} aria-hidden /></a> : <code title={row.original.source}>{row.original.source}</code> },
    { header: t("knowledge.hash"), cell: ({ row }) => <code title={row.original.data_sha256}>{row.original.data_sha256.slice(0, 12)}…</code> },
    { header: t("knowledge.settings"), accessorKey: "setting_count" },
    { header: t("knowledge.exact"), accessorKey: "exact_value_count" },
    { header: t("knowledge.freshness"), cell: ({ row }) => <span>{t("knowledge.days", { count: row.original.age_days })}{row.original.stale ? <AlertTriangle size={14} aria-label={t("knowledge.stale")} /> : null}</span> },
    { header: t("knowledge.validation"), cell: ({ row }) => <StatusBadge status={row.original.validation_state} /> },
    { header: t("knowledge.active"), cell: ({ row }) => <button className="icon-action" type="button" aria-label={row.original.active ? t("knowledge.deactivate") : t("knowledge.activate")} onClick={() => stateMutation.mutate({ packId: row.original.pack_id, active: !row.original.active })}><Power size={17} aria-hidden />{row.original.active ? t("common.yes") : t("common.no")}</button> },
    { header: t("knowledge.actions"), cell: ({ row }) => <div className="table-actions"><a className="icon-action" href={`/api/v1/knowledge-packs/${encodeURIComponent(row.original.pack_id)}/provenance`} rel="noreferrer" target="_blank"><ExternalLink size={16} aria-hidden />{t("knowledge.provenance")}</a><a className="icon-action" href={`/api/v1/knowledge-packs/${encodeURIComponent(row.original.pack_id)}/validation-report`} download><Download size={16} aria-hidden />{t("knowledge.validation")}</a>{!row.original.synthetic ? <button className="icon-action danger-action" type="button" onClick={() => { if (window.confirm(t("knowledge.removeConfirm"))) removeMutation.mutate(row.original.pack_id); }}><Trash2 size={16} aria-hidden />{t("knowledge.remove")}</button> : null}</div> },
  ], [i18n.language, removeMutation, stateMutation, t]);
  if (query.isLoading) return <LoadingState />;
  if (query.isError || !query.data) return <ErrorState error={query.error} />;
  return <div className="content-page"><div className="page-heading"><div><p className="eyebrow">{t("knowledge.eyebrow")}</p><h1>{t("knowledge.title")}</h1><p className="page-intro">{t("knowledge.intro")}</p></div><div className="action-row"><button className="secondary-action" type="button" disabled={validationMutation.isPending} onClick={() => validationInput.current?.click()}><Download size={17} aria-hidden />{t("knowledge.validate")}</button><input ref={validationInput} className="sr-only" type="file" accept=".zip,application/zip" onChange={(event) => { const file = event.target.files?.[0]; if (file) validationMutation.mutate(file); event.target.value = ""; }} /><button className="secondary-action" type="button" disabled={importMutation.isPending} onClick={() => input.current?.click()}><Upload size={17} aria-hidden />{t("knowledge.import")}</button><input ref={input} className="sr-only" type="file" accept=".zip,application/zip" onChange={(event) => { const file = event.target.files?.[0]; if (file) importMutation.mutate(file); event.target.value = ""; }} /></div></div>{message ? <div className="inline-notice" role="status">{message}</div> : null}<div className="synthetic-banner"><AlertTriangle size={18} aria-hidden /><strong>{t("knowledge.syntheticWarning")}</strong></div><DataTable data={query.data} columns={columns} label={t("knowledge.title")} /><section className="panel official-empty"><Box size={24} aria-hidden /><div><h2>{t("knowledge.officialMissing")}</h2><p>{t("knowledge.officialMissingBody")}</p></div></section></div>;
}
