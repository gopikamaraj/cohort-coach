import type { Page } from "@playwright/test";

// The language switch and the role are in the title bar; a role is chosen on the landing page's cards.

/** Choose the language in My profile, then go back to the screen the test was on. */
export async function chooseLanguage(page: Page, lang: string): Promise<void> {
  const at = new URL(page.url()).hash || "#/roles";
  await page.goto("/#/profile");
  await page.getByTestId("profile-lang").selectOption(lang);
  await page.goto(`/${at}`);
}

/** Choose a role as the landing page's cards do (the app reads it when it starts), then open its home. */
export async function chooseRole(page: Page, role: string): Promise<void> {
  await page.goto("/#/roles");
  await page.evaluate((r) => localStorage.setItem("cc.role", r), role);
  await page.reload();
  const home: Record<string, string> = { teacher: "home", mentor: "mentor", coach: "coach", officer: "officer", admin: "admin", judge: "roles" };
  await page.goto(`/#/${home[role] ?? "home"}`);
}
