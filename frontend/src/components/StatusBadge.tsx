import { AlertCircle, CheckCircle2, CircleHelp, Info, ShieldAlert, ShieldCheck } from "lucide-react";
import { useTranslation } from "react-i18next";

const statusGroup = (status: string) => {
  if (["aligned", "succeeded", "valid"].includes(status)) return "success";
  if (["accepted_deviation"].includes(status)) return "accepted";
  if (["critical", "high", "confirmed", "confirmed_conflict", "error", "runtime_remediation_required"].includes(status)) return "danger";
  if (["medium", "low", "less_restrictive", "expired_deviation", "probable", "probable_conflict", "different", "manual_review_required", "changes_required_before_pilot"].includes(status)) return "review";
  if (["not_evaluable", "unknown", "none", "not_in_selected_baseline"].includes(status)) return "unknown";
  return "info";
};

export function StatusBadge({ status, label }: { status: string; label?: string }) {
  const { t } = useTranslation();
  const group = statusGroup(status);
  const Icon = group === "success" ? CheckCircle2 : group === "danger" ? ShieldAlert : group === "review" ? AlertCircle : group === "unknown" ? CircleHelp : group === "accepted" ? ShieldCheck : Info;
  const translated = t(`status.${status}`, { defaultValue: status.replaceAll("_", " ") });
  return (
    <span className={`status-badge status-${group}`}>
      <Icon size={14} aria-hidden="true" />
      <span>{label ?? translated}</span>
    </span>
  );
}

