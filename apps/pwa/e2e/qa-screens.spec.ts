import { expect, test, type Page } from "@playwright/test";
import { axe, fits, fresh, noRawText, shot, targets } from "./qa";

test.use({ actionTimeout: 30_000 });

// Cross-cutting QA (docs/build/reports/QA-DEMO.md, Step 4): a role matrix (which tabs and which
// role-only widgets each role sees), axe on every inventoried screen for every role that reaches
// it, and Hindi and Tamil on the main screens (fits, no raw keys, no English words left).
// Recorded AI answers; a simulated class loaded from judge mode; synthetic data only.

const NAV: Record<string, string[]> = {
  teacher: ["#/home", "#/papers", "#/check", "#/cards", "#/practice", "#/programme", "#/history", "#/profile"],
  mentor: ["#/mentor", "#/home", "#/papers", "#/check", "#/cards", "#/practice", "#/programme", "#/history", "#/profile"],
  coach: ["#/coach", "#/review", "#/papers", "#/cohort", "#/profile"],
  officer: ["#/officer", "#/review", "#/profile"],
  judge: ["#/judge", "#/demo", "#/two-classes", "#/home", "#/papers", "#/check", "#/cards", "#/practice", "#/programme", "#/history", "#/coach", "#/review", "#/cohort", "#/admin", "#/profile"],
};

// Screens reached from outside the tabs (links, the header, the landing page).
const EXTRA: Record<string, string[]> = {
  teacher: ["#/privacy", "#/watch", "#/flow"],
  mentor: ["#/cohort"],
  coach: [],
  officer: [],
  judge: ["#/roles", "#/tour", "#/watch", "#/aimap", "#/audit", "#/testing", "#/assistant", "#/officer", "#/mentor"],
};

async function withClass(page: Page, role: string, lang = "en") {
  await fresh(page, "judge", lang);
  await page.goto("/#/judge");
  await page.getByTestId("load-demo").click();
  await expect(page.getByTestId("demo-loaded")).toBeVisible();
  await page.evaluate((r) => localStorage.setItem("cc.role", r), role);
  await page.reload(); // the role is read when the app starts; a hash change alone keeps the old one
}

const tabs = (page: Page) => page.locator(".navbar a").evaluateAll((as) => as.map((a) => (a as HTMLAnchorElement).hash));

for (const role of Object.keys(NAV)) {
  test(`role matrix and axe on every screen: ${role}`, async ({ page }) => {
    test.setTimeout(300_000);
    await withClass(page, role);
    await page.goto(`/${NAV[role]![0]}`);
    await expect(page.locator(".navbar")).toBeVisible();
    expect.soft(await tabs(page), `${role}: tabs in order`).toEqual(NAV[role]);
    if (role === "officer") expect.soft(await tabs(page), "officers have no Papers page").not.toContain("#/papers");
    for (const route of [...NAV[role]!, ...EXTRA[role]!]) {
      await page.goto(`/${route}`);
      await page.waitForLoadState("networkidle").catch(() => undefined);
      await page.waitForTimeout(300);
      const where = `${role} ${route}`;
      await axe(page, where);
      await fits(page, where);
      await noRawText(page, where);
      await targets(page, where);
    }
  });
}

test("role-only widgets: judge tools say they are judge-only, officers cannot make papers", async ({ page }) => {
  test.setTimeout(240_000);
  // On the judge deployment (JUDGE_MODE=1) a judge viewing as any role keeps the judge tools, and
  // they say so; a teacher deployment never shows them (QA-DEMO, Open question 1).
  for (const role of ["teacher", "judge"]) {
    await withClass(page, role);
    await page.goto("/#/practice");
    await page.getByTestId("start-practice").click();
    await expect(page.getByTestId("kid-4")).toBeVisible();
    await page.getByTestId("side-judge").click();
    await expect.soft(page.locator("#side-panel-judge")).toContainText("Not shown to teachers");
  }
  await withClass(page, "officer");
  await page.goto("/#/papers");
  expect.soft(await page.getByTestId("papers-create").count(), "officer: no Create a paper").toBe(0);
});

// Words that may stay in Latin script on a translated screen: codes, the product name, units.
const KEEP = new Set(["SUB-SFL", "SUB-NODEC", "ADD-NOCARRY", "PV-HEARD", "PV-REVERSE", "Cohort", "Coach", "Mbps", "SCERT", "Demo", "PDF", "YAML", "ZIP", "Sarvam", "Claude", "Anthropic", "Opus", "Sonnet", "Haiku"]);

for (const lang of ["hi", "ta"] as const) {
  test(`main screens in ${lang === "hi" ? "Hindi" : "Tamil"}: fit, no raw keys, no English left`, async ({ page }) => {
    test.setTimeout(300_000);
    await withClass(page, "teacher", lang);
    const script = lang === "hi" ? /[ऀ-ॿ]/ : /[஀-௿]/;
    for (const route of ["#/home", "#/papers", "#/check", "#/cards", "#/practice", "#/programme", "#/demo?step=1", "#/demo?step=4", "#/two-classes"]) {
      await page.goto(`/${route}`);
      await page.waitForLoadState("networkidle").catch(() => undefined);
      await page.waitForTimeout(300);
      const where = `${lang} ${route}`;
      await fits(page, where);
      await noRawText(page, where);
      const text = (await page.locator("main").innerText()).replace(/[\w-]+\.(json|png|pdf|zip|yaml)/g, " "); // file names stay as they are
      expect.soft(script.test(text), `${where}: text in the chosen script`).toBe(true);
      const english = [...new Set((text.match(/\b[A-Za-z][A-Za-z'-]{3,}\b/g) ?? []).filter((w) => !KEEP.has(w)))];
      expect.soft(english, `${where}: English words left on a translated screen`).toEqual([]);
      await shot(page, `lang-${lang}`, route.replace(/[#/?=]+/g, "-").replace(/^-|-$/g, ""));
    }
  });
}

// Performance on a throttled phone profile (Fast 3G: 1.6 Mbps down, 750 kbps up, 150 ms latency;
// CPU 4x slower). First visit (nothing cached) and a second visit (the service worker's cache), to
// the point where the screen's main heading is visible. Written to test-results/qa-perf.json.
test("each demo screen is usable within about 3 seconds on a throttled phone", async ({ page, context }) => {
  test.setTimeout(300_000);
  const cdp = await context.newCDPSession(page);
  await cdp.send("Network.enable");
  await cdp.send("Network.emulateNetworkConditions", { offline: false, latency: 150, downloadThroughput: (1.6 * 1024 * 1024) / 8, uploadThroughput: (750 * 1024) / 8 });
  await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
  const out: { route: string; first_ms: number; cached_ms: number }[] = [];
  await fresh(page, "teacher");
  for (const route of ["#/roles", "#/home", "#/papers", "#/check", "#/cards", "#/practice", "#/programme", "#/demo?step=1"]) {
    const t0 = Date.now();
    await page.goto(`/${route}`);
    await page.locator("main h1, main h2").first().waitFor({ timeout: 60_000 });
    const first = Date.now() - t0;
    const t1 = Date.now();
    await page.reload();
    await page.locator("main h1, main h2").first().waitFor({ timeout: 60_000 });
    out.push({ route, first_ms: first, cached_ms: Date.now() - t1 });
  }
  const { writeFileSync, mkdirSync } = await import("node:fs");
  mkdirSync("test-results", { recursive: true });
  writeFileSync("test-results/qa-perf.json", JSON.stringify({ profile: "Fast 3G, CPU 4x", at: new Date().toISOString(), screens: out }, null, 1));
  for (const r of out) expect.soft(r.cached_ms, `${r.route}: usable within 3 s once cached`).toBeLessThan(3000);
});
