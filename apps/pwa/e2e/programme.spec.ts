import { expect, test, type Page } from "@playwright/test";

// My programme, What I entered (history), the classroom observation, and the layout at several
// screen sizes. The API runs in recorded mode; none of these screens makes a paid call.

const LINES = ["Priya, what is 52 minus 29?", "Tell me how you got that."];

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => {
    localStorage.clear();
    localStorage.setItem("cc.voice", "0");
  });
});

async function loadDemo(page: Page) {
  await page.goto("/#/judge");
  await page.getByTestId("load-demo").click();
  await expect(page.getByTestId("demo-loaded")).toBeVisible();
}

test("My programme shows where she stands, step by step, and says where lessons will appear", async ({ page }) => {
  await loadDemo(page);
  await page.goto("/#/programme");
  await expect(page.getByTestId("programme")).toBeVisible();
  await expect(page.getByRole("note")).toContainText("Simulated data");
  await expect(page.getByTestId("prog-check")).toHaveAttribute("data-done", "true");
  await expect(page.getByTestId("prog-track")).toHaveAttribute("data-done", "true");
  await expect(page.getByTestId("prog-cohort")).toContainText(/cohort of \d+ teachers|waiting list/);
  await expect(page.getByTestId("prog-mentor")).toContainText("Mentors are chosen after the next check");
  await expect(page.getByTestId("prog-lessons")).toHaveAttribute("data-done", "false");
  await expect(page.getByText("None published yet")).toBeVisible();
  await expect(page.getByText("Where you will hear")).toBeVisible();
  expect(await page.locator("body").innerText()).not.toMatch(/%/);
});

test("a class with no check yet is told to start with the check, and the screen works offline", async ({ page, context }) => {
  await page.goto("/#/programme");
  await expect(page.getByTestId("prog-check")).toHaveAttribute("data-done", "false");
  await expect(page.getByTestId("prog-cohort")).toContainText("Not placed yet");
  await context.setOffline(true);
  await page.evaluate(() => window.dispatchEvent(new Event("offline")));
  await expect(page.getByTestId("prog-offline")).toBeVisible();
  await expect(page.getByTestId("prog-check")).toBeVisible(); // the steps from this phone are still there
  await context.setOffline(false);
});

test("What I entered lists the check with its children and send state, and shows the answers on request", async ({ page }) => {
  await loadDemo(page);
  await page.goto("/#/history");
  await expect(page.getByTestId("history-check").first()).toBeVisible();
  await expect(page.getByTestId("history-check").first()).toContainText("children");
  await expect(page.getByTestId("history-state").first()).toContainText(/Class counts/);
  await expect(page.getByTestId("history-table")).toHaveCount(0);
  await page.getByTestId("history-toggle").first().click();
  await expect(page.getByTestId("history-table")).toBeVisible();
  await expect(page.getByText("never holds a child's answers")).toBeVisible();
});

test("a child filled from a photo is recorded as such in the history", async ({ page }) => {
  const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAFUlEQVR4nGP88OEDAzbAhFV00EoAADQGAuBmG04kAAAAAElFTkSuQmCC", "base64");
  const cells = Array.from({ length: 10 }, (_, i) => ({ text: String(30 + i), status: "ok" }));
  await page.route("**/api/sheets/read", (r) => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ form: "A", retried: false, cells }) }));
  await page.goto("/#/check");
  await page.getByTestId("form-A").click();
  await page.getByTestId("photo-input").setInputFiles({ name: "s.png", mimeType: "image/png", buffer: PNG });
  await expect(page.getByTestId("photo-note")).toContainText("Filled in from the photo");
  await page.goto("/#/history");
  await expect(page.getByTestId("history-check").first()).toContainText("1 filled in from a photo");
  await expect(page.getByTestId("history-state").first()).toContainText("Not finished yet");
});

test("after trying it in class she records what she saw: kept on the phone, sent as choices only", async ({ page }) => {
  const sent: string[] = [];
  page.on("request", (r) => {
    if (/\/api\/practice\/observations$/.test(r.url())) sent.push(r.postData() ?? "");
  });
  await page.goto("/#/practice?seed=5");
  await page.getByTestId("start-practice").click();
  await expect(page.getByTestId("kid-4")).toBeVisible();
  for (const [i, line] of LINES.entries()) {
    await page.getByTestId("say").fill(line);
    await page.getByTestId("send").click();
    await expect(page.getByTestId(`reply-${i + 1}`)).toBeVisible();
  }
  await page.getByTestId("tab-review").click();
  await page.getByTestId("review-item").click();
  await expect(page.getByTestId("obs-save")).toBeDisabled();
  await page.getByTestId("obs-some").click();
  await page.getByTestId("obs-diff-quieter").click();
  await page.getByTestId("obs-diff-too_easy").click();
  await page.getByTestId("obs-save").click();
  await expect(page.getByTestId("obs-state")).toContainText("sent");
  expect(sent).toHaveLength(1);
  expect(JSON.parse(sent[0]!)).toEqual({ scenario: "SUB-SFL", language: "en", likeness: "some", differences: ["quieter", "too_easy"] });
  expect(sent[0]).not.toContain("Priya");
  await page.goto("/#/history");
  await expect(page.getByTestId("history-observations")).toContainText("1 (0 waiting");
});

const SIZES = [
  { name: "320 narrow phone", width: 320, height: 640 },
  { name: "360 phone", width: 360, height: 740 },
  { name: "768 tablet", width: 768, height: 1024 },
  { name: "1280 laptop", width: 1280, height: 800 },
];
for (const size of SIZES) {
  test(`no sideways scrolling and a reachable menu at ${size.name}`, async ({ page }) => {
    test.setTimeout(90_000);
    await page.setViewportSize({ width: size.width, height: size.height });
    await loadDemo(page);
    for (const route of ["home", "check", "cards", "practice", "programme", "history", "judge"]) {
      await page.goto(`/#/${route}`);
      if (route === "check" && (await page.getByTestId("form-A").count()) > 0) await page.getByTestId("form-A").click();
      if (route === "practice") {
        await page.getByTestId("start-practice").click();
        await expect(page.getByTestId("goal")).toBeVisible();
      }
      if (route === "history") await page.getByTestId("history-toggle").first().click();
      const overflow = await page.evaluate(() => {
        const wide = [...document.querySelectorAll("body *")].filter((el) => {
          const r = el.getBoundingClientRect();
          return r.width > 0 && r.right > window.innerWidth + 1 && !el.closest(".table-scroll, .navbar");
        });
        return { page: document.documentElement.scrollWidth - window.innerWidth, wide: wide.slice(0, 3).map((e) => e.tagName + "." + e.className) };
      });
      expect(overflow, `${size.name} ${route}`).toEqual({ page: 0, wide: [] });
      await expect(page.locator("nav.navbar a").first()).toBeVisible();
    }
  });
}

test("on a wide screen the app is a centred column, not a phone frame", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/#/home");
  const box = (await page.locator(".frame").boundingBox())!;
  expect(box.width).toBeGreaterThan(700);
  expect(box.width).toBeLessThanOrEqual(1000);
  expect(Math.abs(box.x + box.width / 2 - 640)).toBeLessThan(2);
});
