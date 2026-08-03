import { ArrowLeft, ArrowRight, Check, Cloud, FileArchive, Files, FlaskConical, LockKeyhole, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { Link, useHistory } from "react-router-dom";
import { z } from "zod";

import { ApiError, createDemoAudit, createOfflineAudit, getKnowledgePacks, previewOfflineAudit, type AuditPreview } from "../api/client";
import { usePreferences } from "../app/preferences";

const contextSchema = z.object({ physical: z.boolean(), vdi: z.boolean(), shared: z.boolean(), pilot: z.string().max(500), notes: z.string().max(2000) });
type ContextForm = z.infer<typeof contextSchema>;
interface DisplayError { title: string; text: string; technicalCode?: string }

export function NewAuditPage() {
  const { t } = useTranslation();
  const { language, mode } = usePreferences();
  const history = useHistory();
  const [step, setStep] = useState(1);
  const [files, setFiles] = useState<File[]>([]);
  const [deviation, setDeviation] = useState<File | undefined>();
  const [requirements, setRequirements] = useState<File | undefined>();
  const [preview, setPreview] = useState<AuditPreview | null>(null);
  const [error, setError] = useState<DisplayError | null>(null);
  const [working, setWorking] = useState(false);
  const packs = useQuery({ queryKey: ["knowledge-packs"], queryFn: getKnowledgePacks });
  const availablePacks = (packs.data ?? []).filter((pack) => pack.active);
  const [selectedPackId, setSelectedPackId] = useState("synthetic.test-baseline");
  const form = useForm<ContextForm>({ defaultValues: { physical: true, vdi: false, shared: false, pilot: "", notes: "" } });
  const displayError = (reason: unknown, upload: boolean): DisplayError => {
    if (upload && reason instanceof ApiError && reason.status === 422) {
      return { title: t("newAudit.uploadReadErrorTitle"), text: t("newAudit.uploadReadErrorText"), technicalCode: reason.code };
    }
    if (reason instanceof ApiError && reason.code) {
      return { title: t("common.error"), text: t("common.unknownError"), technicalCode: reason.code };
    }
    return { title: t("common.error"), text: reason instanceof Error ? reason.message : t("common.unknownError"), technicalCode: reason instanceof ApiError ? reason.code : undefined };
  };

  const startDemo = async () => {
    setWorking(true); setError(null);
    try { const audit = await createDemoAudit(language); history.push(`/audit/${audit.audit_id}/dashboard`); }
    catch (reason) { setError(displayError(reason, false)); setWorking(false); }
  };
  const inspectFiles = async () => {
    if (!files.length) { setError({ title: t("common.error"), text: t("newAudit.fileRequired") }); return; }
    setWorking(true); setError(null);
    try { setPreview(await previewOfflineAudit(files)); setStep(2); }
    catch (reason) { setError(displayError(reason, true)); }
    finally { setWorking(false); }
  };
  const startUpload = form.handleSubmit(async (values) => {
    if (!contextSchema.safeParse(values).success || files.length === 0) { setError({ title: t("common.error"), text: t("newAudit.fileRequired") }); return; }
    setWorking(true); setError(null);
    try { const audit = await createOfflineAudit(files, language, selectedPackId ? [selectedPackId] : [], { physical_device: values.physical, vdi: values.vdi, shared_device: values.shared, pilot_context: values.pilot, environment_notes: values.notes }, deviation, requirements); history.push(`/audit/${audit.audit_id}/dashboard`); }
    catch (reason) { setError(displayError(reason, true)); setWorking(false); }
  });

  return <div className="content-page wizard-page"><p className="eyebrow">{t("newAudit.eyebrow")}</p><h1>{t("newAudit.title")}</h1><p className="page-intro">{t("newAudit.description")}</p><ol className="wizard-progress"><li className={step >= 1 ? "active" : ""}><span>{step > 1 ? <Check size={15} aria-hidden /> : "1"}</span>{t("newAudit.stepSource")}</li><li className={step >= 2 ? "active" : ""}><span>{step > 2 ? <Check size={15} aria-hidden /> : "2"}</span>{t("newAudit.stepBaseline")}</li><li className={step >= 3 ? "active" : ""}><span>3</span>{t("newAudit.stepContext")}</li></ol>{error ? <div className="inline-error" role="alert"><strong>{error.title}</strong><span>{error.text}</span>{mode === "expert" && error.technicalCode ? <code>{t("newAudit.technicalError", { code: error.technicalCode })}</code> : null}</div> : null}
    {step === 1 ? <section className="wizard-panel"><div className="source-grid"><label className="source-card upload-card"><span className="source-icon"><Files size={24} aria-hidden /></span><strong>{t("newAudit.uploadTitle")}</strong><span>{t("newAudit.uploadBody")}</span><span className="file-button">{t("newAudit.chooseFiles")}</span><input className="sr-only" type="file" multiple accept=".json,.zip,application/json,application/zip" onChange={(event) => { setFiles(Array.from(event.target.files ?? [])); setPreview(null); }} /></label><button className="source-card" type="button" onClick={() => void startDemo()} disabled={working}><span className="source-icon"><FlaskConical size={24} aria-hidden /></span><strong>{t("newAudit.demoTitle")}</strong><span>{t("newAudit.demoBody")}</span></button><button className="source-card" disabled type="button"><span className="source-icon"><Cloud size={24} aria-hidden /></span><strong>{t("newAudit.tenantTitle")}</strong><span>{t("newAudit.tenantBody")}</span><small>{t("common.planned")}</small></button></div>{files.length ? <div className="selected-files"><strong>{t("newAudit.selectedFiles")}</strong><ul>{files.map((file) => <li key={`${file.name}-${String(file.size)}`}><FileArchive size={16} aria-hidden />{file.name}<span>{new Intl.NumberFormat(language).format(file.size)} B</span></li>)}</ul></div> : <p className="muted-note">{t("newAudit.noFiles")}</p>}<div className="wizard-actions"><button className="primary-action" type="button" disabled={!files.length || working} onClick={() => void inspectFiles()}>{working ? t("newAudit.inspecting") : t("newAudit.continue")}<ArrowRight size={17} aria-hidden /></button></div></section> : null}
    {step === 2 ? <section className="wizard-panel"><fieldset className="pack-options"><legend>{t("newAudit.selectedPack")}</legend>{availablePacks.map((pack) => <label className={`pack-selector ${selectedPackId === pack.pack_id ? "selected" : ""}`} key={pack.pack_id}><input className="sr-only" type="radio" name="pack" value={pack.pack_id} checked={selectedPackId === pack.pack_id} onChange={() => setSelectedPackId(pack.pack_id)} /><span className="source-icon"><ShieldCheck size={24} aria-hidden /></span><div><strong>{pack.name}</strong><p>{pack.product} · {pack.version}</p>{pack.synthetic ? <span className="synthetic-label">{t("app.synthetic")}</span> : null}</div>{selectedPackId === pack.pack_id ? <Check aria-hidden /> : null}</label>)}<label className={`pack-selector ${selectedPackId === "" ? "selected" : ""}`}><input className="sr-only" type="radio" name="pack" value="" checked={selectedPackId === ""} onChange={() => setSelectedPackId("")} /><span className="source-icon"><ShieldCheck size={24} aria-hidden /></span><div><strong>{t("newAudit.limited")}</strong><p>{t("newAudit.limitedBody")}</p></div>{selectedPackId === "" ? <Check aria-hidden /> : null}</label></fieldset><div className="action-row"><Link className="secondary-action" to="/knowledge-packs">{t("newAudit.managePacks")}</Link></div><label className="file-field"><span>{t("newAudit.deviation")}</span><input type="file" accept=".json,application/json" onChange={(event) => setDeviation(event.target.files?.[0])} /></label><div className="wizard-actions"><button className="secondary-action" type="button" onClick={() => setStep(1)}><ArrowLeft size={17} aria-hidden />{t("newAudit.back")}</button><button className="primary-action" type="button" disabled={selectedPackId !== "" && !availablePacks.some((pack) => pack.pack_id === selectedPackId)} onClick={() => setStep(3)}>{t("newAudit.continue")}<ArrowRight size={17} aria-hidden /></button></div></section> : null}
    {step === 3 ? <form className="wizard-panel" onSubmit={(event) => void startUpload(event)}><h2>{t("newAudit.contextTitle")}</h2><div className="checkbox-grid"><label><input type="checkbox" {...form.register("physical")} />{t("newAudit.physical")}</label><label><input type="checkbox" {...form.register("vdi")} />{t("newAudit.vdi")}</label><label><input type="checkbox" {...form.register("shared")} />{t("newAudit.shared")}</label></div><label className="file-field"><span>{t("newAudit.requirements")}</span><input type="file" accept=".json,application/json" onChange={(event) => setRequirements(event.target.files?.[0])} /></label><label className="textarea-field"><span>{t("newAudit.pilot")}</span><textarea rows={2} {...form.register("pilot")} /></label><label className="textarea-field"><span>{t("newAudit.notes")}</span><textarea rows={3} {...form.register("notes")} /></label><div className="audit-summary"><h2>{t("newAudit.summary")}</h2><dl><div><dt>{t("newAudit.selectedFiles")}</dt><dd>{files.length}</dd></div><div><dt>{t("newAudit.detectedPolicies")}</dt><dd>{preview?.policy_count ?? "—"}</dd></div><div><dt>{t("newAudit.detectedSettings")}</dt><dd>{preview?.setting_count ?? "—"}</dd></div><div><dt>{t("newAudit.selectedPack")}</dt><dd>{selectedPackId || t("newAudit.limited")}</dd></div><div><dt>{t("newAudit.requirements")}</dt><dd>{requirements?.name ?? t("common.notAvailable")}</dd></div><div><dt>{t("preferences.language")}</dt><dd>{language.toUpperCase()}</dd></div></dl><p><LockKeyhole size={16} aria-hidden />{t("newAudit.privacy")}</p><p><LockKeyhole size={16} aria-hidden />{t("newAudit.offlinePermissions")}</p></div><div className="wizard-actions"><button className="secondary-action" type="button" onClick={() => setStep(2)}><ArrowLeft size={17} aria-hidden />{t("newAudit.back")}</button><button className="primary-action" type="submit" disabled={working}>{working ? t("newAudit.starting") : t("newAudit.start")}<ArrowRight size={17} aria-hidden /></button></div></form> : null}
  </div>;
}
