import AxeBuilder from "@axe-core/playwright";
import { type Page } from "@playwright/test";
import { expect, test } from "./test";

// Two classes to a cohort, across roles, on the real API (recorded AI answers, the stub voice):
// T1 enters 3A and waits, T2 enters 3B and the cohort forms, the coach approves lesson 1, T1 marks
// it heard and answers Not yet, presses Generate next lesson, the coach approves lesson 2, T2 asks in
// the chat with a made-up child's name (masked), the coach answers, T1 sees it shared, a question
// typed offline is sent once back online, and the coach's Cohorts view shows the counts. Simulated.

const CONSENT = '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}';
// "Meena writes 365 for 703 minus 468. What should I do?" in Hindi (T2 writes Hindi); Meena is made up
const NAME = "मीना";
const QUESTION_HI = `${NAME} 703 में से 468 घटाने पर 365 लिखती है। मैं क्या करूँ?`;
// "Ask the child to show it with bundles of ten."
const REPLY_HI = "बच्चे से दस की गड्डियों से दिखाने को कहें।";

async function fresh(page: Page) {
  await page.goto("/");
  await page.evaluate((c) => {
    (((u: (string | null)[]) => (localStorage.clear(), u[0] && localStorage.setItem("cc.user", u[0]), u[1] && localStorage.setItem("cc.cacheOwner", u[1])))([localStorage.getItem("cc.user"), localStorage.getItem("cc.cacheOwner")]));
    localStorage.setItem("cc.consent", c);
    localStorage.setItem("cc.role", "judge");
    localStorage.setItem("cc.lang", "en");
  }, CONSENT);
}

async function at(page: Page, step: number, who: string) {
  await page.goto(`/#/two-classes?step=${step}&as=${who}`);
  await page.getByTestId("run-as").selectOption(who);
  await expect(page.getByTestId("run-busy")).toHaveCount(0);
}

async function axe(page: Page) {
  const found = (await new AxeBuilder({ page }).include('[data-testid="two-classes"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations;
  expect(found.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`)).toEqual([]);
}

test("two classes form a cohort, then lesson 1, feedback, the next lesson, the chat and the coach's view", async ({ page, context }) => {
  test.setTimeout(240_000);
  const posts: string[] = [];
  page.on("request", (r) => {
    if (r.method() === "POST" && r.url().includes("/api/cohort-run/")) posts.push(r.postData() ?? "");
  });
  await fresh(page);

  // Flow 1: T1 submits 3A and waits; T2 submits 3B and the cohort forms by itself
  await at(page, 1, "T1");
  await expect(page.getByText("Simulated", { exact: false }).first()).toBeVisible();
  await page.getByTestId("run-submit-3A").click();
  await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "waiting_for_classes");
  await expect(page.getByTestId("run-status")).toContainText("1 of 2");
  await expect(page.getByTestId("run-reason-SUB-SFL")).toContainText("4 of 16");
  await axe(page);
  await page.getByTestId("run-as").selectOption("T2");
  await page.getByTestId("run-submit-3B").click();
  await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "formed", { timeout: 60_000 }); // drafts and voices lesson 1
  await expect(page.getByTestId("run-cohort")).toContainText("2 classes, 2 teachers");
  await expect(page.getByTestId("run-label")).toHaveText(["Pilot cohort, two classes", "Based on one question per child"]);
  await expect(page.getByTestId("run-reason-ADD-NOCARRY")).toContainText("under 1 in 4");
  await expect(page.getByTestId("run-mentor")).toContainText("No mentor suggestion");
  // nothing per child ever left the page: the synthetic sheets are made on the server, counts only
  expect(posts.join(" ")).not.toMatch(/rows|roll/);

  // Flow 2: lesson 1 waits for the coach, in each teacher's language
  await at(page, 2, "T1");
  await expect(page.getByTestId("run-lesson-waiting")).toBeVisible();
  await at(page, 2, "C1");
  await expect(page.getByTestId("run-cl-L1-en")).toContainText("Waiting for the coach");
  await expect(page.getByTestId("run-cl-L1-hi")).toBeVisible();
  await page.getByTestId("run-approve-L1-en").click();
  await expect(page.getByTestId("run-cl-L1-en")).toContainText("Released");
  await page.getByTestId("run-approve-L1-hi").click();
  await expect(page.getByTestId("run-cl-L1-hi")).toContainText("Released");
  await axe(page);

  // Flow 3: T1 marks it heard, answers Not yet with a note naming a child, and gets her next lesson
  await at(page, 3, "T1");
  const l1 = page.getByTestId("run-lesson-L1-en");
  await expect(l1.getByTestId("run-script")).toContainText("of 16");
  await l1.getByTestId("run-heard").click();
  await page.getByTestId("run-fb-note").fill("Meena still writes 365");
  await page.getByTestId("run-fb-not_yet").click();
  await expect(page.getByTestId("run-fb-saved")).toContainText("Not yet");
  await page.getByTestId("run-next").click();
  const l2 = page.getByTestId("run-lesson-L2-T1");
  await expect(l2.getByTestId("run-decision")).toHaveAttribute("data-mode", "other_approach", { timeout: 60_000 });
  await expect(l2.getByTestId("run-decision")).toContainText("another approach");
  await expect(l2.getByTestId("run-lesson-waiting")).toBeVisible();
  await axe(page);
  await at(page, 3, "C1");
  await page.getByTestId("run-approve-L2-T1").click();
  await expect(page.getByTestId("run-cl-L2-T1")).toContainText("Released");
  await at(page, 3, "T1");
  await expect(page.getByTestId("run-lesson-L2-T1").getByTestId("run-script")).toBeVisible();

  // Flow 4: T2 asks with a made-up name and shares it; the name is masked; an outsider is kept out
  await at(page, 4, "T3");
  await expect(page.getByTestId("run-chat-msg")).toContainText("not in the cohort");
  await at(page, 4, "T2");
  await page.getByTestId("run-chat-text").fill(QUESTION_HI);
  await page.getByTestId("run-chat-send").click();
  const mine = page.getByTestId("run-mine");
  await expect(mine).toContainText("[child]");
  await expect(mine).not.toContainText(NAME);
  await at(page, 4, "C1");
  const pending = page.getByTestId("run-pending");
  await expect(pending).toContainText("[child]");
  await expect(pending).not.toContainText(NAME);
  await page.getByTestId("run-own").fill(REPLY_HI);
  await page.getByTestId("run-send-own").click();
  await expect(page.getByTestId("run-pending")).toHaveCount(0);
  await at(page, 4, "T1");
  await expect(page.getByTestId("run-shared")).toContainText(REPLY_HI);
  await expect(page.getByTestId("run-shared")).not.toContainText(NAME);

  // a question typed offline waits in the outbox and goes once she is back online
  await context.setOffline(true);
  await page.getByTestId("run-chat-text").fill("How long should the bundles activity take?");
  await page.getByTestId("run-chat-send").click();
  await expect(page.getByTestId("run-chat-queued")).toContainText("1 question");
  await context.setOffline(false);
  await expect(page.getByTestId("run-chat-queued")).toHaveCount(0, { timeout: 20_000 });
  await expect(page.getByTestId("run-mine")).toContainText("bundles activity");

  // Flow 5: the coach's Cohorts view, counts only; a mentor of another cohort sees nothing
  await at(page, 5, "C1");
  const cohort = page.getByTestId("run-coach-cohort");
  await expect(cohort).toContainText("9 of 34 children");
  await expect(page.getByTestId("run-coach-fb")).toContainText("tried 0, partly 0, not yet 1");
  await expect(page.getByTestId("run-coach-l2")).toContainText("Released 1");
  await expect(page.getByTestId("run-coach-chat")).toContainText("1 open");
  await expect(page.getByTestId("run-timeline")).toContainText("Cohort formed");
  await expect(cohort).not.toContainText("Meena");
  await axe(page);
  await at(page, 5, "M2");
  await expect(page.getByTestId("run-mentor-empty")).toBeVisible();
  await at(page, 5, "officer");
  await expect(page.getByTestId("run-officer")).toContainText("hidden");
});
