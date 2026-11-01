// The results page for a class of 16 whose papers were entered and approved: the findings, the answer
// map (roll by question), "Why an error is flagged" (which items check each error) and "What each error
// means". Everything is compared with e2e/fixtures/results16.json, which scripts/make_results16.py wrote
// from the Python engine, so the page is checked against the engine and not against itself.
import { readFileSync, mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { chooseLanguage } from "./switch";
import { enterRolls, finishEntering, startSample } from "./sample";

interface Fixture {
  form: string;
  children: { roll: number; answers: string[]; cells: { kind: string; codes: string[] }[]; shows: string[] }[];
  class: { checked: number; counts: Record<string, number>; track: string | null; untracked: Record<string, number> };
}
const here = path.dirname(fileURLToPath(import.meta.url));
const fx = JSON.parse(readFileSync(path.join(here, "fixtures", "results16.json"), "utf-8")) as Fixture;
const SHOTS = path.resolve(here, "../../../data/autopilot-screens");
const CODES = ["PV-HEARD", "PV-REVERSE", "ADD-NOCARRY", "SUB-SFL", "SUB-NODEC"];
const SHORT: Record<string, string> = { "PV-HEARD": "PH", "PV-REVERSE": "PR", "ADD-NOCARRY": "AC", "SUB-SFL": "SF", "SUB-NODEC": "SN" };

async function enter16(page: Page): Promise<void> {
  await startSample(page, { size: fx.children.length });
  await enterRolls(page, fx.children.map((c) => c.answers));
  await finishEntering(page);
  await page.goto("/#/cards");
  await expect(page.getByTestId("answer-map")).toBeVisible();
}
const primary = (codes: string[], shows: string[]): string | null => {
  const order = CODES;
  return [...codes.filter((c) => shows.includes(c)), ...codes].sort((a, b) => order.indexOf(a) - order.indexOf(b))[0] ?? null;
};

test.describe("phone", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("the findings and the class counts equal the engine", async ({ page }) => {
    await enter16(page);
    await expect(page.getByText("16 children checked.")).toBeVisible();
    for (const code of CODES) {
      const n = fx.class.counts[code] as number;
      const card = page.getByTestId(`card-${code}`);
      if (n === 0) {
        await expect(card).toHaveCount(0);
        continue;
      }
      await expect(card.locator(".numeral")).toHaveText(String(n));
      await expect(card).toContainText("/ 16");
    }
    const text = await page.locator("main").innerText();
    for (const bad of ["%", "undefined", "NaN", "[object"]) expect(text, bad).not.toContain(bad);
    await page.screenshot({ path: path.join(SHOTS, "results-top-phone.png"), fullPage: false });
  });

  test("every cell of the answer map is the engine's reading of that answer", async ({ page }) => {
    await enter16(page);
    const cells = await page.$$eval("[data-testid^=cell-]", (els) =>
      els.map((e) => ({ id: e.getAttribute("data-testid"), kind: e.getAttribute("data-kind"), code: e.getAttribute("data-code"), confirmed: e.getAttribute("data-confirmed"), text: (e.textContent ?? "").trim(), label: e.getAttribute("aria-label") })),
    );
    expect(cells).toHaveLength(fx.children.length * 10);
    for (const child of fx.children) {
      child.cells.forEach((c, q) => {
        const got = cells.find((x) => x.id === `cell-${child.roll}-${q + 1}`);
        expect(got, `roll ${child.roll} q${q + 1}`).toBeTruthy();
        expect(got?.kind, `roll ${child.roll} q${q + 1}`).toBe(c.kind);
        const want = primary(c.codes, child.shows);
        expect(got?.code, `roll ${child.roll} q${q + 1}`).toBe(want ?? "");
        if (want) {
          expect(got?.text).toBe(SHORT[want]);
          expect(got?.confirmed).toBe(c.codes.some((x) => child.shows.includes(x)) ? "1" : "0");
        }
        expect(got?.label).toContain(`Roll ${child.roll}, question ${q + 1}:`);
      });
    }
    // five chosen cells, read as a person would
    await expect(page.getByTestId("cell-4-7")).toHaveText("SF");
    await expect(page.getByTestId("cell-1-1")).toHaveText("✓");
    await expect(page.getByTestId("cell-13-6")).toHaveText("–");
    await expect(page.getByTestId("cell-3-10")).toHaveText("×");
    await expect(page.getByTestId("cell-11-1")).toHaveText("PR");
  });

  test("column totals are the children who got each question wrong, and the legend counts the class card", async ({ page }) => {
    await enter16(page);
    for (let q = 0; q < 10; q++) {
      const wrong = fx.children.filter((c) => ["error", "other"].includes(c.cells[q]?.kind ?? "")).length;
      await expect(page.getByTestId(`amap-total-${q + 1}`)).toHaveText(String(wrong));
    }
    for (const code of CODES) {
      const n = fx.class.counts[code] as number;
      const chip = page.getByTestId(`legend-${code}`);
      if (n === 0 && !fx.children.some((c) => c.cells.some((x) => x.codes.includes(code)))) continue;
      await expect(chip).toContainText(`${n} children`);
    }
    // children who made a mistake on one question only (rolls 6 and 13 for SUB-SFL) are "possible", not counted
    const possible = fx.children.filter((c) => c.cells.some((x) => x.codes.includes("SUB-SFL")) && !c.shows.includes("SUB-SFL")).length;
    expect(possible).toBe(2);
    await expect(page.getByTestId("legend-SUB-SFL")).toContainText(`${possible} possible`);
    await expect(page.getByTestId("amap-local")).toHaveText("This table stays on this phone.");
  });

  test("sorting, highlighting, the popover and the keyboard", async ({ page }) => {
    await enter16(page);
    // sort by wrong answers: the roll with the most wrong answers first (ties by roll)
    const wrongOf = (c: Fixture["children"][number]) => c.cells.filter((x) => ["error", "other"].includes(x.kind)).length;
    const expected = [...fx.children].sort((a, b) => wrongOf(b) - wrongOf(a) || a.roll - b.roll).map((c) => c.roll);
    await page.getByTestId("amap-sort-errors").click();
    const order = await page.$$eval("[data-testid^=amap-row-]", (els) => els.map((e) => Number((e.getAttribute("data-testid") ?? "").replace("amap-row-", ""))));
    expect(order).toEqual(expected);
    await page.getByTestId("amap-sort-roll").click();
    // highlight one mistake: every other cell is dimmed, and the matrix row and questions are marked
    await page.getByTestId("legend-SUB-SFL").click();
    expect(await page.locator(".amap-cell.amap-dim").count()).toBe(160 - fx.children.reduce((s, c) => s + c.cells.filter((x) => x.codes.includes("SUB-SFL")).length, 0));
    await expect(page.getByTestId("legend-SUB-SFL")).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByTestId("results-coverage-SUB-SFL")).toHaveClass(/cov-row-on/);
    await page.getByTestId("legend-SUB-SFL").click();
    expect(await page.locator(".amap-cell.amap-dim").count()).toBe(0);
    // choosing a question in the answer map marks the errors it checks in the matrix
    await page.getByTestId("amap-col-1").getByRole("button").click();
    await expect(page.getByTestId("results-coverage-PV-HEARD")).toHaveClass(/cov-row-on/);
    await expect(page.getByTestId("results-coverage-SUB-SFL")).not.toHaveClass(/cov-row-on/);
    await page.getByTestId("amap-col-1").getByRole("button").click();
    // the popover
    await page.getByTestId("cell-4-7").click();
    const pop = page.getByTestId("amap-pop");
    await expect(pop).toContainText("Roll 4 · question 7");
    await expect(pop).toContainText("74 − 36");
    await expect(pop).toContainText("Answer given: 42");
    await expect(pop).toContainText("Correct answer: 38");
    await expect(pop).toContainText("Takes the smaller digit from the larger");
    await expect(pop).toContainText("Confirmed");
    await page.getByTestId("amap-pop-close").click();
    await page.getByTestId("cell-6-8").click(); // roll 6 made the mistake once
    await expect(page.getByTestId("amap-pop")).toContainText("Possible");
    await page.getByTestId("amap-pop-more").click();
    await expect(page.getByTestId("explain-SUB-SFL")).toHaveAttribute("open", "");
    // arrow keys move between cells
    await page.getByTestId("cell-1-1").focus();
    await page.keyboard.press("ArrowRight");
    await expect(page.getByTestId("cell-1-2")).toBeFocused();
    await page.keyboard.press("ArrowDown");
    await expect(page.getByTestId("cell-2-2")).toBeFocused();
    await page.keyboard.press("ArrowLeft");
    await expect(page.getByTestId("cell-2-1")).toBeFocused();
    await page.keyboard.press("ArrowUp");
    await page.keyboard.press("ArrowUp");
    await expect(page.getByTestId("cell-1-1")).toBeFocused();
  });

  test("Why an error is flagged: the paper's own matrix with this class's counts", async ({ page }) => {
    await enter16(page);
    const grid = page.getByTestId("results-coverage");
    await page.getByTestId("results-why").evaluate((el) => ((el as HTMLDetailsElement).open = true));
    await expect(grid).toBeVisible();
    const probes: Record<string, number[]> = { "PV-HEARD": [1, 2], "PV-REVERSE": [1, 2], "ADD-NOCARRY": [3, 4, 5], "SUB-SFL": [7, 8, 9, 10], "SUB-NODEC": [7, 8, 9, 10] };
    for (const code of CODES) {
      const row = page.getByTestId(`results-coverage-${code}`);
      await expect(row).toBeVisible();
      const dots = await row.locator("td").evaluateAll((tds) => tds.slice(0, 10).map((td) => (td.textContent ?? "").includes("●")));
      expect(dots.map((d, i) => (d ? i + 1 : 0)).filter(Boolean), code).toEqual(probes[code]);
      await expect(row.locator("td").nth(10)).toHaveText(String((probes[code] as number[]).length)); // items checking it
      const confirmed = fx.class.counts[code] as number;
      await expect(page.getByTestId(`results-coverage-${code}-class`)).toContainText(confirmed > 0 ? `${confirmed} confirmed` : "none found");
    }
    await expect(page.getByTestId("results-rule")).toHaveText("An error is confirmed when a child makes it on at least 2 of its questions. On one question it is shown as possible.");
    await expect(page.getByTestId("results-shared")).toContainText("the child's actual answer decides");
    // header cells do not wrap: every question number and every error code is on one line
    const wrapped = await grid.evaluate((table) => {
      const bad: string[] = [];
      table.querySelectorAll("thead th .nowrap, tbody .cov-code-text").forEach((el) => {
        if (el.getClientRects().length > 1) bad.push(el.textContent ?? "");
        const style = getComputedStyle(el);
        if (style.whiteSpace !== "nowrap") bad.push(`white-space:${style.whiteSpace} ${el.textContent}`);
      });
      return bad;
    });
    expect(wrapped).toEqual([]);
    await page.getByTestId("results-detail").screenshot({ path: path.join(SHOTS, "results-why-phone.png") });
  });

  test("What each error means: every error found has an explanation with the class's own example", async ({ page }) => {
    await enter16(page);
    for (const code of CODES) {
      const here = fx.children.some((c) => c.cells.some((x) => x.codes.includes(code)));
      if (!here) continue;
      const panel = page.getByTestId(`explain-${code}`);
      await expect(panel).toHaveCount(1);
      await panel.locator("summary").click();
      for (const f of ["what", "why", "spot", "first"]) await expect(page.getByTestId(`explain-${code}-${f}`)).not.toBeEmpty();
      await expect(page.getByTestId(`explain-${code}-class`)).toContainText("of 16 children show it");
    }
    // the worked example comes from the class's own question: most children made SUB-SFL on question 7 (74 - 36 = 38; 42)
    await expect(page.getByTestId("explain-SUB-SFL-example")).toContainText("74 − 36");
    await expect(page.getByTestId("explain-SUB-SFL-example")).toContainText("writes 42");
    await expect(page.getByTestId("explain-SUB-SFL-example")).toContainText("correct answer is 38");
    await expect(page.getByTestId("explain-PV-HEARD-example")).toContainText("when you say 346");
    await expect(page.getByTestId("explain-SUB-SFL").locator(".chip-draft")).toBeVisible();
    await page.getByTestId("results-detail").screenshot({ path: path.join(SHOTS, "results-explain-phone.png") });
  });

  test("the results page passes axe and stays inside the screen", async ({ page }) => {
    await enter16(page);
    await page.getByTestId("results-why").evaluate((el) => ((el as HTMLDetailsElement).open = true));
    const found = (await new AxeBuilder({ page }).include("[data-testid=results-detail]").withTags(["wcag2a", "wcag2aa"]).analyze()).violations;
    expect(found.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`)).toEqual([]);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow).toBeLessThanOrEqual(0);
    // nothing is cut off at the right edge: every block of the detail fits inside the screen, tables scroll in their own box
    const wide = await page.getByTestId("results-detail").evaluate((root) => {
      const limit = window.innerWidth;
      return [...root.querySelectorAll("p, summary, h2, h3, .amap-chip, .table-scroll")]
        .filter((el) => el.getBoundingClientRect().right > limit + 1)
        .map((el) => `${el.tagName}.${el.className} ${(el.textContent ?? "").slice(0, 30)}`);
    });
    expect(wide).toEqual([]);
    for (const [id, name] of [["amap-legend", "map"], ["results-why", "why"], ["explanations", "explain"]] as const) {
      await page.getByTestId(id).scrollIntoViewIfNeeded();
      await page.getByTestId(id).evaluate((el) => el.scrollIntoView({ block: "start" }));
      await page.screenshot({ path: path.join(SHOTS, `results-${name}-view-phone.png`) });
    }
  });

  test("it fits in Hindi and Tamil at 360 px", async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 780 });
    await enter16(page);
    for (const lang of ["hi", "ta"]) {
      await chooseLanguage(page, lang);
      await expect(page.getByTestId("answer-map")).toBeVisible();
      await page.getByTestId("results-why").evaluate((el) => ((el as HTMLDetailsElement).open = true));
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(overflow, lang).toBeLessThanOrEqual(0);
      const text = await page.locator("main").innerText();
      expect(text).not.toContain("results.");
      expect(text).not.toContain("undefined");
      await page.getByTestId("results-detail").screenshot({ path: path.join(SHOTS, `results-${lang}-360.png`) });
    }
  });
});

test.describe("laptop", () => {
  test.use({ viewport: { width: 1280, height: 800 } });

  test("the coverage matrix is open by default and nothing overflows", async ({ page }) => {
    mkdirSync(SHOTS, { recursive: true });
    await enter16(page);
    await expect(page.getByTestId("results-why")).toHaveAttribute("open", "");
    await expect(page.getByTestId("results-coverage")).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow).toBeLessThanOrEqual(0);
    await page.getByTestId("results-detail").screenshot({ path: path.join(SHOTS, "results-full-laptop.png") });
  });
});

test.describe("absent children, reload and offline", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("two absent rolls are left out of the map and the count, and the page is the same after a reload and offline", async ({ page, context }) => {
    await startSample(page, { size: fx.children.length + 2 });
    await enterRolls(page, fx.children.map((c) => c.answers));
    await page.getByTestId("absent").check(); // roll 17
    await page.getByTestId("child-select").selectOption({ index: fx.children.length + 1 });
    await page.getByTestId("absent").check(); // roll 18
    await finishEntering(page);
    await page.goto("/#/cards");
    await expect(page.getByText("16 children checked.")).toBeVisible();
    const check = async () => {
      await expect(page.getByTestId("answer-map")).toBeVisible();
      await expect(page.getByText("2 absent: not in this table.")).toBeVisible();
      await expect(page.locator("[data-testid^=amap-row-]")).toHaveCount(16);
      await expect(page.getByTestId("card-SUB-SFL").locator(".numeral")).toHaveText(String(fx.class.counts["SUB-SFL"]));
    };
    await check();
    await page.reload();
    await check();
    await page.evaluate(async () => {
      await navigator.serviceWorker.ready;
    });
    await page.waitForFunction(async () => (await caches.keys()).length > 0);
    await context.setOffline(true);
    await page.reload();
    await check();
    await context.setOffline(false);
  });

  test("with no check yet the results page says so and shows no table", async ({ page }) => {
    await page.goto("/#/cards");
    await expect(page.getByTestId("cards-none")).toBeVisible();
    await expect(page.getByTestId("answer-map")).toHaveCount(0);
  });
});
