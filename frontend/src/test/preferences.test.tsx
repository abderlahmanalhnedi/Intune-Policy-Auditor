import { FluentProvider, webLightTheme } from "@fluentui/react-components";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { PreferencesProvider, usePreferences } from "../app/preferences";
import { AppShell } from "../components/AppShell";

function PreferenceProbe() {
  const preferences = usePreferences();
  return <div><output>{preferences.language}:{preferences.mode}:{preferences.theme}:{preferences.resolvedTheme}</output><button onClick={() => preferences.setMode("expert")}>expert</button><button onClick={() => preferences.setTheme("dark")}>dark</button><button onClick={() => preferences.setLanguage("en")}>English</button></div>;
}

describe("preferences and navigation", () => {
  it("persists Guided/Expert, language, and light/dark choices locally", async () => {
    const user = userEvent.setup();
    render(<PreferencesProvider><PreferenceProbe /></PreferencesProvider>);
    expect(screen.getByText("de:guided:system:light")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "expert" }));
    await user.click(screen.getByRole("button", { name: "dark" }));
    await user.click(screen.getByRole("button", { name: "English" }));
    expect(screen.getByText("en:expert:dark:dark")).toBeVisible();
    expect(localStorage.getItem("ipa-mode")).toBe("expert");
    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("supports keyboard dismissal of responsive navigation", async () => {
    const user = userEvent.setup();
    render(<FluentProvider theme={webLightTheme}><MemoryRouter><PreferencesProvider><AppShell><p>Content</p></AppShell></PreferencesProvider></MemoryRouter></FluentProvider>);
    await user.click(screen.getByRole("button", { name: /navigation öffnen|open navigation/i }));
    expect(screen.getByRole("complementary")).toHaveClass("is-open");
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.getByRole("complementary")).not.toHaveClass("is-open");
  });
});
