import type { TFunction } from "i18next";

export function localized(value: Record<string, string>, language: string): string {
  return value[language] ?? value.en ?? Object.values(value)[0] ?? "";
}

export function displayValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}

export function percent(value: number | null | undefined, locale: string, t: TFunction): string {
  return value === null || value === undefined
    ? t("common.notAvailable")
    : new Intl.NumberFormat(locale, { style: "percent", maximumFractionDigits: 0 }).format(value);
}

export function dominantAlignment(statuses: string[]): string {
  const priority = ["expired_deviation", "less_restrictive", "not_evaluable", "different", "more_restrictive", "accepted_deviation", "aligned"];
  return priority.find((status) => statuses.includes(status)) ?? "not_evaluable";
}

