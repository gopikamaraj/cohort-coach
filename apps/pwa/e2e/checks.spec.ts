import { expect, test } from "./test";
import { begin, openWithPaper, startSample } from "./sample";

// Every check says what it is: Start a check, the header on every entry screen, a before-and-after view
// from a pre-test and a post-test. Everything is local to the phone; the demo class is made up.

const CONSENT = '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}';

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate((c) => {
    (((u: (string | null)[]) => (localStorage.clear(), u[0] && localStorage.setItem("cc.user", u[0]), u[1] && localStorage.setItem("cc.cacheOwner", u[1])))([localStorage.getItem("cc.user"), localStorage.getItem("cc.cacheOwner")]));
    localStorage.setItem("cc.consent", c);
  }, CONSENT);
});

test("a fresh phone is offered a pre-test, and the header names the check on every entry screen", async ({ page }) => {
  await openWithPaper(page);
  await expect(page.getByTestId("start-check")).toBeVisible();
  await expect(page.getByTestId("kind-pre")).toHaveAttribute("aria-checked", "true");
  await expect(page.getByTestId("kind-pre")).toContainText("suggested");
  await expect(page.getByTestId("exists-none")).toBeVisible();
  await begin(page, 18);
  await expect(page.getByTestId("check-label")).toContainText(/^Pre-test · PRE · /);
  await expect(page.getByTestId("check-label")).toContainText(String(new Date().getUTCFullYear()));
  await expect(page.getByTestId("check-progress")).toHaveText("0 of 18 papers entered");
  await page.getByTestId("input-1").fill("346");
  await page.getByTestId("input-2").fill("728");
  await page.getByTestId("next-child").click();
  await expect(page.getByTestId("check-label")).toBeVisible(); // still there on the next child
  await page.getByTestId("input-1").fill("346");
  await expect(page.getByTestId("check-progress")).toHaveText("2 of 18 papers entered");
});

test("a post-test with no pre-test says so plainly and can carry on as a termly check", async ({ page }) => {
  await page.goto("/#/check");
  await page.getByTestId("kind-post").click();
  await expect(page.getByTestId("no-pre-note")).toContainText("No pre-test is saved");
  await page.getByTestId("make-termly").click();
  await expect(page.getByTestId("kind-termly")).toHaveAttribute("aria-checked", "true");
  await expect(page.getByTestId("no-pre-note")).toHaveCount(0);
  // there is no termly paper for this class yet: the list says so and the way to make one is a link
  await expect(page.getByTestId("chooser-none")).toBeVisible();
  await expect(page.getByTestId("start-check-go")).toBeDisabled();
});

test("changing a check keeps its papers: the kind and date change, the paper does not once papers are entered", async ({ page }) => {
  await startSample(page, { size: 2 });
  await page.getByTestId("input-1").fill("346");
  page.once("dialog", (d) => void d.accept());
  await page.getByTestId("check-change").click();
  await expect(page.getByTestId("start-check")).toBeVisible();
  await expect(page.getByTestId("paper-chooser")).toBeVisible(); // the paper is fixed: only its own row can be chosen
  await page.getByTestId("kind-termly").click();
  await page.getByTestId("start-check-go").click();
  await expect(page.getByTestId("check-label")).toContainText(/^Termly check · PRE · /);
  await expect(page.getByTestId("input-1")).toHaveValue("346"); // nothing lost
  // and it is saved: wait for the write to land on the phone, then reload and the label is the same
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          new Promise<string>((resolve) => {
            const open = indexedDB.open("cohort-coach");
            open.onsuccess = () => {
              const all = open.result.transaction("checks").objectStore("checks").getAll();
              all.onsuccess = () => resolve((all.result as { kind?: string }[]).map((c) => c.kind ?? "").join(","));
              all.onerror = () => resolve("");
            };
            open.onerror = () => resolve("");
          }),
      ),
    )
    .toBe("termly");
  await page.reload();
  await expect(page.getByTestId("check-label")).toContainText(/^Termly check · PRE · /);
});

test("cancelling a change with papers entered leaves the check as it was", async ({ page }) => {
  await startSample(page, { size: 2 });
  await page.getByTestId("input-1").fill("346");
  page.once("dialog", (d) => void d.dismiss());
  await page.getByTestId("check-change").click();
  await expect(page.getByTestId("start-check")).toHaveCount(0);
  await expect(page.getByTestId("input-1")).toHaveValue("346");
});

test("the demo class has a pre-test and a post-test, and the class page shows counts before and after", async ({ page }) => {
  await page.goto("/#/judge");
  await page.getByTestId("load-demo").click();
  await expect(page.getByTestId("demo-loaded")).toBeVisible();
  await page.getByTestId("advance").click();
  await page.getByTestId("load-demo").click();
  await page.goto("/#/cards");
  await expect(page.getByTestId("cards-check-label")).toContainText(/^Post-test · POST · /);
  const ba = page.getByTestId("before-after");
  await expect(ba.getByTestId("ba-demo")).toHaveText("Demo data");
  await expect(ba.getByTestId("ba-label")).toContainText(/Pre-test PRE · .* \(/);
  await expect(ba.getByTestId("ba-label")).toContainText(/to Post-test POST · .* \(/);
  await expect(ba.getByTestId("ba-paired")).toContainText("28 children paired");
  await expect(ba.getByTestId("ba-small")).toHaveCount(0);
  // counts only: the subtraction row is 14 flagged before, 5 no longer flagged, 9 still, 0 new
  const c3 = ba.getByTestId("ba-row-C3").locator("td");
  await expect(c3).toHaveText(["14", "5", "9", "0"]);
  await expect(ba.getByTestId("ba-bar-C3")).toBeVisible();
  expect(await ba.innerText()).not.toContain("%");
});

test("the history lists each check with its kind and date", async ({ page }) => {
  await startSample(page, { size: 2 });
  await page.getByTestId("input-1").fill("346");
  await page.goto("/#/history");
  await expect(page.getByTestId("history-kind").first()).toContainText(/^Pre-test · /);
});

test("Start a check, the check header and the before-and-after view pass axe", async ({ page }) => {
  const { default: AxeBuilder } = await import("@axe-core/playwright");
  const scan = async (selector: string) => {
    const r = await new AxeBuilder({ page }).include(selector).withTags(["wcag2a", "wcag2aa"]).analyze();
    expect(r.violations.map((v) => `${v.id}: ${v.nodes.length}`), selector).toEqual([]);
  };
  await openWithPaper(page);
  await expect(page.getByTestId("start-check")).toBeVisible();
  await scan("[data-testid=start-check]");
  await begin(page, 2);
  await expect(page.getByTestId("check-header")).toBeVisible();
  await scan("[data-testid=check-header]");
  await page.goto("/#/judge");
  await page.getByTestId("load-demo").click();
  await page.getByTestId("advance").click();
  await page.getByTestId("load-demo").click();
  await page.goto("/#/cards");
  await expect(page.getByTestId("ba-table")).toBeVisible();
  await scan("[data-testid=before-after]");
});
