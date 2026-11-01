// Renders every route at phone and desktop size; used for the before/after audit.
// Run: node qa/audit-shots.mjs <outDir> [base]   (web build served at base, judge API behind it)
import { chromium } from "@playwright/test";
import fs from "node:fs";

const out = process.argv[2] ?? "audit-out";
const base = process.argv[3] ?? "http://localhost:4173";
fs.mkdirSync(out, { recursive: true });
const ROUTES = ["roles", "tour", "judge", "home", "check", "cards", "practice", "programme", "history", "aimap", "audit", "profile", "privacy", "flow", "watch", "review", "cohort", "mentor", "coach", "officer", "assistant"];
const MAIN = new Set(["roles", "home", "check", "practice", "officer", "assistant"]);
const SIZES = { "360x800": { width: 360, height: 800 }, "1280x800": { width: 1280, height: 800 } };
const roleFor = (r) => (["coach", "review"].includes(r) ? "coach" : r === "officer" ? "officer" : r === "mentor" ? "mentor" : "teacher");
const report = [];
const browser = await chromium.launch();
for (const [sname, viewport] of Object.entries(SIZES)) {
  for (const lang of ["en", "hi", "ta"]) {
    const ctx = await browser.newContext({ viewport });
    for (const r of ROUTES) {
      if (lang !== "en" && !MAIN.has(r)) continue;
      await ctx.addInitScript(([l, role]) => { try { localStorage.setItem("cc.lang", l); localStorage.setItem("cc.role", role); } catch { /* ignore */ } }, [lang, roleFor(r)]);
      const page = await ctx.newPage();
      await page.goto(`${base}/#/${r}`, { waitUntil: "load" });
      await page.waitForTimeout(900);
      const m = await page.evaluate(() => {
        const el = document.scrollingElement;
        const main = document.querySelector("main");
        const small = [...document.querySelectorAll("button, a[href], [role=button], input, select")].filter((b) => { const x = b.getBoundingClientRect(); return x.width > 0 && (x.height < 44 || x.width < 44); }).length;
        const sizes = new Set([...document.querySelectorAll("body *")].map((n) => getComputedStyle(n).fontSize));
        return { overflowX: el.scrollWidth > el.clientWidth + 2, small, fontSizes: sizes.size, mainHeight: main ? main.scrollHeight : 0 };
      });
      report.push({ route: r, size: sname, lang, ...m });
      await page.screenshot({ path: `${out}/${r}_${sname}_${lang}.png` });
      await page.close();
    }
    await ctx.close();
  }
}
await browser.close();
fs.writeFileSync(`${out}/metrics.json`, JSON.stringify(report, null, 1));
console.log(`${report.length} screenshots, ${report.filter((x) => x.overflowX).length} with sideways scroll`);
