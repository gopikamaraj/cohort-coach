import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => localStorage.clear());
  await page.goto("/#/roles");
  await page.reload();
});

test("a fresh browser lands on four role cards and the guided tour", async ({ page }) => {
  await expect(page.getByTestId("card-tour")).toBeVisible();
  await expect(page.getByTestId("card-tour")).toContainText("Start here if you're judging");
  for (const r of ["teacher", "mentor", "coach", "officer"]) await expect(page.getByTestId(`card-${r}`)).toBeVisible();
  await expect(page.getByTestId("card-coach")).toContainText("DIET");
  await expect(page.getByTestId("card-officer")).toContainText("programme staff");
});

test("picking a role shows what it can and cannot do, then enters the dashboard once", async ({ page }) => {
  await page.getByTestId("card-officer").click();
  const dialog = page.getByTestId("role-dialog");
  await expect(dialog).toBeVisible();
  await expect(page.getByTestId("dlg-cannot")).toContainText("counts only, and nothing under 5 classes");
  await expect(dialog).toContainText("Simulated");
  await page.getByTestId("dlg-back").click();
  await expect(page.getByTestId("role-dialog")).toHaveCount(0);
  await page.getByTestId("card-officer").click();
  await page.getByTestId("dlg-enter").click();
  await expect(page).toHaveURL(/#\/officer/);
  // the second time the dialog is skipped
  await page.goto("/#/roles");
  await page.getByTestId("card-officer").click();
  await expect(page).toHaveURL(/#\/officer/);
});

test("the teacher dialog says what is on Telegram and the weekly cap, with no percentage", async ({ page }) => {
  await page.getByTestId("card-teacher").click();
  const dialog = page.getByTestId("role-dialog");
  await expect(dialog).toContainText("Telegram");
  await expect(dialog).toContainText("At most 20 minutes a week");
  await expect(dialog).not.toContainText("%");
});

test("a role has a deep link that opens its dialog", async ({ page }) => {
  await page.goto("/#/roles?open=coach");
  await expect(page.getByTestId("role-dialog")).toContainText("BRC, CRC, DIET faculty member or head teacher");
});

test("the landing page uses the width: one column on a phone, a grid of equal cards on a laptop", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/#/roles");
  await page.reload();
  const frame = (await page.locator(".frame").boundingBox())!;
  expect(frame.width).toBeGreaterThan(1000);
  const widths = await Promise.all(["teacher", "mentor", "coach", "officer"].map(async (r) => (await page.getByTestId(`card-${r}`).boundingBox())!.width));
  expect(Math.max(...widths) - Math.min(...widths)).toBeLessThan(2); // equal cards, not ragged
  const ys = await Promise.all(["teacher", "officer"].map(async (r) => (await page.getByTestId(`card-${r}`).boundingBox())!.y));
  expect(Math.abs(ys[0]! - ys[1]!)).toBeLessThan(2); // four across on one row
  await page.setViewportSize({ width: 390, height: 800 });
  await page.reload();
  const t = (await page.getByTestId("card-teacher").boundingBox())!;
  const o = (await page.getByTestId("card-officer").boundingBox())!;
  expect(Math.abs(t.width - o.width)).toBeLessThan(2);
  expect(t.x + t.width).toBeLessThanOrEqual(390);
});

test("the install card opens plain steps in her language, and closes again", async ({ page }) => {
  await expect(page.getByTestId("install-card")).toBeVisible();
  await page.getByTestId("install-open").click();
  const sheet = page.getByTestId("install-dialog");
  await expect(sheet).toBeVisible();
  await expect(sheet).toContainText("What is this?");
  await expect(page.getByTestId("install-steps").locator("li")).toHaveCount(5);
  await expect(sheet).toContainText("Add to Home screen");
  await expect(sheet).toContainText("The Practice Class needs signal");
  await expect(sheet).not.toContainText("%");
  await page.getByTestId("install-close").click();
  await expect(sheet).toBeHidden();
  // Esc closes it too
  await page.getByTestId("install-open").click();
  await expect(sheet).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(sheet).toBeHidden();
});

test("the install steps read in Hindi and Tamil, with no English words", async ({ page }) => {
  for (const [lang, title] of [["hi", "यह क्या है?"], ["ta", "இது என்ன?"]] as const) {
    await page.goto("/#/roles");
    await page.getByTestId("lang").selectOption(lang);
    await page.getByTestId("install-open").click();
    const sheet = page.getByTestId("install-dialog");
    await expect(sheet).toContainText(title);
    const words = (await sheet.innerText()).match(/[A-Za-z][A-Za-z'’-]{2,}/g) ?? [];
    expect(words, lang).toEqual([]);
    await page.getByTestId("install-close").click();
  }
});

test("the install button is on My profile too, and the sheet fits a phone", async ({ page }) => {
  await page.goto("/#/profile");
  await page.getByTestId("install-open").click();
  const box = (await page.getByTestId("install-dialog").boundingBox())!;
  expect(box.x).toBeGreaterThanOrEqual(0);
  expect(box.x + box.width).toBeLessThanOrEqual(page.viewportSize()!.width + 1);
  await expect(page.getByTestId("install-close")).toBeVisible();
  expect((await page.getByTestId("install-close").boundingBox())!.height).toBeGreaterThanOrEqual(48);
});

test("offline: a short pill with the cloud-off icon, and a note on what still works", async ({ page }) => {
  await expect(page.getByTestId("offline-note")).toHaveCount(0);
  await page.context().setOffline(true);
  await expect(page.getByTestId("status")).toHaveText("Offline");
  await expect(page.getByTestId("status").locator("svg")).toHaveCount(1);
  await expect(page.getByTestId("offline-note")).toContainText("saved lessons");
  await expect(page.getByTestId("offline-note")).toContainText("Practice Class needs signal");
  // the app name stays on one line beside the pill
  const brand = (await page.getByTestId("brand").boundingBox())!;
  expect(brand.height).toBeLessThan(60);
  await page.context().setOffline(false);
  await expect(page.getByTestId("status")).toContainText("Online");
  await expect(page.getByTestId("offline-note")).toHaveCount(0);
});

test("online, the pill adds the browser's own signal estimate when it has one", async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "connection", { value: { effectiveType: "3g", downlink: 1.65, addEventListener() {}, removeEventListener() {} }, configurable: true });
  });
  await page.reload();
  await expect(page.getByTestId("status-speed")).toContainText("Slow signal · 1.7 Mbps");
  await expect(page.getByTestId("status")).toHaveAttribute("title", /Upload speed is not shown/);
  await page.context().setOffline(true);
  await expect(page.getByTestId("status-speed")).toHaveCount(0); // no speed while offline
  await page.context().setOffline(false);
});

test("no speed is shown when the browser gives no estimate", async ({ page }) => {
  await page.addInitScript(() => Object.defineProperty(navigator, "connection", { value: undefined, configurable: true }));
  await page.reload();
  await expect(page.getByTestId("status")).toContainText("Online");
  await expect(page.getByTestId("status-speed")).toHaveCount(0);
});

test("the Mode menu needs a second back end; without one the page shows only the mode chip", async ({ page }) => {
  // This test build has one back end, so there is nothing to switch to (the deployed site has two).
  await expect(page.getByTestId("mode")).toHaveCount(0);
  await expect(page.getByTestId("mode-banner")).toContainText("Judge demo");
  await expect(page.getByTestId("card-tour")).toBeVisible();
  await expect(page.getByRole("button", { name: /Open the pilot/ })).toHaveCount(0);
});

test("the tour card sits in the first screen of a phone, above the fold", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 640 });
  await page.reload();
  const tour = (await page.getByTestId("card-tour").boundingBox())!;
  expect(tour.y + tour.height).toBeLessThanOrEqual(640 - 56); // above the bottom bar
});
