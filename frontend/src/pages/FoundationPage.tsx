import { ArrowRight, FileCheck2, LockKeyhole, ShieldCheck } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

export function FoundationPage() {
  const { t } = useTranslation();
  const principles = [
    { icon: LockKeyhole, title: t("foundation.privacyTitle"), body: t("foundation.privacyBody") },
    { icon: FileCheck2, title: t("foundation.evidenceTitle"), body: t("foundation.evidenceBody") },
    { icon: ShieldCheck, title: t("foundation.readOnlyTitle"), body: t("foundation.readOnlyBody") },
  ];

  return (
    <div className="landing-page">
      <section className="hero-panel">
        <div className="hero-copy">
          <p className="eyebrow">{t("foundation.eyebrow")}</p>
          <h1>{t("foundation.title")}</h1>
          <p className="hero-description">{t("foundation.description")}</p>
          <div className="hero-actions">
            <Link className="primary-action" to="/audit/new">
              {t("foundation.start")} <ArrowRight size={18} aria-hidden />
            </Link>
            <Link className="secondary-action" to="/audit/demo/dashboard">
              {t("foundation.demo")}
            </Link>
          </div>
        </div>
        <div className="trust-visual" aria-label={t("foundation.evidenceTitle")}>
          <div className="signal-orbit orbit-one" aria-hidden="true" />
          <div className="signal-orbit orbit-two" aria-hidden="true" />
          <div className="trust-core">
            <ShieldCheck size={42} aria-hidden="true" />
            <strong>{t("foundation.status")}</strong>
            <span>{t("foundation.notSafe")}</span>
          </div>
          <div className="evidence-chip chip-one">{t("foundation.exactId")}</div>
          <div className="evidence-chip chip-two">{t("foundation.semantics")}</div>
          <div className="evidence-chip chip-three">{t("foundation.source")}</div>
        </div>
      </section>
      <section className="principle-grid" aria-label={t("foundation.evidenceTitle")}>
        {principles.map((principle) => (
          <article className="principle-card" key={principle.title}>
            <span className="principle-icon"><principle.icon size={21} aria-hidden /></span>
            <h2>{principle.title}</h2>
            <p>{principle.body}</p>
          </article>
        ))}
      </section>
      <div className="foundation-status" role="status">
        <span className="status-dot" aria-hidden="true" />
        <strong>{t("foundation.status")}</strong>
        <span>{t("foundation.statusDetail")}</span>
      </div>
    </div>
  );
}
