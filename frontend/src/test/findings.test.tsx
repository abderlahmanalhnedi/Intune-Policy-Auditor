import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import type { Finding } from "../api/client";
import { FindingsPage } from "../pages/FindingsPage";

const findings = [
  {
    finding_id: "one",
    severity: "high",
    finding_type: "baseline_deviation",
    policy_id: "p1",
    policy_name: "High policy",
    setting_id: "synthetic.one",
    setting_name: { de: "Hoch", en: "High" },
    configured_value: false,
    microsoft_value: true,
    alignment: "less_restrictive",
    evidence_confidence: "exact",
    title: { de: "Hoher Befund", en: "High finding" },
    explanation: { de: "Abweichung", en: "Deviation" },
    why_it_matters: { de: "Test", en: "Test" },
    user_impact: { de: "Test", en: "Test" },
    business_impact: { de: "Test", en: "Test" },
    recommended_action: { de: "Prüfen", en: "Review" },
    pilot_suggestion: { de: "Pilot", en: "Pilot" },
    rollback_suggestion: { de: "Zurückrollen", en: "Roll back" },
    evidence: [],
    decision_trace: [],
    assignments: [],
    applicability: "applicable",
  },
  {
    finding_id: "two",
    severity: "information",
    finding_type: "insufficient_evidence",
    policy_id: "p2",
    policy_name: "Unknown policy",
    setting_id: "unknown.two",
    setting_name: { de: "Unbekannt", en: "Unknown" },
    configured_value: "value",
    microsoft_value: null,
    alignment: "not_evaluable",
    evidence_confidence: "unknown",
    title: { de: "Nicht bewertbar", en: "Not evaluable" },
    explanation: { de: "Evidenz fehlt", en: "Evidence is missing" },
    why_it_matters: { de: "Unbekannt", en: "Unknown" },
    user_impact: { de: "Unbekannt", en: "Unknown" },
    business_impact: { de: "Unbekannt", en: "Unknown" },
    recommended_action: { de: "Evidenz ergänzen", en: "Add evidence" },
    pilot_suggestion: { de: "Kein Pilot", en: "No pilot" },
    rollback_suggestion: { de: "Nicht zutreffend", en: "Not applicable" },
    evidence: [],
    decision_trace: [],
    assignments: [],
    applicability: "unknown",
    not_evaluable_reasons: ["unknown_setting_id"],
  },
] as unknown as Finding[];

vi.mock("../features/audit/hooks", () => ({
  useFindings: () => ({
    isLoading: false,
    isError: false,
    data: { items: findings, total: findings.length, page: 1, page_size: 200 },
  }),
}));

describe("findings filters", () => {
  it("filters by severity and not-evaluable state without recalculating the audit", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter initialEntries={["/audit/demo/findings"]}><Route path="/audit/:auditId/findings"><FindingsPage /></Route></MemoryRouter>);
    expect(screen.getByText("High policy")).toBeVisible();
    expect(screen.getByText("Unknown policy")).toBeVisible();
    await user.selectOptions(screen.getByRole("combobox"), "not_evaluable");
    expect(screen.queryByText("High policy")).not.toBeInTheDocument();
    expect(screen.getByText("Unknown policy")).toBeVisible();
    await user.selectOptions(screen.getByRole("combobox"), "high");
    expect(screen.getByText("High policy")).toBeVisible();
    expect(screen.queryByText("Unknown policy")).not.toBeInTheDocument();
  });
});
