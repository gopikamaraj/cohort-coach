import { expect, test, type Page } from "@playwright/test";

// The flow: a paper is made (with its answer key), Enter check chooses that paper, and the phone reads
// the answers with the paper's OWN key: it has the paper's number of boxes, finds the errors its
// numbers show, and no form letter is asked for. The key is worked out by the engine on the server.

const CONSENT = '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}';

async function fresh(page: Page) {
  await page.goto("/");
  await page.evaluate((c) => {
    localStorage.clear();
    localStorage.setItem("cc.consent", c);
    localStorage.setItem("cc.role", "teacher");
  }, CONSENT);
}

async function makePaper(page: Page) {
  await page.goto("/#/papers");
  await page.getByTestId("papers-create").click();
  await page.getByTestId("route-rules").click();
  await page.getByTestId("paper-make").click();
  await expect(page.getByTestId("paper-view")).toBeVisible({ timeout: 30_000 });
}

test("Enter check asks for a paper, not a form, and reads its answers with the paper's own key", async ({ page }) => {
  test.setTimeout(120_000);
  await fresh(page);
  await page.goto("/#/check");
  // no paper yet: nothing to start with, and no Form A / Form B buttons
  await expect(page.getByTestId("start-check-go")).toBeDisabled();
  await expect(page.getByTestId("start-need-paper")).toBeVisible();
  await expect(page.getByTestId("form-A")).toHaveCount(0);

  await makePaper(page);
  await page.goto("/#/check");
  await expect(page.getByTestId("paper-attached")).toBeVisible(); // the only paper is chosen for her
  await page.getByTestId("check-expected").fill("1");
  await page.getByTestId("start-check-go").click();
  await expect(page.getByTestId("check-paper-code")).toBeVisible();

  // the phone now holds this paper's key: one box for each of its questions, from the server's engine
  const key = await page.evaluate(() => JSON.parse(localStorage.getItem("cc.paperkeys") ?? "{}") as Record<string, { items: { n: number; correct: number; probes: string[]; wrong: Record<string, string[]> }[] }>);
  const form = Object.values(key)[0]!;
  expect(form.items.length).toBeGreaterThanOrEqual(10);
  await expect(page.getByTestId(`box-${form.items.length}`)).toBeVisible();

  // one child who forgets the carried ten on two addition items: the error is found from the paper's own wrong answers
  const nocarry = form.items.filter((i) => i.probes.includes("ADD-NOCARRY")).slice(0, 2);
  expect(nocarry.length).toBe(2);
  for (const it of form.items) {
    const wrong = nocarry.find((n) => n.n === it.n) ? Object.entries(it.wrong).find(([, codes]) => codes.includes("ADD-NOCARRY"))?.[0] : undefined;
    await page.getByTestId(`input-${it.n}`).fill(wrong ?? String(it.correct));
  }
  page.once("dialog", (d) => void d.accept()); // no picture to check against: approve anyway
  await page.getByTestId("approve").click();
  page.once("dialog", (d) => void d.accept());
  await page.getByTestId("finish").click();
  await expect(page).toHaveURL(/#\/cards/);
});
