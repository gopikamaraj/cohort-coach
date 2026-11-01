import { expect, test, type Page } from "@playwright/test";
import { chooseLanguage } from "./switch";

// The Practice Class review tab (rehearsals recorded on this phone, replayed, tagged by her), the
// cue card of things to say, and the language. The API replays a recording made on 2026-10-17
// (seed 5), so no paid call is made.

const LINES = [
  "Priya, what is 52 minus 29?",
  "Tell me how you got that.",
  "/tap bundles",
  "Priya, you only have 2 loose ones. Open a bundle to exchange it for ten sticks.",
  "Let us check by adding back. What is 23 plus 29?",
  "Priya, now try 74 minus 46.",
  "Well done, thank you for trying.",
];

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => {
    localStorage.clear();
    localStorage.setItem("cc.consent", '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}');
    localStorage.setItem("cc.voice", "0");
  });
});

async function rehearse(page: Page, count = LINES.length) {
  await page.goto("/#/practice?seed=5");
  await page.getByTestId("start-practice").click();
  await expect(page.getByTestId("kid-4")).toBeVisible();
  let n = 0;
  for (const line of LINES.slice(0, count)) {
    n += 1;
    if (line.startsWith("/tap ")) {
      await page.getByTestId(`tap-${line.slice(5)}`).click();
    } else {
      await page.getByTestId("say").fill(line);
      await page.getByTestId("send").click();
    }
    await expect(page.getByTestId(`reply-${n}`)).toBeVisible();
  }
}

test("a rehearsal is recorded on the phone, tagged by her, replayed turn by turn, and can be deleted", async ({ page }) => {
  const outgoing: string[] = [];
  page.on("request", (r) => {
    if (r.method() === "POST") outgoing.push(r.url());
  });
  await rehearse(page);
  await page.getByTestId("end").click();
  await expect(page.getByTestId("impact")).toBeVisible();
  await page.getByTestId("impact-positive").click();
  await expect(page.getByTestId("impact-positive")).toHaveAttribute("aria-pressed", "true");

  await page.getByTestId("tab-review").click();
  await expect(page.getByTestId("review-item")).toHaveCount(1);
  await expect(page.getByTestId("review-impact")).toHaveText("It helped");
  await expect(page.getByTestId("review-summary")).toContainText("Rehearsals: 1. Helped: 1.");
  expect(await page.locator("body").innerText()).not.toMatch(/%/);

  await page.getByTestId("review-item").click();
  await expect(page.getByTestId("replay-count")).toHaveText("Turn 1 of 7");
  await expect(page.getByTestId("replay-turn-1")).toContainText("Priya, what is 52 minus 29?");
  await expect(page.getByTestId("replay-turn-2")).toHaveCount(0);
  await page.getByTestId("replay-next").click();
  await expect(page.getByTestId("replay-turn-2")).toContainText("Tell me how you got that.");
  await expect(page.getByTestId("replay-count")).toHaveText("Turn 2 of 7");
  await page.getByTestId("replay-prev").click();
  await expect(page.getByTestId("replay-turn-2")).toHaveCount(0);
  await expect(page.getByTestId("moves-used")).toBeVisible();
  await expect(page.getByTestId("review-feedback")).toBeVisible();

  await page.getByTestId("impact-none").click(); // she changes her mind
  await page.getByTestId("review-back").click();
  await expect(page.getByTestId("review-impact")).toHaveText("No difference");

  // nothing was sent anywhere because of the review: only practice calls went out
  for (const url of outgoing) expect(url).toMatch(/\/api\/practice\/sessions(\/[^/]+\/(turns|end))?$/);

  await page.getByTestId("review-item").click();
  page.once("dialog", (d) => void d.accept());
  await page.getByTestId("review-delete").click();
  await expect(page.getByTestId("review-empty")).toBeVisible();
});

test("again from the review restarts with the same children", async ({ page }) => {
  await rehearse(page, 2);
  await page.getByTestId("tab-review").click();
  await page.getByTestId("review-item").click();
  await page.getByTestId("review-again").click();
  await expect(page.getByTestId("kid-4")).toBeVisible();
  await expect(page.getByTestId("turn-counter")).toContainText("Turn 0 of 40");
});

test("the cue card offers things to say, never a scolding, and a tap puts the line in the box", async ({ page }) => {
  await page.goto("/#/practice?seed=5");
  await page.getByTestId("start-practice").click();
  await expect(page.getByTestId("kid-4")).toBeVisible();
  await expect(page.getByTestId("cue-panel")).toHaveCount(0);
  await page.getByTestId("cue-toggle").click();
  await expect(page.getByTestId("cue-panel")).toBeVisible();
  const lines = await page.getByTestId("cue-line").allInnerTexts();
  expect(lines.length).toBeGreaterThanOrEqual(5);
  expect(lines.join(" ")).not.toMatch(/scold|stupid|shut up/i);
  await expect(page.getByTestId("cue-panel")).toContainText("How to say it");
  await page.getByTestId("cue-line").first().click();
  await expect(page.getByTestId("cue-panel")).toHaveCount(0);
  await expect(page.getByTestId("say")).toHaveValue(lines[0]!);
});

test("the language switch changes the practice screen, and the next rehearsal is in the new language", async ({ page }) => {
  const created: string[] = [];
  page.on("request", (r) => {
    if (/\/api\/practice\/sessions$/.test(r.url())) created.push(JSON.parse(r.postData() ?? "{}").language as string);
  });
  await page.goto("/#/practice?seed=5");
  await chooseLanguage(page, "hi");
  await expect(page.getByTestId("goal-intro")).toContainText("उन बच्चों की मदद करें");
  await expect(page.getByTestId("tab-practise")).toHaveText("अभ्यास");
  await page.getByTestId("start-practice").click();
  await expect(page.getByTestId("goal")).toContainText("क्या अभ्यास करना है");
  await page.getByTestId("cue-toggle").click();
  await expect(page.getByTestId("cue-panel")).toContainText("कैसे कहें");
  expect(await page.getByTestId("cue-line").first().innerText()).toMatch(/[ऀ-ॿ]/); // Hindi lines

  await chooseLanguage(page, "ta");
  await page.getByTestId("start-practice").click();
  await expect(page.getByTestId("goal")).toContainText("என்ன பயிற்சி செய்ய வேண்டும்");
  expect(created).toEqual(["hi", "ta"]);
});

test("teacher screens show no English words in Hindi or Tamil", async ({ page }) => {
  test.setTimeout(120_000);
  const allowed = new Set(["English"]); // the language names in the switch
  for (const lang of ["hi", "ta"]) {
    for (const route of ["home", "check", "practice", "programme", "history"]) {
      await page.goto("/");
      await page.evaluate((l) => {
        localStorage.clear();
        localStorage.setItem("cc.consent", '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}');
        localStorage.setItem("cc.lang", l);
        localStorage.setItem("cc.voice", "0");
      }, lang);
      await page.goto(route === "practice" ? "/#/practice?seed=5" : `/#/${route}`);
      await page.reload();
      if (route === "check") {
        await page.getByTestId("start-check").or(page.getByTestId("child-title")).first().waitFor();
      }
      let text = "";
      if (route === "practice") {
        await page.getByTestId("start-practice").click();
        await page.getByTestId("cue-toggle").click();
        text += await page.evaluate(() => document.body.innerText);
        // the rest of a running rehearsal sits on the same page
        await expect(page.getByTestId("tap-bundles")).toBeVisible();
        text += await page.evaluate(() => document.body.innerText);
        await expect(page.getByTestId("goal")).toBeVisible();
      }
      text += await page.evaluate(() => document.body.innerText);
      const words = [...new Set(text.match(/[A-Za-z][A-Za-z'’-]{2,}/g) ?? [])].filter((w) => !allowed.has(w));
      expect(words, `${lang}/${route}`).toEqual([]);
    }
  }
});
