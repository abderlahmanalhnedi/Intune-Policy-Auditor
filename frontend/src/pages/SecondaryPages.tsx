import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Bot, Database, KeyRound, LockKeyhole, ShieldCheck } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import {
  beginDeviceCode,
  clearTemporaryFiles,
  clearTokenCache,
  completeDeviceCode,
  deleteLocalAuditData,
  getSettings,
  getTenantStatus,
  resetSettings,
  signOutTenant,
  updateSettings,
  type DeviceCodePrompt,
  type LocalPreferences,
} from "../api/client";
import { ErrorState, LoadingState } from "../components/QueryState";

export function TenantPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const status = useQuery({ queryKey: ["tenant-status"], queryFn: getTenantStatus });
  const [prompt, setPrompt] = useState<DeviceCodePrompt | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const begin = useMutation({ mutationFn: beginDeviceCode, onSuccess: setPrompt, onError: (error) => setMessage(error instanceof Error ? error.message : t("common.unknownError")) });
  const complete = useMutation({ mutationFn: completeDeviceCode, onSuccess: async () => { setPrompt(null); setMessage(t("tenant.connected")); await queryClient.invalidateQueries({ queryKey: ["tenant-status"] }); }, onError: (error) => setMessage(error instanceof Error ? error.message : t("common.unknownError")) });
  const signout = useMutation({ mutationFn: signOutTenant, onSuccess: async () => { setPrompt(null); setMessage(t("tenant.signedOut")); await queryClient.invalidateQueries({ queryKey: ["tenant-status"] }); } });
  if (status.isLoading) return <LoadingState />;
  if (status.isError || !status.data) return <ErrorState error={status.error} />;
  return <Page eyebrow="tenant.eyebrow" title="tenant.title"><div className="synthetic-banner"><AlertTriangle size={18} aria-hidden /><strong>{t("tenant.warning")}</strong></div><p className="page-intro">{t("tenant.body")}</p><section className="panel permission-card"><KeyRound aria-hidden /><div><span>{t("tenant.permission")}</span><code>DeviceManagementConfiguration.Read.All</code><small>{t("tenant.state")}: {status.data.authenticated ? t("tenant.authenticated") : status.data.configured ? t("tenant.ready") : t("tenant.unconfigured")}</small></div></section>{Object.values(status.data.operations).includes("beta") ? <div className="inline-notice"><AlertTriangle size={16} aria-hidden />{t("tenant.betaWarning")}</div> : null}{prompt ? <section className="panel device-code-panel"><h2>{t("tenant.deviceCode")}</h2><strong className="device-code">{prompt.user_code}</strong><p>{prompt.message}</p><a className="secondary-action" href={prompt.verification_uri} target="_blank" rel="noreferrer">{t("tenant.openLogin")}</a><button className="primary-action" type="button" disabled={complete.isPending} onClick={() => complete.mutate(prompt.flow_id)}>{t("tenant.complete")}</button></section> : null}{message ? <div className="inline-notice" role="status">{message}</div> : null}<div className="action-row"><button className="primary-action" type="button" disabled={!status.data.configured || status.data.authenticated || begin.isPending} onClick={() => begin.mutate()}>{t("tenant.connect")}</button><button className="secondary-action" disabled={!status.data.authenticated || signout.isPending} type="button" onClick={() => signout.mutate()}>{t("tenant.signout")}</button></div></Page>;
}

export function SettingsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["settings"], queryFn: getSettings });
  const [preferences, setPreferences] = useState<LocalPreferences | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => { if (query.data) setPreferences({ history_enabled: query.data.history_enabled, retention_days: query.data.retention_days, save_reports: query.data.save_reports, automatic_cleanup: query.data.automatic_cleanup }); }, [query.data]);
  const save = useMutation({ mutationFn: updateSettings, onSuccess: async () => { setMessage(t("settingsPage.saved")); await queryClient.invalidateQueries({ queryKey: ["settings"] }); }, onError: (error) => setMessage(error instanceof Error ? error.message : t("common.unknownError")) });
  const action = useMutation({ mutationFn: async (name: "delete" | "temporary" | "tokens" | "reset") => { if (name === "delete") await deleteLocalAuditData(); if (name === "temporary") await clearTemporaryFiles(); if (name === "tokens") await clearTokenCache(); if (name === "reset") await resetSettings(); return name; }, onSuccess: async (name) => { setMessage(t(`settingsPage.${name}Done`)); await queryClient.invalidateQueries({ queryKey: ["settings"] }); } });
  if (query.isLoading || !preferences) return <LoadingState />;
  if (query.isError) return <ErrorState error={query.error} />;
  return <Page eyebrow="settingsPage.eyebrow" title="settingsPage.title"><section className="settings-section"><h2><LockKeyhole size={20} aria-hidden />{t("settingsPage.privacy")}</h2><label><input type="checkbox" checked={preferences.history_enabled} onChange={(event) => setPreferences({ ...preferences, history_enabled: event.target.checked })} />{t("settingsPage.history")}</label><label className="number-field"><span>{t("settingsPage.retention")}</span><input type="number" min={1} max={3650} value={preferences.retention_days} onChange={(event) => setPreferences({ ...preferences, retention_days: Number(event.target.value) })} /></label><label><input type="checkbox" checked={preferences.save_reports} onChange={(event) => setPreferences({ ...preferences, save_reports: event.target.checked })} />{t("settingsPage.reports")}</label><label><input type="checkbox" checked={preferences.automatic_cleanup} onChange={(event) => setPreferences({ ...preferences, automatic_cleanup: event.target.checked })} />{t("settingsPage.cleanup")}</label><p>{t("settingsPage.theme")}</p><div className="action-row"><button type="button" className="primary-action" disabled={save.isPending} onClick={() => save.mutate(preferences)}>{t("settingsPage.save")}</button><button type="button" className="secondary-action" onClick={() => action.mutate("temporary")}>{t("settingsPage.clearTemporary")}</button><button type="button" className="secondary-action" onClick={() => action.mutate("tokens")}>{t("settingsPage.clearTokens")}</button><button type="button" className="secondary-action danger-action" onClick={() => { if (window.confirm(t("settingsPage.deleteConfirm"))) action.mutate("delete"); }}><Database size={17} aria-hidden />{t("settingsPage.delete")}</button><button type="button" className="secondary-action" onClick={() => action.mutate("reset")}>{t("settingsPage.reset")}</button></div>{message ? <div className="inline-notice" role="status">{message}</div> : null}</section><section className="settings-section"><h2><Bot size={20} aria-hidden />{t("settingsPage.advanced")}</h2><h3>{t("settingsPage.ai")}</h3><p>{t("settingsPage.aiBody")}</p><span className="status-badge status-info">{t("common.planned")}</span></section></Page>;
}

export function HelpPage() { const { t } = useTranslation(); const cards: Array<[string, string]> = [["help.intune", "help.intuneBody"], ["help.evidence", "help.evidenceBody"], ["help.safe", "help.safeBody"]]; return <Page eyebrow="help.eyebrow" title="help.title"><div className="help-grid">{cards.map(([title, body]) => <article className="panel" key={title}><ShieldCheck size={21} aria-hidden /><h2>{t(title)}</h2><p>{t(body)}</p></article>)}</div></Page>; }
export function AboutPage() { const { t } = useTranslation(); return <Page eyebrow="about.eyebrow" title="about.title"><section className="panel about-panel"><ShieldCheck size={32} aria-hidden /><p>{t("about.body")}</p><strong>{t("about.disclaimer")}</strong><p>{t("about.limits")}</p></section></Page>; }
function Page({ eyebrow, title, children }: { eyebrow: string; title: string; children: ReactNode }) { const { t } = useTranslation(); return <div className="content-page compact-page"><p className="eyebrow">{t(eyebrow)}</p><h1>{t(title)}</h1>{children}</div>; }
