// Evidence screenshots in English, Hindi and Tamil at 360 px (the target phone's width).
// Run on demand: SCREENSHOTS=1 npx playwright test e2e/screenshots.spec.ts
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

const OUT = fileURLToPath(new URL("../../../docs/evidence/screenshots/", import.meta.url));

test.skip(!process.env["SCREENSHOTS"], "set SCREENSHOTS=1 to regenerate the evidence screenshots");
test.use({ viewport: { width: 360, height: 740 }, deviceScaleFactor: 1, hasTouch: true });

for (const lang of ["en", "hi", "ta"] as const) {
  test(`screenshots in ${lang}`, async ({ page }) => {
    mkdirSync(OUT, { recursive: true });
    await page.goto("/");
    await page.evaluate(() => localStorage.clear());
    await page.goto("/#/judge");
    await page.getByTestId("lang").selectOption(lang);
    await page.getByTestId("reset").click();
    await page.getByTestId("load-demo").click();
    await expect(page.getByTestId("demo-loaded")).toBeVisible();
    await page.screenshot({ path: `${OUT}${lang}-1-judge.png` });
    await page.goto("/#/home");
    await page.screenshot({ path: `${OUT}${lang}-2-home.png` });
    await page.goto("/#/check");
    await page.getByTestId("box-3").click();
    await page.screenshot({ path: `${OUT}${lang}-3-check.png` });
    await page.goto("/#/cards");
    await expect(page.getByTestId("card-SUB-SFL")).toBeVisible();
    await page.screenshot({ path: `${OUT}${lang}-4-cards.png` });
  });
}

test("the desktop view puts the phone in a frame", async ({ page }) => {
  mkdirSync(OUT, { recursive: true });
  await page.setViewportSize({ width: 1100, height: 860 });
  await page.goto("/");
  await page.evaluate(() => localStorage.clear());
  await page.goto("/#/judge");
  await page.getByTestId("load-demo").click();
  await page.goto("/#/cards");
  await expect(page.getByTestId("card-SUB-SFL")).toBeVisible();
  await page.screenshot({ path: `${OUT}desktop-frame.png` });
});
