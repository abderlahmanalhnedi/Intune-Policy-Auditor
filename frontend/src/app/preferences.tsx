/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useTranslation } from "react-i18next";

export type Language = "de" | "en";
export type ExperienceMode = "guided" | "expert";
export type ThemePreference = "system" | "light" | "dark";

interface PreferencesValue {
  language: Language;
  mode: ExperienceMode;
  theme: ThemePreference;
  resolvedTheme: "light" | "dark";
  setLanguage: (language: Language) => void;
  setMode: (mode: ExperienceMode) => void;
  setTheme: (theme: ThemePreference) => void;
}

const PreferencesContext = createContext<PreferencesValue | null>(null);

function preference<T extends string>(key: string, allowed: readonly T[], fallback: T): T {
  const value = localStorage.getItem(key);
  return value !== null && allowed.includes(value as T) ? (value as T) : fallback;
}

export function PreferencesProvider({ children }: { children: ReactNode }) {
  const { i18n } = useTranslation();
  const [language, setLanguageState] = useState<Language>(() =>
    preference("ipa-language", ["de", "en"], "de"),
  );
  const [mode, setModeState] = useState<ExperienceMode>(() =>
    preference("ipa-mode", ["guided", "expert"], "guided"),
  );
  const [theme, setThemeState] = useState<ThemePreference>(() =>
    preference("ipa-theme", ["system", "light", "dark"], "system"),
  );
  const [systemTheme, setSystemTheme] = useState<"light" | "dark">(() =>
    window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light",
  );

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const update = () => setSystemTheme(media.matches ? "dark" : "light");
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);

  const resolvedTheme = theme === "system" ? systemTheme : theme;

  useEffect(() => {
    document.documentElement.dataset.theme = resolvedTheme;
    document.documentElement.style.colorScheme = resolvedTheme;
  }, [resolvedTheme]);

  const setLanguage = useCallback(
    (next: Language) => {
      setLanguageState(next);
      localStorage.setItem("ipa-language", next);
      document.documentElement.lang = next;
      void i18n.changeLanguage(next);
    },
    [i18n],
  );
  const setMode = useCallback((next: ExperienceMode) => {
    setModeState(next);
    localStorage.setItem("ipa-mode", next);
  }, []);
  const setTheme = useCallback((next: ThemePreference) => {
    setThemeState(next);
    localStorage.setItem("ipa-theme", next);
  }, []);

  const value = useMemo(
    () => ({ language, mode, theme, resolvedTheme, setLanguage, setMode, setTheme }),
    [language, mode, theme, resolvedTheme, setLanguage, setMode, setTheme],
  );
  return <PreferencesContext.Provider value={value}>{children}</PreferencesContext.Provider>;
}

export function usePreferences(): PreferencesValue {
  const value = useContext(PreferencesContext);
  if (value === null) {
    throw new Error("usePreferences must be used within PreferencesProvider");
  }
  return value;
}
