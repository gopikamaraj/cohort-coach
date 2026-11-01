// Runs axe-core on every route, light and dark, at phone and desktop width.
// Run: node qa/axe.mjs <base> <axeFile> <outJson>   (axe-core is not a project dependency: pass its axe.min.js)
import { chromium } from "@playwright/test";
import fs from "node:fs";

const [, , base = "http://localhost:4174", axeFile, out = "axe.json"] = process.argv;
const axeSrc = fs.readFileSync(axeFile, "utf8");
const ROUTES = (process.env.ONLY ? process.env.ONLY.split(",") : ["roles", "tour", "judge", "home", "check", "cards", "practice", "programme", "history", "aimap", "audit", "profile", "privacy", "flow", "watch", "review", "cohort", "mentor", "coach", "officer", "assistant", "styleguide"]);
const roleFor = (r) => (["coach", "review", "cohort"].includes(r) ? "coach" : r === "officer" ? "officer" : r === "mentor" ? "mentor" : "teacher");
const rows = [];
const browser = await chromium.launch();
for (const scheme of ["light", "dark"]) {
  for (const w of [360, 1280]) {
    const ctx = await browser.newContext({ viewport: { width: w, height: 800 }, colorScheme: scheme });
    for (const r of ROUTES) {
      await ctx.addInitScript(([ro]) => { try { localStorage.setItem("cc.lang", "en"); localStorage.setItem("cc.role", ro); } catch { /* ignore */ } }, [roleFor(r)]);
      const page = await ctx.newPage();
      await page.goto(`${base}/#/${r}`, { waitUntil: "load" });
      await page.waitForTimeout(700);
      await page.evaluate(axeSrc);
      const res = await page.evaluate(() => window.axe.run(document, { runOnly: ["wcag2a", "wcag2aa", "wcag21aa", "best-practice"] }));
      for (const v of res.violations) rows.push({ route: r, w, scheme, id: v.id, impact: v.impact, nodes: v.nodes.length, help: v.help });
      await page.close();
    }
    await ctx.close();
  }
}
await browser.close();
fs.writeFileSync(out, JSON.stringify(rows, null, 1));
const byId = {};
for (const x of rows) byId[x.id] = (byId[x.id] ?? 0) + 1;
console.log(rows.length, "violations", JSON.stringify(byId));
