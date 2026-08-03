import { describe, expect, it } from "vitest";

import { resources } from "../i18n/resources";

function keys(value: object, prefix = ""): string[] {
  return (Object.entries(value) as [string, unknown][]).flatMap(([key, item]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    return typeof item === "object" && item !== null ? keys(item, path) : [path];
  });
}

describe("translations", () => {
  it("keeps German and English resource keys in exact parity", () => {
    expect(keys(resources.de.translation).sort()).toEqual(keys(resources.en.translation).sort());
  });

  it("contains the mandatory not-evaluable and independence language", () => {
    expect(resources.de.translation.common.notEvaluable).toBe("Nicht bewertbar");
    expect(resources.en.translation.common.notEvaluable).toBe("Not evaluable");
    expect(resources.en.translation.about.disclaimer).toContain("not affiliated");
  });

  it("contains the exact localized JSON upload encoding guidance", () => {
    expect(resources.de.translation.newAudit.uploadReadErrorTitle).toBe(
      "Datei kann nicht gelesen werden",
    );
    expect(resources.de.translation.newAudit.uploadReadErrorText).toBe(
      "Die Datei enthält kein unterstütztes JSON-Dokument. Intune-Exporte müssen als UTF-8 oder UTF-16 mit eindeutiger Byte-Reihenfolge gespeichert sein.",
    );
    expect(resources.en.translation.newAudit.uploadReadErrorTitle).toBe(
      "File cannot be read",
    );
    expect(resources.en.translation.newAudit.uploadReadErrorText).toBe(
      "The file does not contain a supported JSON document. Intune exports must be stored as UTF-8 or UTF-16 with an unambiguous byte order.",
    );
  });
});
