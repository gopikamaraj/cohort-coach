import { expect, test } from "@playwright/test";

// A phone: four tabs and More, the bottom bar never scrolls away, and only the content scrolls.
const ROUTES = ["home", "check", "cards", "practice", "programme", "history", "profile", "privacy", "judge", "roles", "tour", "coach", "admin"];

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => {
    localStorage.clear();
    localStorage.setItem("cc.consent", '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}');
  });
});

for (const width of [320, 390, 768, 1280]) {
  test(`no page runs off the side at ${width} px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 640 });
    for (const route of ROUTES) {
      await page.goto(`/#/${route}`);
      await page.waitForTimeout(200);
      const over = await page.evaluate(() => {
        const main = document.querySelector("main") as HTMLElement;
        return { main: main.scrollWidth - main.clientWidth, page: document.documentElement.scrollWidth - innerWidth };
      });
      expect(over, route).toEqual({ main: 0, page: 0 });
    }
  });
}

test("the bottom bar holds four tabs and More, and More opens the rest", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 640 });
  await page.goto("/#/home");
  const tabs = page.locator(".navbar > *");
  await expect(tabs).toHaveCount(5);
  expect(await page.evaluate(() => { const n = document.querySelector(".navbar") as HTMLElement; return n.scrollWidth - n.clientWidth; })).toBe(0);
  await page.getByTestId("nav-more").click();
  const sheet = page.getByTestId("more-sheet");
  await expect(sheet.getByRole("link")).toHaveCount(3); // programme, history, profile
  await sheet.getByRole("link").nth(1).click();
  await expect(page).toHaveURL(/#\/history/);
  await expect(sheet).toHaveCount(0);
  await expect(page.getByTestId("nav-more")).toHaveAttribute("aria-expanded", "false");
});

test("on a long page the content scrolls and the bottom bar stays in view", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 640 });
  await page.goto("/#/profile");
  const main = page.locator("main");
  await main.evaluate((m) => (m.scrollTop = 99999));
  expect(await main.evaluate((m) => m.scrollTop)).toBeGreaterThan(500);
  const bottom = await page.locator(".navbar").evaluate((n) => n.getBoundingClientRect().bottom);
  expect(Math.round(bottom)).toBe(640);
});
