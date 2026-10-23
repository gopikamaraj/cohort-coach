import { expect, test } from "@playwright/test";

const CONSENT = '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}';
const RIGHT = ["346", "728", "85", "74", "82", "35", "38", "26", "43", "54"];

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate((c) => {
    localStorage.clear();
    localStorage.setItem("cc.consent", c);
  }, CONSENT);
  await page.goto("/#/check");
  await page.getByTestId("form-A").click();
});

async function fillChild(page: import("@playwright/test").Page, values: string[]) {
  for (let q = 0; q < values.length; q++) await page.getByTestId(`input-${q + 1}`).fill(values[q]!);
}

test("each box uses the phone's number keyboard, takes digits in any script, and Enter moves on", async ({ page }) => {
  const box = page.getByTestId("input-1");
  await expect(box).toHaveAttribute("inputmode", "numeric");
  await box.fill("३४६"); // Devanagari digits from a Hindi keyboard
  await expect(box).toHaveValue("346");
  await box.fill("3a4-6");
  await expect(box).toHaveValue("346"); // nothing but digits is kept
  await box.press("Enter");
  await expect(page.getByTestId("input-2")).toBeFocused();
  await expect(page.locator(".keypad")).toHaveCount(0); // no keypad of our own
});

test("blank and can't read are marks on a box, and typing replaces them", async ({ page }) => {
  await page.getByTestId("blank-3").click();
  await expect(page.getByTestId("input-3")).toHaveAttribute("data-state", "blank");
  await page.getByTestId("unreadable-3").click();
  await expect(page.getByTestId("input-3")).toHaveAttribute("data-state", "unreadable");
  await page.getByTestId("input-3").fill("85");
  await expect(page.getByTestId("input-3")).not.toHaveAttribute("data-state", /.+/);
});

test("a list of sheets lets her jump to any child and see what was entered", async ({ page }) => {
  await fillChild(page, RIGHT);
  await page.getByTestId("next-child").click();
  await fillChild(page, ["347", "728", "85", "74", "82", "35", "38", "26", "43", "54"]);
  await page.getByTestId("next-child").click();
  const pick = page.getByTestId("child-select");
  await expect(pick.locator("option")).toHaveCount(3);
  await expect(pick.locator("option").nth(0)).toContainText("entered");
  await expect(pick.locator("option").nth(2)).toContainText("not entered");
  await pick.selectOption("1");
  await expect(page.getByTestId("child-title")).toHaveText("Child 2");
  await expect(page.getByTestId("input-1")).toHaveValue("347");
  await pick.selectOption("0");
  await expect(page.getByTestId("input-1")).toHaveValue("346");
});

test("an absent child's roll number is skipped, kept in order and not counted", async ({ page }) => {
  await fillChild(page, RIGHT);
  await page.getByTestId("next-child").click();
  await page.getByTestId("absent").check();
  await expect(page.getByTestId("absent-note")).toBeVisible();
  await expect(page.getByTestId("input-1")).toHaveCount(0);
  await page.getByTestId("next-child").click();
  await expect(page.getByTestId("child-title")).toHaveText("Child 3");
  await fillChild(page, RIGHT);
  await expect(page.getByTestId("check-count")).toContainText("2 children entered");
  await expect(page.getByTestId("check-count")).toContainText("1 absent");
  await expect(page.getByTestId("child-select").locator("option").nth(1)).toContainText("absent");
  await page.reload();
  await page.goto("/#/check");
  await page.getByTestId("child-select").selectOption("1");
  await expect(page.getByTestId("absent")).toBeChecked(); // remembered on this phone
});

test("marking a child absent asks before clearing answers already entered", async ({ page }) => {
  await fillChild(page, RIGHT);
  let asked = 0;
  page.on("dialog", async (d) => {
    asked += 1;
    await d.dismiss();
  });
  await page.getByTestId("absent").check({ force: true }).catch(() => undefined);
  await expect.poll(() => asked).toBe(1);
  await expect(page.getByTestId("input-1")).toHaveValue("346"); // she said no: nothing cleared
});

test("missed the teaching is tagged per concept, with the questions each covers", async ({ page }) => {
  const group = page.getByTestId("missed-group");
  await expect(group.locator("label")).toHaveCount(3);
  await expect(group).toContainText("place value (questions 1–2)");
  await expect(group).toContainText("addition with carrying (questions 3–5)");
  await expect(group).toContainText("subtraction with borrowing (questions 7–10)");
  await page.getByTestId("missed-addition").check();
  await page.getByTestId("next-child").click();
  await expect(page.getByTestId("missed-addition")).not.toBeChecked(); // the tag belongs to the child
  await page.getByTestId("child-select").selectOption("0");
  await expect(page.getByTestId("missed-addition")).toBeChecked();
});
