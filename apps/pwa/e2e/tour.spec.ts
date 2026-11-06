import { expect, test } from "./test";

// The guided tour, rebuilt 6 Nov 2026: nine steps (papers, check, results, cohort, practice, profile, officer, mentor, coach),
// each naming the role, saying what to notice and opening the real screen. The old spec drove the embedded check and
// the "built in a later phase" notes; those are gone with the old tour.

const CONSENT = '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}';

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate((c) => {
    (((u: (string | null)[]) => (localStorage.clear(), u[0] && localStorage.setItem("cc.user", u[0]), u[1] && localStorage.setItem("cc.cacheOwner", u[1])))([localStorage.getItem("cc.user"), localStorage.getItem("cc.cacheOwner")]))
    localStorage.setItem("cc.consent", c);
  }, CONSENT);
});

test("the landing page's tour card starts the tour at step 1 as the teacher, and the page says how to use the nicknames", async ({ page }) => {
  await page.goto("/#/roles");
  await expect(page.getByTestId("how-to-use")).toContainText("3A Math");
  await expect(page.getByTestId("how-to-use")).toContainText("Block Officer");
  await page.getByTestId("card-tour").click();
  await expect(page).toHaveURL(/#\/tour\/1/);
  await expect(page.getByTestId("tour-step")).toContainText("Step 1 of 9");
  await expect(page.getByTestId("tour-banner")).toContainText("Now you're the Teacher");
  await expect(page.getByTestId("tour-notice")).toContainText("What to notice");
  await expect(page.getByTestId("tour-open")).toHaveAttribute("href", /#\/papers$/);
});

test("each step opens its own screen", async ({ page }) => {
  const routes = ["papers", "check", "cards", "cohort", "practice", "profile", "officer", "mentor", "coach"];
  for (const [i, route] of routes.entries()) {
    await page.goto(`/#/tour/${i + 1}`);
    await expect(page.getByTestId("tour-step")).toContainText(`Step ${i + 1} of 9`);
    await expect(page.getByTestId("tour-open")).toHaveAttribute("href", new RegExp(`#/${route}$`));
  }
});

test("every step shows which role you are (the chip is on all nine, not only where the role changes)", async ({ page }) => {
  const roles = ["Teacher", "Teacher", "Teacher", "Teacher", "Teacher", "Teacher", "Officer", "Mentor", "Coach"];
  for (const [i, role] of roles.entries()) {
    await page.goto(`/#/tour/${i + 1}`);
    await expect(page.getByTestId("tour-banner")).toContainText(`Now you're the ${role}`);
  }
});

test("skip and back move through the steps and switch the role banner", async ({ page }) => {
  await page.goto("/#/tour/6");
  await page.getByTestId("tour-next").click();
  await expect(page).toHaveURL(/#\/tour\/7/);
  await expect(page.getByTestId("tour-banner")).toContainText("Officer");
  await page.getByTestId("tour-next").click();
  await expect(page.getByTestId("tour-banner")).toContainText("Mentor");
  await page.getByTestId("tour-back").click();
  await expect(page).toHaveURL(/#\/tour\/7/);
  await page.goto("/#/tour/9");
  await expect(page.getByTestId("tour-next")).toContainText("Finish");
});

test("the officer step says its counts are real and the mentor and coach steps say their data is mocked", async ({ page }) => {
  await page.goto("/#/tour/7");
  await expect(page.getByTestId("tour-notice")).toContainText("pilot class data");
  await expect(page.getByTestId("tour-mocked")).toHaveCount(0);
  for (const n of [8, 9]) {
    await page.goto(`/#/tour/${n}`);
    await expect(page.getByTestId("tour-mocked")).toContainText("mocked data");
  }
});

test("leaving and coming back to the deep link resumes at that step", async ({ page }) => {
  await page.goto("/#/tour/4");
  await page.goto("/#/roles");
  await page.goto("/#/tour/4");
  await expect(page.getByTestId("tour-step")).toContainText("Step 4 of 9");
});

test("a role's walk-through opens the tour at that role's step", async ({ page }) => {
  await page.goto("/#/roles");
  await page.getByTestId("card-coach").click();
  await page.getByTestId("dlg-walk").click();
  await expect(page).toHaveURL(/#\/tour\/9/);
});
