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
    await page.evaluate(() => {
    localStorage.clear();
    localStorage.setItem("cc.consent", '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}');
    localStorage.setItem("cc.voice", "0"); // these tests type; e2e/voice.spec.ts covers speaking
  });
    await page.goto("/#/roles");
    await page.getByTestId(`lang-${lang}`).click();
    await page.goto("/#/judge");
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
  await page.evaluate(() => {
    localStorage.clear();
    localStorage.setItem("cc.consent", '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}');
    localStorage.setItem("cc.voice", "0"); // these tests type; e2e/voice.spec.ts covers speaking
  });
  await page.goto("/#/judge");
  await page.getByTestId("load-demo").click();
  await page.goto("/#/cards");
  await expect(page.getByTestId("card-SUB-SFL")).toBeVisible();
  await page.screenshot({ path: `${OUT}desktop-frame.png` });
});

test("Practice Class screenshots: intro, a turn with the AI layers, feedback, AI map, audit", async ({ page }) => {
  mkdirSync(OUT, { recursive: true });
  await page.goto("/");
  await page.evaluate(() => {
    localStorage.clear();
    localStorage.setItem("cc.consent", '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}');
    localStorage.setItem("cc.voice", "0"); // these tests type; e2e/voice.spec.ts covers speaking
  });
  await page.goto("/#/practice?seed=5");
  await page.screenshot({ path: `${OUT}en-5-practice-intro.png` });
  await page.getByTestId("start-practice").click();
  await expect(page.getByTestId("kid-4")).toBeVisible();
  for (const line of ["Priya, what is 52 minus 29?", "Tell me how you got that."]) {
    await page.getByTestId("say").fill(line);
    await page.getByTestId("send").click();
  }
  await expect(page.getByTestId("reply-2")).toBeVisible();
  await page.getByTestId("side-judge").click();
  await page.getByTestId("layers-toggle").click();
  await page.getByTestId("trace-2").getByTestId("layers-panel").scrollIntoViewIfNeeded();
  await page.getByTestId("trace-2").getByTestId("layer-output").scrollIntoViewIfNeeded();
  await page.screenshot({ path: `${OUT}en-6-practice-layers.png` });
  await page.getByTestId("layers-toggle").click();
  await page.getByTestId("side-turn").click();
  await page.getByTestId("tap-bundles").click();
  await page.getByTestId("say").fill("Priya, you only have 2 loose ones. Open a bundle to exchange it for ten sticks.");
  await page.getByTestId("send").click();
  await page.getByTestId("say").fill("Let us check by adding back. What is 23 plus 29?");
  await page.getByTestId("send").click();
  await page.getByTestId("say").fill("Priya, now try 74 minus 46.");
  await page.getByTestId("send").click();
  await page.getByTestId("say").fill("Well done, thank you for trying.");
  await page.getByTestId("send").click();
  await expect(page.getByTestId("reply-7")).toBeVisible();
  await page.getByTestId("end").click();
  await expect(page.getByTestId("feedback")).toBeVisible();
  await page.screenshot({ path: `${OUT}en-7-practice-feedback.png` });
  await page.goto("/#/aimap");
  await expect(page.getByTestId("ai-map")).toBeVisible();
  await page.screenshot({ path: `${OUT}en-8-aimap.png` });
  await page.goto("/#/audit");
  await expect(page.getByTestId("audit-table")).toBeVisible();
  await page.screenshot({ path: `${OUT}en-9-audit.png` });
});

for (const lang of ["hi", "ta"] as const) {
  test(`Practice Class intro in ${lang}`, async ({ page }) => {
    mkdirSync(OUT, { recursive: true });
    await page.goto("/");
    await page.evaluate(() => {
    localStorage.clear();
    localStorage.setItem("cc.consent", '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}');
    localStorage.setItem("cc.voice", "0"); // these tests type; e2e/voice.spec.ts covers speaking
  });
    await page.goto("/#/roles");
    await page.getByTestId(`lang-${lang}`).click();
    await page.goto("/#/practice");
    await page.screenshot({ path: `${OUT}${lang}-5-practice-intro.png` });
  });
}
