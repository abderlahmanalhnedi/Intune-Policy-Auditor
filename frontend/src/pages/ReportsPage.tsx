import { Download, FileCode2, FileSpreadsheet, FileText } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import { usePreferences } from "../app/preferences";
import { reportUrl } from "../api/client";

export function ReportsPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const { language } = usePreferences();
  const { t } = useTranslation();
  const reports = [
    ["html", "reports.executive", FileText], ["technical-html", "reports.technicalHtml", FileText], ["markdown", "reports.markdown", FileText], ["json", "reports.json", FileCode2],
    ["findings-csv", "reports.findingsCsv", FileSpreadsheet], ["conflicts-csv", "reports.conflictsCsv", FileSpreadsheet],
    ["not-evaluable-csv", "reports.notEvaluableCsv", FileSpreadsheet], ["provenance-json", "reports.provenance", FileCode2], ["pdf", "reports.pdf", FileText],
  ] as const;
  return <div className="content-page"><div className="page-heading"><div><p className="eyebrow">{t("reports.eyebrow")}</p><h1>{t("reports.title")}</h1><p className="page-intro">{t("reports.intro")}</p></div></div><div className="report-grid">{reports.map(([format, label, Icon]) => <article className="report-card" key={format}><span className="source-icon"><Icon size={22} aria-hidden /></span><div><h2>{t(label)}</h2><code>{format}</code></div><a className="secondary-action" href={reportUrl(auditId, format, language)} download><Download size={17} aria-hidden />{t("reports.download")}</a></article>)}</div></div>;
}
