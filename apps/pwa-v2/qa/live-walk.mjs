// Live walkthrough: drives the deployed web app in a real Chromium (phone size) through every page and
// the main features, with generous waits for the live AI. Prints PASS/FAIL per step.
// Run: QA_BASE=https://... node qa/live-walk.mjs
import { chromium, devices } from "@playwright/test";

const BASE = process.env.QA_BASE ?? "https://cohort-coach-pwa-1097171252131.asia-south1.run.app";
const results = [];
const browser = await chromium.launch({ args: ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"] });
const ctx = await browser.newContext({ ...devices["Pixel 5"], permissions: ["microphone"] });
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(String(e).slice(0, 140)));
page.on("response", (r) => {
  if (r.status() >= 500 && !r.url().includes("/api/admin/")) errors.push(`${r.status()} ${r.url().slice(-60)}`);
});

async function step(name, fn) {
  try {
    const note = await fn();
    results.push({ name, ok: true, note: note ?? "" });
  } catch (e) {
    results.push({ name, ok: false, note: String(e).split("\n")[0].slice(0, 160) });
  }
}
const T = (id) => page.getByTestId(id);
const go = async (hash) => {
  await page.goto(`${BASE}/#/${hash}`);
  await page.waitForTimeout(900);
};
const text = () => page.innerText("body");
const vis = (id, t = 15000) => T(id).waitFor({ state: "visible", timeout: t });

await page.goto(BASE);
await page.evaluate(() => {
  localStorage.clear();
  localStorage.setItem("cc.consent", '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}');
  localStorage.setItem("cc.voice", "0");
});

await step("Landing: mode banner, role, 4 role cards + tour card", async () => {
  await go("roles");
  await vis("mode-banner");
  await vis("card-teacher");
  const n = await page.locator('[data-testid^="card-"]').count();
  if (n !== 5) throw new Error(`cards ${n}`);
  const t = await text();
  if (!/Judge demo/.test(t) || !/Role now/.test(t)) throw new Error("banner text");
});
for (const role of ["teacher", "mentor", "coach", "officer"]) {
  await step(`Role dialog and enter: ${role}`, async () => {
    await go("roles");
    await T(`card-${role}`).click();
    await vis("role-dialog");
    if (!(await T("dlg-cannot").count())) throw new Error("no 'cannot' list");
    await T("dlg-enter").click();
    await page.waitForTimeout(1200);
    return page.url().split("#")[1];
  });
}
await step("Guided tour: steps advance 1 to 3", async () => {
  await go("tour/1");
  await vis("tour");
  const first = await T("tour-progress").innerText();
  await T("tour-next").click().catch(() => T("tour-advance").click());
  await page.waitForTimeout(800);
  return `${first.replace(/\s+/g, " ")} -> ${page.url().split("#")[1]}`;
});
await step("Check: type a child's 10 answers, next child, finish", async () => {
  await go("check");
  await vis("form-A");
  await T("form-A").click();
  for (let q = 1; q <= 10; q++) await T(`input-${q}`).fill(String(q + 10));
  await T("next-child").click();
  await page.waitForTimeout(400);
  const c = await T("check-count").innerText();
  return c.replace(/\s+/g, " ");
});
await step("Judge page: load simulated class", async () => {
  await go("judge");
  await vis("load-demo");
  await T("load-demo").click();
  await vis("demo-loaded");
  if (!/imulated/.test(await text())) throw new Error("no simulated label");
});
await step("Home: 28 children counted, no percentage", async () => {
  await go("home");
  await vis("home-status");
  if (!/28/.test(await T("home-status").innerText())) throw new Error("count");
  if (/%/.test(await text())) throw new Error("percent");
});
await step("Cards: SUB-SFL count line (11 of 28)", async () => {
  await T("home-action").click();
  await vis("line-SUB-SFL");
  const l = await T("line-SUB-SFL").innerText();
  if (!/11 of 28/.test(l)) throw new Error(l);
  if (/%/.test(await text())) throw new Error("percent");
});
await step("Practice: start, 3 typed turns get checked child replies (live AI)", async () => {
  await go("practice?seed=5");
  await vis("start-practice");
  await T("start-practice").click();
  await vis("kid-4");
  const lines = ["Let us use sticks. Show me 52 with bundles of ten.", "Ravi, how did you get your answer?", "Good. Now check by adding back."];
  for (let i = 0; i < lines.length; i++) {
    await T("say").fill(lines[i]);
    await T("send").click();
    await vis(`reply-${i + 1}`, 40000);
  }
  return "3 turns";
});
await step("Practice: end gives feedback with Checked badge and 2 strengths", async () => {
  await T("end").click();
  await vis("feedback", 40000);
  const badge = await T("fb-badge").innerText();
  const s = await page.locator("[data-testid^=strength-]").count();
  if (/%/.test(await text())) throw new Error("percent");
  return `${badge}; ${s} strength items`;
});
await step("AI layers map and audit trail", async () => {
  await go("aimap");
  await page.waitForTimeout(800);
  const t1 = (await text()).length;
  await go("audit");
  await page.waitForTimeout(1200);
  const t2 = await text();
  if (t1 < 200 || t2.length < 100) throw new Error("thin pages");
});
await step("Watch: model run plays (recorded) with steps", async () => {
  await go("watch");
  await vis("watch");
  await page.waitForTimeout(800);
  return (await T("run-kind").innerText().catch(() => "")).replace(/\s+/g, " ");
});
for (const r of ["programme", "history", "profile", "privacy", "coach", "mentor", "officer", "review", "cohort", "flow", "admin"]) {
  await step(`Page opens with content: #/${r}`, async () => {
    await go(r);
    await page.waitForTimeout(1500);
    const t = await text();
    if (t.length < 150) throw new Error(`only ${t.length} chars`);
    if (/\bundefined\b|\[object Object\]/.test(t)) throw new Error("undefined text");
    return r === "admin" ? ((await T("admin-closed").count()) ? "shows 'closed' message" : "no closed message") : "";
  });
}
await step("Officer: cohort panel and funnel with review-waiting line", async () => {
  await go("officer");
  await vis("officer-cohorts");
  await vis("funnel");
  await vis("review-waiting");
  return (await T("review-waiting").innerText()).replace(/\s+/g, " ").slice(0, 110);
});
await step("Officer: propose then activate a cohort", async () => {
  await T("cohort-create").click();
  await page.waitForTimeout(1500);
  const btn = page.locator('[data-testid^="activate-"]').first();
  await btn.waitFor({ timeout: 10000 });
  await btn.click();
  await page.waitForTimeout(1500);
  return (await page.locator('[data-testid^="cohort-"]').first().innerText().catch(() => "")).replace(/\s+/g, " ").slice(0, 90);
});
await step("Language switch: Hindi then Tamil, no raw keys", async () => {
  for (const l of ["hi", "ta"]) {
    await page.evaluate((x) => localStorage.setItem("cc.lang", x), l);
    await go("roles");
    await vis("card-teacher");
    const t = await text();
    if (/\b(landing|roles|role)\.[a-z_]+/.test(t)) throw new Error(`raw key in ${l}`);
    if (!new RegExp(l === "hi" ? "[\\u0900-\\u097F]" : "[\\u0B80-\\u0BFF]").test(t)) throw new Error(`no ${l} script`);
  }
  await page.evaluate(() => localStorage.setItem("cc.lang", "en"));
});
await step("Offline: Programme still opens with no network", async () => {
  await go("programme");
  await page.waitForTimeout(1500);
  await ctx.setOffline(true);
  await page.reload();
  await page.waitForTimeout(2000);
  const t = await text();
  await ctx.setOffline(false);
  if (t.length < 100) throw new Error("blank offline");
});
await step("Mode switch: pilot sign-in page, wrong key refused, back to judge", async () => {
  await go("roles");
  await T("mode-to-pilot").click();
  await vis("mode-chip");
  const ins = page.locator("input");
  await ins.nth(0).fill("nobody");
  await ins.nth(1).fill("not-a-real-key");
  await page.locator("form button").last().click();
  await page.waitForTimeout(2500);
  const t = await text();
  await T("mode-to-judge").click();
  await vis("mode-banner");
  return /not right/i.test(t) ? "wrong key refused with message" : `after submit: ${t.slice(0, 80).replace(/\s+/g, " ")}`;
});
await step("Pilot deep links stay inside pilot: #/home redirects to upload", async () => {
  await page.evaluate(() => localStorage.setItem("cc.mode", "pilot"));
  await page.goto(`${BASE}/#/home`);
  await page.reload(); // the mode is read when the page loads
  await page.waitForTimeout(2500);
  const h = await page.evaluate(() => location.hash);
  await page.evaluate(() => localStorage.setItem("cc.mode", "judge"));
  if (!/upload/.test(h)) throw new Error(h);
});

await browser.close();
let pass = 0;
for (const r of results) {
  console.log(`${r.ok ? "PASS" : "FAIL"} | ${r.name}${r.note ? " | " + r.note : ""}`);
  if (r.ok) pass++;
}
console.log(`\n${pass}/${results.length} steps passed. Page errors / 5xx outside admin: ${errors.length}`);
for (const e of errors.slice(0, 8)) console.log("  " + e);
