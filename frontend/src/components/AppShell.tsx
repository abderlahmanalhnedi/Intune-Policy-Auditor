import { Button } from "@fluentui/react-components";
import {
  BookOpen,
  Box,
  CircleHelp,
  FileBarChart,
  FileSearch,
  Gauge,
  Languages,
  Menu,
  Moon,
  Network,
  PanelLeftClose,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Sun,
  UsersRound,
} from "lucide-react";
import { useEffect, useState, type ComponentType, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { NavLink, useLocation } from "react-router-dom";

import { usePreferences } from "../app/preferences";

interface NavigationItem {
  label: string;
  path: string;
  icon: ComponentType<{ size?: number; "aria-hidden"?: boolean }>;
}

export function AppShell({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const { language, mode, theme, setLanguage, setMode, setTheme } = usePreferences();
  const location = useLocation();
  const [navOpen, setNavOpen] = useState(false);
  useEffect(() => {
    if (!navOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setNavOpen(false);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [navOpen]);
  const auditId = /^\/audit\/([^/]+)/.exec(location.pathname)?.[1] ?? "demo";
  const mainItems: NavigationItem[] = [
    { label: t("navigation.dashboard"), path: `/audit/${auditId}/dashboard`, icon: Gauge },
    { label: t("navigation.policies"), path: `/audit/${auditId}/policies`, icon: FileSearch },
    { label: t("navigation.findings"), path: `/audit/${auditId}/findings`, icon: ShieldCheck },
    { label: t("navigation.conflicts"), path: `/audit/${auditId}/conflicts`, icon: Network },
    { label: t("navigation.knowledge"), path: "/knowledge-packs", icon: Box },
    { label: t("navigation.reports"), path: `/audit/${auditId}/reports`, icon: FileBarChart },
  ];
  const secondaryItems: NavigationItem[] = [
    { label: t("navigation.tenant"), path: "/tenant", icon: UsersRound },
    { label: t("navigation.settings"), path: "/settings", icon: Settings },
    { label: t("navigation.help"), path: "/help", icon: CircleHelp },
    { label: t("navigation.about"), path: "/about", icon: BookOpen },
  ];

  const cycleTheme = () => {
    setTheme(theme === "system" ? "light" : theme === "light" ? "dark" : "system");
  };

  return (
    <div className="app-frame">
      <a className="skip-link" href="#main-content">
        {t("common.skip")}
      </a>
      <header className="topbar">
        <Button
          appearance="subtle"
          className="mobile-menu"
          icon={<Menu aria-hidden />}
          aria-label={t("navigation.open")}
          onClick={() => setNavOpen(true)}
        />
        <NavLink to="/" className="brand" aria-label={t("app.name")}>
          <span className="brand-mark" aria-hidden="true">
            <ShieldCheck size={22} />
          </span>
          <span>
            <strong>{t("app.name")}</strong>
            <small>{t("app.independent")}</small>
          </span>
        </NavLink>
        <div className="preference-controls">
          <label className="compact-control">
            <Languages size={16} aria-hidden="true" />
            <span className="sr-only">{t("preferences.language")}</span>
            <select
              value={language}
              onChange={(event) => setLanguage(event.target.value as "de" | "en")}
            >
              <option value="de">DE</option>
              <option value="en">EN</option>
            </select>
          </label>
          <label className="compact-control mode-control">
            <SlidersHorizontal size={16} aria-hidden="true" />
            <span className="sr-only">{t("preferences.mode")}</span>
            <select
              value={mode}
              onChange={(event) => setMode(event.target.value as "guided" | "expert")}
            >
              <option value="guided">{t("preferences.guided")}</option>
              <option value="expert">{t("preferences.expert")}</option>
            </select>
          </label>
          <Button
            appearance="subtle"
            icon={theme === "dark" ? <Moon aria-hidden /> : <Sun aria-hidden />}
            aria-label={`${t("preferences.theme")}: ${t(`preferences.${theme}`)}`}
            title={`${t("preferences.theme")}: ${t(`preferences.${theme}`)}`}
            onClick={cycleTheme}
          />
        </div>
      </header>

      <aside className={`sidebar ${navOpen ? "is-open" : ""}`} aria-label={t("navigation.main")}>
        <div className="sidebar-mobile-header">
          <strong>{t("navigation.main")}</strong>
          <Button
            appearance="subtle"
            icon={<PanelLeftClose aria-hidden />}
            aria-label={t("navigation.close")}
            onClick={() => setNavOpen(false)}
          />
        </div>
        <nav>
          <ul className="nav-list">
            {mainItems.map((item) => (
              <li key={item.path}>
                <NavLink
                  to={item.path}
                  onClick={() => setNavOpen(false)}
                  activeClassName="active"
                >
                  <item.icon size={19} aria-hidden />
                  <span>{item.label}</span>
                </NavLink>
              </li>
            ))}
          </ul>
          <div className="nav-divider" />
          <ul className="nav-list nav-secondary">
            {secondaryItems.map((item) => (
              <li key={item.path}>
                <NavLink
                  to={item.path}
                  onClick={() => setNavOpen(false)}
                  activeClassName="active"
                >
                  <item.icon size={18} aria-hidden />
                  <span>{item.label}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
        <div className="sidebar-footnote">
          <span className="status-dot" aria-hidden="true" />
          <span>{t("app.offline")}</span>
          <small>v3.0.0-dev</small>
        </div>
      </aside>
      {navOpen ? <button className="nav-scrim" aria-label={t("navigation.close")} onClick={() => setNavOpen(false)} /> : null}

      <main id="main-content" className="main-content" tabIndex={-1}>
        {children}
      </main>
    </div>
  );
}
