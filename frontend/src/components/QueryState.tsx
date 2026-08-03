import { AlertTriangle, LoaderCircle } from "lucide-react";
import { useTranslation } from "react-i18next";

export function LoadingState() {
  const { t } = useTranslation();
  return <div className="query-state" role="status"><LoaderCircle className="spin" aria-hidden /><strong>{t("common.loading")}</strong></div>;
}

export function ErrorState({ error }: { error: unknown }) {
  const { t } = useTranslation();
  const message = error instanceof Error ? error.message : t("common.unknownError");
  return <div className="query-state query-error" role="alert"><AlertTriangle aria-hidden /><div><strong>{t("common.error")}</strong><p>{message}</p></div></div>;
}

