// Starts a Practice Class session against the built app, takes one typed turn, and screenshots it.
// Run: node qa/practice-shots.mjs <outDir> <base> [lang] [dark]
import { chromium } from "@playwright/test";
const [, , out = "out", base = "http://localhost:4174", lang = "en", dark = "0"] = process.argv;
const CONSENT = '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}';
const b = await chromium.launch();
for (const [w, h] of [[360, 800], [1280, 800]]) {
  const ctx = await b.newContext({ viewport: { width: w, height: h }, colorScheme: dark === "1" ? "dark" : "light" });
  await ctx.addInitScript(([l, c]) => { localStorage.setItem("cc.lang", l); localStorage.setItem("cc.role", "teacher"); localStorage.setItem("cc.consent", c); }, [lang, CONSENT]);
  const p = await ctx.newPage();
  await p.goto(`${base}/#/practice?seed=5`);
  await p.getByTestId("start-practice").click();
  await p.getByTestId("say").waitFor({ timeout: 15000 }).catch(() => {});
  if (await p.getByTestId("use-text").count()) await p.getByTestId("use-text").click();
  await p.waitForTimeout(500);
  const say = p.getByTestId("say");
  if (await say.count()) { await say.fill("Show me 52 with bundles of ten."); await p.getByTestId("send").click(); await p.waitForTimeout(4000); }
  await p.screenshot({ path: `${out}/practice_${w}x${h}_${lang}${dark === "1" ? "_dark" : ""}.png` });
  await ctx.close();
}
await b.close();
