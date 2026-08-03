import { useQuery } from "@tanstack/react-query";

import {
  getAudit,
  getConflicts,
  getDashboard,
  getFinding,
  getFindings,
  getPolicies,
  getPolicy,
} from "../../api/client";

export const useAudit = (auditId: string) =>
  useQuery({ queryKey: ["audit", auditId], queryFn: () => getAudit(auditId) });

export const useDashboard = (auditId: string) =>
  useQuery({ queryKey: ["audit", auditId, "dashboard"], queryFn: () => getDashboard(auditId) });

export const usePolicies = (auditId: string) =>
  useQuery({ queryKey: ["audit", auditId, "policies"], queryFn: () => getPolicies(auditId) });

export const usePolicy = (auditId: string, policyId: string) =>
  useQuery({ queryKey: ["audit", auditId, "policy", policyId], queryFn: () => getPolicy(auditId, policyId) });

export const useFindings = (auditId: string) =>
  useQuery({ queryKey: ["audit", auditId, "findings"], queryFn: () => getFindings(auditId) });

export const useFinding = (auditId: string, findingId: string) =>
  useQuery({ queryKey: ["audit", auditId, "finding", findingId], queryFn: () => getFinding(auditId, findingId) });

export const useConflicts = (auditId: string) =>
  useQuery({ queryKey: ["audit", auditId, "conflicts"], queryFn: () => getConflicts(auditId) });

