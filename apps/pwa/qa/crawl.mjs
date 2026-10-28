// Browser QA crawl: opens every route in a real Chromium against a running build and API, in each
// language and at phone and desktop widths, and records what it finds. Output: a JSON report and
// screenshots. Run: node qa/crawl.mjs <outDir>   (web on :4173, api on :8011)
import { chromium, devices } from "@playwright/test";
import fs from "node:fs";

const out = process.argv[2] ?? "qa-out";
fs.mkdirSync(out, { recursive: true });
const ROUTES = ["roles", "judge", "home", "check", "cards", "practice", "programme", "history", "aimap", "audit", "profile", "privacy", "admin", "coach", "mentor", "flow", "officer", "watch", "tour", "tour/2", "review", "cohort"];
const LANGS = ["en", "hi", "ta"];
const VIEWS = { phone: { ...devices["Pixel 5"], viewport: { width: 360, height: 740 } }, desktop: { viewport: { width: 1280, height: 800 } } };
const base = process.env.QA_BASE ?? "http://localhost:4173";
const teacherRoutes = new Set(["home", "check", "cards", "practice", "history", "flow", "watch", "tour", "tour/2", "profile", "programme"]);
const rows = [];
const browser = await chromium.launch();
for (const [vname, vopts] of Object.entries(VIEWS)) {
  for (const lang of LANGS) {
    const ctx = await browser.newContext({ ...vopts, permissions: ["microphone"] });
    await ctx.addInitScript((l) => {
      try { localStorage.setItem("cc.lang", l); localStorage.setItem("cc.role", "officer"); } catch { /* ignore */ }
    }, lang);
    for (const r of ROUTES) {
      const page = await ctx.newPage();
      const issues = [];
      const errors = [];
      const bad = [];
      page.on("pageerror", (e) => errors.push(String(e).slice(0, 160)));
      page.on("console", (m) => { if (m.type() === "error") errors.push(m.text().slice(0, 160)); });
      page.on("response", (res) => { if (res.status() >= 500 || (res.status() === 404 && res.url().includes("/api/"))) bad.push(`${res.status()} ${res.url().replace(base, "")}`); });
      const t0 = Date.now();
      try {
        await page.goto(`${base}/#/${r}`, { waitUntil: "load" });
        await page.waitForTimeout(1200);
        const info = await page.evaluate(() => {
          const el = document.scrollingElement;
          const txt = document.body.innerText;
          const small = [...document.querySelectorAll("button, a[href], [role=button]")].filter((b) => { const x = b.getBoundingClientRect(); return x.width > 0 && (x.height < 40 || x.width < 40); }).length;
          return { txt, overflow: el.scrollWidth > el.clientWidth + 2, small, len: txt.length, title: document.title };
        });
        if (info.len < 20) issues.push("blank or near-blank page");
        if (info.overflow) issues.push("horizontal scroll");
        if (/\bundefined\b|\bNaN\b|\[object Object\]/.test(info.txt)) issues.push("undefined/NaN/[object Object] in text");
        if (/\b[a-z]+\.[a-z_]+\.[a-z_]+\b/.test(info.txt.replace(/\S+@\S+/g, "")) && /(^|\s)(cohort|officer|flow|nav|home|check|cards)\.[a-z_]+/.test(info.txt)) issues.push("raw string key visible");
        if (teacherRoutes.has(r) && /\d\s?%|percent|प्रतिशत|சதவீதம்/i.test(info.txt)) issues.push("percentage on a teacher screen");
        if (vname === "phone" && info.small > 0) issues.push(`${info.small} tap targets under 40px`);
        if (errors.length) issues.push(`console/page errors: ${errors.length}`);
        if (bad.length) issues.push(`bad API responses: ${bad.join(", ")}`);
        const file = `${out}/${vname}-${lang}-${r.replace("/", "_")}.png`;
        if (lang === "en" || r === "roles") await page.screenshot({ path: file });
        rows.push({ route: r, view: vname, lang, ms: Date.now() - t0, chars: info.len, simulated: /simulated|सिम्युलेटेड|अनुकरण|உருவகப்படுத்த/i.test(info.txt), issues, errors: errors.slice(0, 2), bad });
      } catch (e) {
        rows.push({ route: r, view: vname, lang, issues: [`crawl failed: ${String(e).slice(0, 120)}`], errors: [], bad: [] });
      }
      await page.close();
    }
    await ctx.close();
  }
}
await browser.close();
fs.writeFileSync(`${out}/report.json`, JSON.stringify(rows, null, 1));
const withIssues = rows.filter((x) => x.issues.length);
console.log(`pages checked: ${rows.length}, with issues: ${withIssues.length}`);
for (const x of withIssues) console.log(`${x.view}/${x.lang} #/${x.route}: ${x.issues.join("; ")}${x.errors[0] ? ` | ${x.errors[0]}` : ""}`);
