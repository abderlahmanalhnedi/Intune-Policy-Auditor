import { describe, expect, it } from "vitest";

import i18n from "../i18n";
import { displayValue, dominantAlignment, localized, percent } from "../features/audit/format";

describe("audit presentation helpers", () => {
  it("does not present an unavailable metric as zero", () => {
    expect(percent(null, "en", i18n.t)).toBe("Nicht verfügbar");
    expect(percent(0, "en", i18n.t)).toBe("0%");
  });

  it("uses deterministic status priority and safe plain-value rendering", () => {
    expect(dominantAlignment(["aligned", "not_evaluable"])).toBe("not_evaluable");
    expect(localized({ de: "Deutsch", en: "English" }, "en")).toBe("English");
    expect(displayValue({ enabled: true })).toBe('{"enabled":true}');
  });
});
