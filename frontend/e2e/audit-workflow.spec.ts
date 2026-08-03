import { expect, test } from "@playwright/test";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import JSZip from "jszip";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "../..");
const samples = path.join(root, "samples", "policies");
const generated = path.join(root, "frontend", "test-results", "generated");
const policyZip = path.join(generated, "policies.zip");
const utf16Policy = path.join(generated, "policy-utf16-le.json");
const binaryJson = path.join(generated, "binary.json");

test.beforeAll(async () => {
  await mkdir(generated, { recursive: true });
  const zip = new JSZip();
  const policy = await readFile(path.join(samples, "01-core-device-security.json"));
  zip.file("policy.json", policy);
  await writeFile(policyZip, await zip.generateAsync({ type: "nodebuffer" }));
  await writeFile(utf16Policy, Buffer.concat([Buffer.from([0xff, 0xfe]), Buffer.from(policy.toString("utf8"), "utf16le")]));
  await writeFile(binaryJson, Buffer.from([0x00, 0x01, 0x4d, 0x5a, 0xff, 0x10]));
});

test("demo audit covers navigation, modes, themes, languages, and reports", async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 768 });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Intune|Verstehen|Understand/ })).toBeVisible();
  await page.getByLabel("Sprache").selectOption("en");
  await page.getByRole("link", { name: "Open demonstration audit" }).click();
  await expect(page).toHaveURL(/\/audit\/[^/]+\/dashboard/);
  await expect(page.getByRole("heading", { name: "Decision dashboard" })).toBeVisible();
  await expect(page.getByText(/Synthetic demonstration data/)).toBeVisible();

  await page.getByLabel("View").selectOption("expert");
  await expect(page.getByLabel("View")).toHaveValue("expert");
  await page.getByLabel("View").selectOption("guided");
  await page.getByRole("button", { name: /Theme: System/ }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.getByRole("button", { name: /Theme: Light/ }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");

  for (const destination of ["Policies", "Findings", "Conflicts", "Knowledge Packs", "Reports"]) {
    await page.getByRole("link", { name: destination, exact: true }).click();
    await expect(page.getByRole("heading", { name: new RegExp(destination === "Knowledge Packs" ? "Knowledge Packs" : destination) })).toBeVisible();
    if (destination === "Findings") await expect(page.getByRole("table").getByText("Not evaluable").first()).toBeVisible();
    if (destination === "Conflicts") {
      await expect(page.getByRole("table").getByText("Confirmed").first()).toBeVisible();
      await expect(page.getByRole("table").getByText("Possible").first()).toBeVisible();
    }
  }
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("article").filter({ hasText: "Technical PDF report" }).getByRole("link", { name: "Download" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/\.pdf$/);

  await page.getByLabel("Language").selectOption("de");
  await expect(page.getByRole("heading", { name: "Berichte" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("offline wizard accepts multiple JSON files, deviations, and a selected pack", async ({ page }) => {
  await page.goto("/audit/new");
  await page.getByLabel("Sprache").selectOption("en");
  await page.locator('input[type="file"][multiple]').setInputFiles([
    path.join(samples, "01-core-device-security.json"),
    path.join(samples, "02-hardened-pilot.json"),
  ]);
  await expect(page.getByText("2", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByRole("radio", { name: /Synthetic Test Baseline/i })).toBeChecked();
  await page.locator('input[type="file"]:not([multiple])').setInputFiles(
    path.join(root, "organization", "accepted-deviations.example.json"),
  );
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByLabel("Organization requirements (optional)").setInputFiles(
    path.join(root, "organization", "requirements.example.json"),
  );
  await page.getByRole("button", { name: "Start audit" }).click();
  await expect(page).toHaveURL(/\/audit\/[^/]+\/dashboard/);
  await expect(page.getByRole("heading", { name: "Decision dashboard" })).toBeVisible();
  await page.getByRole("link", { name: "Findings", exact: true }).click();
  await expect(page.getByRole("table").getByRole("row", { name: /Accepted deviation/ }).first()).toBeVisible();
});

test("UTF-16 JSON and ZIP inputs succeed while malformed and binary JSON are localized", async ({ page }) => {
  await page.goto("/audit/new");
  await page.getByLabel("Sprache").selectOption("en");
  await page.locator('input[type="file"][multiple]').setInputFiles(
    utf16Policy,
  );
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Start audit" }).click();
  await expect(page).toHaveURL(/\/dashboard/);

  await page.goto("/audit/new");
  await page.locator('input[type="file"][multiple]').setInputFiles(policyZip);
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Start audit" }).click();
  await expect(page).toHaveURL(/\/dashboard/);

  await page.goto("/audit/new");
  await page.locator('input[type="file"][multiple]').setInputFiles(
    path.join(root, "samples", "malformed", "malformed.json"),
  );
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByRole("alert")).toContainText("File cannot be read");
  await expect(page.getByRole("alert")).toContainText("The file does not contain a supported JSON document. Intune exports must be stored as UTF-8 or UTF-16 with an unambiguous byte order.");
  await expect(page.getByRole("alert")).not.toContainText("malformed_json");

  await page.locator('input[type="file"][multiple]').setInputFiles(binaryJson);
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByRole("alert")).toContainText("File cannot be read");
  await expect(page.getByRole("alert")).not.toContainText("unsupported_encoding");
  await page.getByLabel("View").selectOption("expert");
  await expect(page.getByRole("alert")).toContainText("Technical error: unsupported_encoding");
});
