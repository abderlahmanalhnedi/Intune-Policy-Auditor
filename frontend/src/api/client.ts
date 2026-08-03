import type { components } from "./schema";

export type AuditResult = components["schemas"]["AuditResult"];
export type AuditPreview = components["schemas"]["AuditPreview"];
export type DashboardSummary = components["schemas"]["DashboardSummary"];
export type PolicyEvaluation = components["schemas"]["PolicyEvaluation"];
export type Finding = components["schemas"]["Finding"];
export type ConflictResult = components["schemas"]["ConflictResult"];
export type KnowledgePackSummary = components["schemas"]["KnowledgePackSummary"];
export type SettingEvaluation = components["schemas"]["SettingEvaluation"];
export type TenantStatus = components["schemas"]["TenantStatus"];
export type DeviceCodePrompt = components["schemas"]["DeviceCodePrompt"];
export type AuthenticationResult = components["schemas"]["AuthenticationResult"];
export type PublicSettings = components["schemas"]["PublicSettings"];
export type LocalPreferences = components["schemas"]["LocalPreferences"];
export type PackValidationReport = components["schemas"]["PackValidationReport"];

interface Envelope<T> {
  data: T;
  meta: { request_id: string };
}

interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

interface Problem {
  title?: string;
  detail?: string;
  request_id?: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers,
  });
  if (!response.ok) {
    let problem: Problem = {};
    try {
      problem = (await response.json()) as Problem;
    } catch {
      problem = {};
    }
    throw new ApiError(problem.detail ?? problem.title ?? `HTTP ${String(response.status)}`, response.status, problem.request_id);
  }
  return (await response.json()) as T;
}

export async function createDemoAudit(language: "de" | "en"): Promise<AuditResult> {
  const response = await request<Envelope<AuditResult>>(`/audits/demo?language=${language}`, { method: "POST" });
  return response.data;
}

export async function previewOfflineAudit(files: File[]): Promise<AuditPreview> {
  const form = new FormData();
  for (const file of files) form.append("files", file);
  const response = await request<Envelope<AuditPreview>>("/audits/preview", { method: "POST", body: form });
  return response.data;
}

export interface AuditContextInput {
  physical_device?: boolean;
  vdi?: boolean;
  shared_device?: boolean;
  pilot_context?: string;
  environment_notes?: string;
}

export async function createOfflineAudit(
  files: File[],
  language: "de" | "en",
  packIds: string[],
  context: AuditContextInput,
  deviation?: File,
  organizationRequirements?: File,
): Promise<AuditResult> {
  const form = new FormData();
  for (const file of files) form.append("files", file);
  form.append("knowledge_pack_ids", JSON.stringify(packIds));
  form.append("language", language);
  form.append("audit_context", JSON.stringify(context));
  if (deviation) form.append("deviations", deviation);
  if (organizationRequirements) form.append("organization_requirements", organizationRequirements);
  const response = await request<Envelope<AuditResult>>("/audits", { method: "POST", body: form });
  return response.data;
}

export async function getAudit(auditId: string): Promise<AuditResult> {
  const response = await request<Envelope<AuditResult>>(`/audits/${encodeURIComponent(auditId)}`);
  return response.data;
}

export async function getDashboard(auditId: string): Promise<DashboardSummary> {
  const response = await request<Envelope<DashboardSummary>>(`/audits/${encodeURIComponent(auditId)}/dashboard`);
  return response.data;
}

export async function getPolicies(auditId: string): Promise<Page<PolicyEvaluation>> {
  const response = await request<Envelope<Page<PolicyEvaluation>>>(`/audits/${encodeURIComponent(auditId)}/policies?page_size=200`);
  return response.data;
}

export async function getPolicy(auditId: string, policyId: string): Promise<PolicyEvaluation> {
  const response = await request<Envelope<PolicyEvaluation>>(`/audits/${encodeURIComponent(auditId)}/policies/${encodeURIComponent(policyId)}`);
  return response.data;
}

export async function getFindings(auditId: string): Promise<Page<Finding>> {
  const response = await request<Envelope<Page<Finding>>>(`/audits/${encodeURIComponent(auditId)}/findings?page_size=200`);
  return response.data;
}

export async function getFinding(auditId: string, findingId: string): Promise<Finding> {
  const response = await request<Envelope<Finding>>(`/audits/${encodeURIComponent(auditId)}/findings/${encodeURIComponent(findingId)}`);
  return response.data;
}

export async function getConflicts(auditId: string): Promise<Page<ConflictResult>> {
  const response = await request<Envelope<Page<ConflictResult>>>(`/audits/${encodeURIComponent(auditId)}/conflicts?page_size=200`);
  return response.data;
}

export async function getKnowledgePacks(): Promise<KnowledgePackSummary[]> {
  const response = await request<Envelope<KnowledgePackSummary[]>>("/knowledge-packs");
  return response.data;
}

export async function importKnowledgePack(file: File): Promise<KnowledgePackSummary> {
  const form = new FormData();
  form.append("pack", file);
  const response = await request<Envelope<KnowledgePackSummary>>("/knowledge-packs/import", { method: "POST", body: form });
  return response.data;
}

export async function validateKnowledgePack(file: File): Promise<PackValidationReport> {
  const form = new FormData();
  form.append("pack", file);
  const response = await request<Envelope<PackValidationReport>>("/knowledge-packs/validate", { method: "POST", body: form });
  return response.data;
}

export async function setKnowledgePackActive(packId: string, active: boolean): Promise<KnowledgePackSummary> {
  const action = active ? "activate" : "deactivate";
  const response = await request<Envelope<KnowledgePackSummary>>(`/knowledge-packs/${encodeURIComponent(packId)}/${action}`, { method: "POST" });
  return response.data;
}

export async function removeKnowledgePack(packId: string): Promise<void> {
  await request<Envelope<{ removed: boolean }>>(`/knowledge-packs/${encodeURIComponent(packId)}`, { method: "DELETE" });
}

export async function getTenantStatus(): Promise<TenantStatus> {
  const response = await request<Envelope<TenantStatus>>("/tenant/status");
  return response.data;
}

export async function beginDeviceCode(): Promise<DeviceCodePrompt> {
  const response = await request<Envelope<DeviceCodePrompt>>("/tenant/device-code", { method: "POST" });
  return response.data;
}

export async function completeDeviceCode(flowId: string): Promise<AuthenticationResult> {
  const response = await request<Envelope<AuthenticationResult>>("/tenant/device-code/complete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ flow_id: flowId }),
  });
  return response.data;
}

export async function signOutTenant(): Promise<void> {
  await request<Envelope<{ signed_out: boolean }>>("/tenant/signout", { method: "POST" });
}

export async function getSettings(): Promise<PublicSettings> {
  const response = await request<Envelope<PublicSettings>>("/settings");
  return response.data;
}

export async function updateSettings(settings: LocalPreferences): Promise<LocalPreferences> {
  const response = await request<Envelope<LocalPreferences>>("/settings", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings),
  });
  return response.data;
}

export async function deleteLocalAuditData(): Promise<void> {
  await request<Envelope<Record<string, number>>>("/settings/local-audit-data", { method: "DELETE" });
}

export async function clearTemporaryFiles(): Promise<void> {
  await request<Envelope<Record<string, number>>>("/settings/clear-temporary", { method: "POST" });
}

export async function clearTokenCache(): Promise<void> {
  await request<Envelope<{ token_cache_deleted: boolean }>>("/settings/clear-token-cache", { method: "POST" });
}

export async function resetSettings(): Promise<void> {
  await request<Envelope<Record<string, number>>>("/settings/reset", { method: "POST" });
}

export function reportUrl(auditId: string, format: string, language: "de" | "en"): string {
  return `/api/v1/audits/${encodeURIComponent(auditId)}/reports/${encodeURIComponent(format)}?language=${language}`;
}
