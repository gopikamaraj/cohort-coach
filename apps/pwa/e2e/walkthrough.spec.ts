// Phase 3 walk-through of the clean-up (docs/build/reports/CLEANUP-REPORT.md): two teacher nicknames, a coach and an
// officer, each in a browser context of its own (a context is a separate browser profile, so it stands in for a
// separate device). The six flows of the plan, in one story:
//   2. Teacher A goes offline, enters answers, comes back online: the popup, everything saved, the cloud has it.
//   1. Teacher B cannot see A's check. The officer sees counts, switches the rule, creates a cohort from both classes;
//      both teachers see the cohort and its plan.
//   3. Teacher A signs in with the same nickname on a second profile and sees the same data.
//   4. No term appears on any page, and A's earlier entries are visible.
//   5. A module's audio plays in the browser.
//   6. The error-rule control is on every page where counts appear, and the counts change correctly.
import { mkdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { type Browser, type BrowserContext, type Page } from "@playwright/test";
import { expect, test } from "./test";
import { enterRolls, finishEntering, startSample } from "./sample";

const here = path.dirname(fileURLToPath(import.meta.url));
const fx = JSON.parse(readFileSync(path.join(here, "fixtures", "results16.json"), "utf-8")) as { children: { answers: string[] }[] };
const SHOTS = path.resolve(here, "../../../data/autopilot-screens");
const CONSENT = '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}';
const ORIGIN = "http://localhost:4173";

interface Person {
  id: string;
  ctx: BrowserContext;
  page: Page;
}

/** A person signed in with a nickname, in a browser context of their own. Pass `id` to be the same person again. */
async function person(browser: Browser, label: string, role: string, id?: string): Promise<Person> {
  const nick = id ?? `wt-${label}-${Date.now().toString(36)}${Math.random().toString(36).slice(2, 5)}`;
  if (!id) {
    const res = await fetch("http://localhost:8011/api/users/register", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ nickname: nick }) });
    expect(res.ok, `registering ${nick}`).toBe(true);
  }
  const user = JSON.stringify({ id: nick, nickname: nick });
  const ctx = await browser.newContext({
    baseURL: ORIGIN,
    viewport: { width: 390, height: 844 },
    serviceWorkers: "allow",
    extraHTTPHeaders: { "X-User": nick },
    storageState: {
      cookies: [],
      origins: [{ origin: ORIGIN, localStorage: [{ name: "cc.user", value: user }, { name: "cc.cacheOwner", value: nick }, { name: "cc.role", value: role }, { name: "cc.consent", value: CONSENT }, { name: "cc.voice", value: "0" }] }],
    },
  });
  return { id: nick, ctx, page: await ctx.newPage() };
}

const API = "http://localhost:8011";
/** What the cloud database holds for one person: a plain request from Node, so the browser's offline switch does not touch it. */
const storeOf = async (id: string): Promise<Record<string, Record<string, unknown>>> => (await (await fetch(`${API}/api/store`, { headers: { "X-User": id } })).json()) as Record<string, Record<string, unknown>>;
const status = async (id: string, role: string, route: string): Promise<number> => (await fetch(`${API}${route}`, { headers: { "X-User": id, "X-Role": role } })).status;

async function noTerms(page: Page, where: string): Promise<void> {
  await page.waitForLoadState("networkidle");
  const text = await page.locator("body").innerText();
  expect(text, `${where} shows the word term`).not.toMatch(/\bterms?\b/i);
  expect(text, `${where} shows a paper code with a term`).not.toMatch(/ · T\d+\b/);
  await expect(page.getByTestId("term-select"), `${where} has a term selector`).toHaveCount(0);
}

const shot = async (page: Page, name: string): Promise<void> => {
  mkdirSync(SHOTS, { recursive: true });
  await page.screenshot({ path: path.join(SHOTS, `walkthrough-${name}.png`) });
};

// a missing element fails in 30 seconds with its name, not after the whole test budget
test.use({ actionTimeout: 30_000 });

test("the walk-through: two teachers, a coach and an officer", async ({ browser }) => {
  test.setTimeout(900_000);
  const A = await person(browser, "a", "teacher");
  const B = await person(browser, "b", "teacher");
  const coach = await person(browser, "c", "coach");
  const officer = await person(browser, "o", "officer");
  const everyone = [A, B, coach, officer];
  try {
    // ---- flow 2: A goes offline, enters answers, comes back online ------------------------------------------------
    await startSample(A.page, { size: fx.children.length });
    await A.page.waitForTimeout(800); // the class and the new check are written while online
    await A.ctx.setOffline(true);
    await enterRolls(A.page, fx.children.map((c) => c.answers));
    await A.page.waitForTimeout(600);
    expect(JSON.stringify((await storeOf(A.id)).checks), "nothing of A's offline entry is in the cloud yet").not.toContain("346");
    await A.ctx.setOffline(false);
    await expect(A.page.getByTestId("sync-notice")).toBeVisible({ timeout: 30_000 });
    await expect(A.page.getByTestId("sync-body")).toContainText("while you were offline");
    await shot(A.page, "2-popup");
    await expect(A.page.getByTestId("sync-saved")).toBeVisible({ timeout: 30_000 });
    await expect(A.page.getByTestId("sync-notice")).toBeHidden({ timeout: 15_000 });
    await expect.poll(async () => JSON.stringify((await storeOf(A.id)).checks), { timeout: 20_000 }).toContain("346"); // the cloud database has it
    await finishEntering(A.page);

    // B enters the same made-up class (online)
    await startSample(B.page, { size: fx.children.length });
    await enterRolls(B.page, fx.children.map((c) => c.answers));
    await finishEntering(B.page);
    await A.page.goto("/#/cards");
    await expect(A.page.getByTestId("answer-map")).toBeVisible({ timeout: 30_000 });
    await B.page.goto("/#/cards");
    await expect(B.page.getByTestId("answer-map")).toBeVisible({ timeout: 30_000 });

    // ---- flow 1: B cannot see A's check; the officer sees counts and creates a cohort ---------------------------------
    // each check reaches the cloud a moment after it is finished (the write goes out at once while online)
    for (const p of [A, B]) await expect.poll(async () => Object.keys((await storeOf(p.id)).checks).length, { timeout: 20_000, message: `${p.id}'s check is in the cloud` }).toBeGreaterThan(0);
    const sa = await storeOf(A.id);
    const sb = await storeOf(B.id);
    expect(Object.keys(sa.checks).length, "A has her check").toBeGreaterThan(0);
    expect(Object.keys(sb.checks).length, "B has her check").toBeGreaterThan(0);
    for (const k of Object.keys(sa.checks)) expect(Object.keys(sb.checks), "B never gets A's check").not.toContain(k);
    for (const k of Object.keys(sa.classes)) expect(Object.keys(sb.classes), "B never gets A's class").not.toContain(k);
    expect(await status(B.id, "teacher", "/api/store/all/checks"), "a teacher cannot list other teachers' checks").toBe(403);
    expect(await status(B.id, "teacher", "/api/store/coach-summary"), "a teacher cannot read the officer's counts").toBe(403);
    expect(await status(coach.id, "coach", "/api/store/all/checks"), "a coach sees only the checks of cohorts assigned to her (none yet)").toBe(200);

    await officer.page.goto("/#/officer");
    await expect(officer.page.getByTestId("officer")).toBeVisible();
    await expect(officer.page.getByTestId("rule-control").first()).toBeVisible();
    await officer.page.getByTestId("rule-2").first().check(); // the default, stated
    await officer.page.getByTestId("coach-pick-SUB-SFL").check();
    await expect(officer.page.getByTestId("officer-classes")).toBeVisible();
    await expect(officer.page.getByTestId("demo-caps").first()).toContainText("Demo: no minimum group sizes");
    const rows = officer.page.locator("[data-testid^=officer-class-]");
    // the officer sees every entered class, so this needs a test database with no other class in it
    await expect(rows, "the officer lists exactly A's and B's classes: delete e2e.sqlite at the repo root (servers stopped) and run again").toHaveCount(2);
    const labels = officer.page.locator("label:has([data-testid^=officer-class-])"); // the checkbox carries the test id; the words are in its label
    const counts = async (): Promise<number[]> => (await labels.allInnerTexts()).map((t) => Number(/(\d+) children/.exec(t)?.[1] ?? NaN));
    const confirmed = await counts();
    expect(confirmed.every((n) => Number.isFinite(n) && n > 0), `each class shows how many children, as a number (rows: ${JSON.stringify(await labels.allInnerTexts())})`).toBe(true);
    const page_text = await officer.page.locator("body").innerText();
    for (const p of [A, B]) expect(page_text, "the officer sees no nickname").not.toContain(p.id);
    expect(page_text, "no class is named, only Class A and Class B").toMatch(/Class A/);
    await officer.page.getByTestId("rule-1").first().check(); // count a mistake seen in one question too
    await expect.poll(counts, { timeout: 15_000 }).not.toEqual(confirmed);
    const possible = await counts();
    possible.forEach((n, i) => expect(n, "the possible rule counts at least the confirmed children").toBeGreaterThanOrEqual(confirmed[i] ?? 0));
    expect(possible.reduce((a, b) => a + b, 0), "and more of them").toBeGreaterThan(confirmed.reduce((a, b) => a + b, 0));
    await expect(officer.page.getByTestId("rule-shown").first()).toContainText("one question");
    await shot(officer.page, "1-officer-create");
    await expect(officer.page.getByTestId("officer-select-all")).toBeChecked();
    await officer.page.getByTestId("coach-cohort-name").fill("Walk-through cohort");
    await officer.page.getByTestId("coach-cohort-create").click();
    await expect(officer.page.getByTestId("officer-made")).toContainText("Cohort created from 2 classes");
    await expect(officer.page.getByTestId("coach-cohorts")).toContainText("Walk-through cohort");
    await expect(officer.page.getByTestId("coach-cohorts").getByTestId("rule-line")).toContainText("one question"); // the cohort says which rule it was built with

    // both teachers see the cohort and its plan
    for (const t of [A, B]) {
      await t.page.goto("/#/cohort"); // My programme: her cohorts and their improvement plan
      await expect(t.page.getByTestId("my-class-cohorts")).toContainText("Walk-through cohort", { timeout: 30_000 });
      await expect(t.page.getByTestId("module-start"), "the plan is there, ready to start").toBeVisible({ timeout: 30_000 });
    }
    await shot(B.page, "1-teacher-b-sees-the-cohort");

    // ---- flow 5: a module's audio plays in the browser -----------------------------------------------------------
    await A.page.getByTestId("module-start").click();
    await expect(A.page.getByTestId("module-1")).toBeVisible({ timeout: 60_000 });
    await expect(A.page.getByTestId("module-1-player-audio")).toHaveCount(0); // no autoplay: nothing is made until she presses Listen
    await A.page.getByTestId("module-1-listen").click();
    await expect(A.page.getByTestId("module-1-toggle")).toBeVisible({ timeout: 60_000 });
    const audio = A.page.getByTestId("module-1-player-audio");
    expect(await audio.evaluate((a: HTMLAudioElement) => a.paused)).toBe(true);
    await A.page.getByTestId("module-1-toggle").click();
    await expect.poll(() => audio.evaluate((a: HTMLAudioElement) => a.paused), { timeout: 15_000 }).toBe(false);
    await A.page.getByTestId("module-1-toggle").click();
    await expect.poll(() => audio.evaluate((a: HTMLAudioElement) => a.paused)).toBe(true);
    await shot(A.page, "5-audio-player");

    // ---- flow 3: A signs in with the same nickname on a second profile -------------------------------------------
    const A2 = await person(browser, "a", "teacher", A.id);
    everyone.push(A2);
    await A2.page.goto("/#/cards"); // a new profile with an empty cache: it signs in by nickname and reads everything from the cloud
    const mapShown = await A2.page.getByTestId("answer-map").waitFor({ timeout: 30_000 }).then(() => true, () => false);
    if (!mapShown) {
      const idb = await A2.page.evaluate(() => new Promise<string>((res) => { const r = indexedDB.open("cohort-coach"); r.onsuccess = () => { const out: Record<string, number> = {}; const names = ["classes", "checks", "profiles", "settings", "transcripts"]; let n = 0; for (const tb of names) { const g = r.result.transaction(tb).objectStore(tb).count(); g.onsuccess = () => { out[tb] = g.result; if (++n === names.length) res(JSON.stringify(out)); }; } }; }));
      const cloud = await storeOf(A.id);
      throw new Error(`the second profile does not show A's results. Its cache holds ${idb}; the cloud holds ${JSON.stringify(Object.fromEntries(Object.entries(cloud).map(([k, v]) => [k, Object.keys(v).length])))}; the page says: ${(await A2.page.locator("main").innerText()).replace(/\s+/g, " ").slice(0, 240)}`);
    }
    await A2.page.goto("/#/cohort");
    await expect(A2.page.getByTestId("my-class-cohorts")).toContainText("Walk-through cohort", { timeout: 30_000 });

    // ---- flow 6: the rule control is on every page that shows counts, and the counts change correctly --------------
    await A.page.goto("/#/cards");
    await expect(A.page.getByTestId("rule-control").first()).toBeVisible();
    await A.page.getByTestId("rule-2").first().check();
    await expect(A.page.getByTestId("rule-shown").first()).toContainText("two or more");
    await expect(A.page.getByTestId("mistakes-table").getByText(/possible/)).toHaveCount(0);
    const confirmedCard = await A.page.getByTestId("card-SUB-SFL").locator(".numeral").innerText();
    await A.page.getByTestId("rule-1").first().check();
    await expect(A.page.getByTestId("mistakes-table").getByText(/possible/).first()).toBeVisible();
    expect(await A.page.getByTestId("card-SUB-SFL").locator(".numeral").innerText(), "the confirmed count itself does not change").toBe(confirmedCard);
    await shot(A.page, "6-results-rule");
    await coach.page.goto("/#/coach");
    await expect(coach.page.getByTestId("rule-control").first(), "the coach page has the control").toBeVisible();
    await coach.page.getByTestId("rule-1").first().check();
    await expect(coach.page.getByTestId("rule-shown").first()).toContainText("one question");
    await coach.page.getByTestId("rule-2").first().check();
    await expect(coach.page.getByTestId("rule-shown").first()).toContainText("two or more");
    await officer.page.goto("/#/officer");
    await expect(officer.page.getByTestId("rule-control").first(), "the officer page has the control").toBeVisible();
    const officer2 = await person(browser, "o", "officer", officer.id); // the officer on another device
    everyone.push(officer2);
    await officer2.page.goto("/#/officer");
    await expect(officer2.page.getByTestId("rule-1").first(), "the rule is saved to her account: the other device shows one question").toBeChecked({ timeout: 30_000 });

    // ---- flow 4: no term anywhere, and A's earlier entries are visible ------------------------------------------
    for (const [who, routes] of [
      [A, ["/#/home", "/#/papers", "/#/check", "/#/cards", "/#/history", "/#/cohort", "/#/profile"]],
      [B, ["/#/home", "/#/papers", "/#/cards", "/#/history"]],
      [coach, ["/#/coach"]],
      [officer, ["/#/officer"]],
    ] as [Person, string[]][]) {
      for (const r of routes) {
        await who.page.goto(r);
        await noTerms(who.page, `${who.id} ${r}`);
      }
    }
    await A.page.goto("/#/history");
    await expect(A.page.locator("body")).toContainText("16", { timeout: 20_000 }); // her 16-roll check is listed, by date
  } finally {
    for (const p of everyone) await p.ctx.close().catch(() => undefined);
  }
});
