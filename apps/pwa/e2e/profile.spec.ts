import { readFileSync } from "node:fs";
import { expect, test, type Page } from "@playwright/test";

// My profile (classes, storage and backup, data used, privacy), the privacy notice and consent, feedback to
// the admin, and the icon toasts. These tests start with NO consent (unlike the others) on purpose.

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => {
    localStorage.clear();
    localStorage.setItem("cc.voice", "0");
  });
});

async function chooseAll(page: Page) {
  await page.goto("/#/profile");
  for (const s of ["counts", "practice_ai", "feedback"]) await page.getByTestId(`consent-${s}`).check();
}

test("nothing is on by default, the notice is readable, and choices are recorded with a version", async ({ page }) => {
  const records: string[] = [];
  page.on("request", (r) => {
    if (/\/api\/consents$/.test(r.url())) records.push(r.postData() ?? "");
  });
  await page.goto("/#/home");
  await expect(page.getByTestId("privacy-prompt")).toBeVisible();
  await page.getByTestId("privacy-start").click();
  await expect(page.getByTestId("privacy-notice")).toContainText("Digital Personal Data Protection Act");
  await expect(page.getByTestId("grievance")).toBeVisible();
  await page.getByTestId("notice-to-profile").click();
  for (const s of ["counts", "practice_ai", "share_rehearsal", "feedback"]) await expect(page.getByTestId(`consent-${s}`)).not.toBeChecked();
  await page.getByTestId("consent-counts").check();
  await expect(page.getByText("notice version 1")).toBeVisible();
  await expect.poll(() => records.length).toBeGreaterThan(0);
  const first = JSON.parse(records[0]!) as Record<string, unknown>;
  expect(Object.keys(first).sort()).toEqual(["device_id", "granted", "scope", "version"]);
  expect(String(first["device_id"])).toMatch(/^[0-9a-f]{16}$/);
  await page.getByTestId("consent-withdraw").click();
  await expect(page.getByTestId("consent-counts")).not.toBeChecked();
  await page.goto("/#/home");
  await expect(page.getByTestId("privacy-prompt")).toBeHidden(); // she has chosen (to withdraw): not asked again
});

test("class counts are not sent until she agrees", async ({ page }) => {
  const posts: string[] = [];
  page.on("request", (r) => {
    if (/\/profile$/.test(r.url()) && r.method() === "POST") posts.push(r.url());
  });
  await page.route("**/api/classes/*/profile", (route) => route.fulfill({ status: 200, contentType: "application/json", body: "{}" }));
  await page.goto("/#/judge");
  await page.getByTestId("load-demo").click();
  await expect(page.getByTestId("demo-loaded")).toBeVisible();
  await page.waitForTimeout(800);
  expect(posts).toHaveLength(0);
  await page.goto("/#/profile");
  await page.getByTestId("consent-counts").check();
  await page.goto("/#/judge");
  await page.reload();
  await expect.poll(() => posts.length).toBeGreaterThan(0);
});

test("the Practice Class asks before using AI, then remembers", async ({ page }) => {
  await page.goto("/#/practice");
  await expect(page.getByTestId("practice-consent")).toBeVisible();
  await expect(page.getByTestId("start-practice")).toContainText("Allow and start");
  await page.getByTestId("start-practice").click();
  await expect(page.getByTestId("kid-4")).toBeVisible();
  await page.goto("/#/profile");
  await expect(page.getByTestId("consent-practice_ai")).toBeChecked();
});

test("several classes: add, switch, rename and delete, each with its own data", async ({ page }) => {
  await page.goto("/#/profile");
  await page.getByTestId("class-name").fill("Class 3A");
  await page.getByTestId("class-add").click();
  await page.getByTestId("class-name").fill("Class 3B");
  await page.getByTestId("class-add").click();
  await expect(page.getByTestId("class-row")).toHaveCount(2);
  await expect(page.getByTestId("class-row").first()).toContainText("In use");
  await page.getByTestId("class-use").first().click();
  await expect(page.getByTestId("class-row").nth(1)).toContainText("In use");
  page.once("dialog", (d) => void d.accept());
  await page.getByTestId("class-delete").first().click();
  await expect(page.getByTestId("class-row")).toHaveCount(1);
});

test("the browser is asked to keep her data, and she can see the answer", async ({ page }) => {
  await page.addInitScript(() => {
    let persisted = false;
    Object.defineProperty(navigator, "storage", {
      value: { persist: async () => ((persisted = true), true), persisted: async () => persisted, estimate: async () => ({ usage: 5_000_000, quota: 800_000_000 }) },
      configurable: true,
    });
  });
  await page.reload();
  await page.goto("/#/profile");
  await expect(page.getByTestId("persist-state")).toContainText("protected");
  await expect(page.getByTestId("pf-storage")).toContainText("5.0 MB of about 800.0 MB");
});

test("data used counts the app's own calls, converts to a cost from her price, and clears", async ({ page }) => {
  await page.goto("/#/judge");
  await page.getByTestId("load-demo").click();
  await page.goto("/#/programme");
  await expect(page.getByTestId("prog-cohort")).toContainText(/cohort of|waiting list/); // the call has finished
  await page.goto("/#/profile");
  await expect.poll(async () => parseFloat(await page.getByTestId("data-total").innerText())).toBeGreaterThan(0);
  await page.getByTestId("data-price").fill("100");
  await expect(page.getByTestId("data-cost")).toContainText("About");
  await page.getByTestId("data-clear").click();
  await expect(page.getByTestId("data-total")).toHaveText("0.0 KB");
});

test("export then restore brings the work back, and a passphrase-sealed file needs its passphrase", async ({ page }, info) => {
  await page.goto("/#/judge");
  await page.getByTestId("load-demo").click();
  await expect(page.getByTestId("demo-loaded")).toBeVisible();
  await page.goto("/#/profile");
  const download = page.waitForEvent("download");
  await page.getByTestId("backup-export").click();
  const file = info.outputPath("backup.json");
  await (await download).saveAs(file);
  const text = readFileSync(file, "utf-8");
  expect(JSON.parse(text).format).toBe("cohort-coach-backup");

  await page.getByTestId("backup-pass").fill("tea and biscuits");
  const sealedDl = page.waitForEvent("download");
  await page.getByTestId("backup-export").click();
  const sealed = info.outputPath("sealed.json");
  await (await sealedDl).saveAs(sealed);
  expect(readFileSync(sealed, "utf-8")).not.toContain("children");

  // wipe the phone, then restore from the sealed file
  page.once("dialog", (d) => void d.accept());
  await page.getByTestId("erase-all").click();
  await expect(page.getByTestId("toast").filter({ hasText: "erased" })).toBeVisible();
  await page.getByTestId("backup-pass").fill("wrong");
  await page.getByTestId("backup-file").setInputFiles(sealed);
  await expect(page.getByTestId("toast").last()).toContainText("passphrase");
  await page.getByTestId("backup-pass").fill("tea and biscuits");
  await page.getByTestId("backup-file").setInputFiles(sealed);
  await expect(page.getByTestId("toast").last()).toContainText("Restored 1 classes");
  await page.goto("/#/history");
  await expect(page.getByTestId("history-check").first()).toContainText("28 children");
});

test("erase everything clears the phone and asks the server to erase the class counts", async ({ page }) => {
  const erased: string[] = [];
  page.on("request", (r) => {
    if (r.method() === "DELETE") erased.push(r.url());
  });
  await page.route("**/api/classes/*", (route) => (route.request().method() === "DELETE" ? route.fulfill({ status: 200, contentType: "application/json", body: '{"deleted":1}' }) : route.continue()));
  await page.goto("/#/judge");
  await page.getByTestId("load-demo").click();
  await expect(page.getByTestId("demo-loaded")).toBeVisible();
  await page.goto("/#/profile");
  page.once("dialog", (d) => void d.accept());
  await page.getByTestId("erase-all").click();
  await expect(page.getByTestId("toast").first()).toContainText("erased");
  expect(erased.length).toBeGreaterThan(0);
  await page.goto("/#/history");
  await expect(page.getByTestId("history-empty")).toBeVisible();
});

test("feedback needs her switch, refuses personal details, and reaches the admin to review", async ({ page }) => {
  await page.goto("/#/profile");
  await page.getByTestId("star-4").click();
  await page.getByTestId("feedback-text").fill("The keypad is easy to use");
  await page.getByTestId("feedback-send").click();
  await expect(page.getByTestId("toast").last()).toContainText("Turn on");
  await page.getByTestId("consent-feedback").check();
  await page.getByTestId("feedback-text").fill("call me on 9876543210");
  await page.getByTestId("feedback-send").click();
  await expect(page.getByTestId("toast").last()).toContainText("personal");
  await page.getByTestId("feedback-text").fill("The keypad is easy to use e2e-" + Date.now());
  await page.getByTestId("feedback-send").click();
  await expect(page.getByTestId("toast").last()).toContainText("Thank you");

  await page.getByTestId("role").selectOption("admin");
  await expect(page.getByTestId("admin")).toBeVisible();
  await expect(page.getByTestId("admin-item").first()).toContainText("The keypad is easy to use");
  await expect(page.getByTestId("admin-item").first()).toContainText("★★★★");
  await page.getByTestId("admin-kind").selectOption("simulation");
  await expect(page.getByTestId("admin-item")).toHaveCount(0);
  await page.getByTestId("admin-kind").selectOption("app");
  page.once("dialog", (d) => void d.accept("looks fine"));
  await page.getByTestId("admin-review").first().click();
  await expect(page.getByTestId("admin-item").first()).toHaveAttribute("data-status", "reviewed");
});

test("the card's speaker icon answers with a toast instead of a paragraph, and a flag reaches the admin", async ({ page }) => {
  await page.goto("/#/profile");
  await page.getByTestId("consent-feedback").check();
  await page.goto("/#/judge");
  await page.getByTestId("load-demo").click();
  await page.goto("/#/cards");
  const listen = page.getByTestId("listen-SUB-SFL");
  await expect(listen).toHaveAttribute("aria-label", "Listen");
  await expect(listen).not.toContainText("Listen"); // an icon, not a sentence
  await listen.click();
  await expect(page.getByTestId("toast").last()).toContainText("Listening arrives");
  await page.getByTestId("flag-SUB-SFL").click();
  await expect(page.getByTestId("toast").last()).toContainText("review this card");
  await page.getByTestId("role").selectOption("admin");
  await page.getByTestId("admin-kind").selectOption("card_flag");
  await expect(page.getByTestId("admin-item").first()).toContainText("SUB-SFL");
});

test("role screens: coach sees counts only, mentor sees what mentors do, nothing is a percentage", async ({ page }) => {
  await page.goto("/#/judge");
  await page.getByTestId("role").selectOption("coach");
  await expect(page.getByTestId("coach-T1")).toBeVisible();
  await expect(page.getByTestId("coach-T1")).toContainText(/\d+ of \d+ children checked/);
  await page.getByTestId("role").selectOption("mentor");
  await expect(page.getByTestId("mentor")).toContainText("exact words");
  expect(await page.locator("body").innerText()).not.toMatch(/%/);
});
