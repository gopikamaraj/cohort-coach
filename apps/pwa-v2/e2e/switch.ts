import type { Page } from "@playwright/test";

// Role and language are chosen on the landing page (the top bar shows nowhere else); a teacher
// already inside the app changes language in My profile.

/** Choose the language in My profile, then go back to the screen the test was on. */
export async function chooseLanguage(page: Page, lang: string): Promise<void> {
  const at = new URL(page.url()).hash || "#/roles";
  await page.goto("/#/profile");
  await page.getByTestId("profile-lang").selectOption(lang);
  await page.goto(`/${at}`);
}

/** Choose a role on the landing page; the app opens that role's home. */
export async function chooseRole(page: Page, role: string): Promise<void> {
  await page.goto("/#/roles");
  await page.getByTestId("role").selectOption(role);
}
