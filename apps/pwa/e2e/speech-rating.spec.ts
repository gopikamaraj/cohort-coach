import path from "node:path";
import { readFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

// The offline rating page of the listening test (scripts/speech_eval_pack.py). The fixture was made
// by the same page() function with two generated tone clips. It works from a file, offline.

const here = path.dirname(fileURLToPath(import.meta.url));
const PAGE = pathToFileURL(path.join(here, "fixtures", "rate-sample.html")).href;

test("a rater scores each clip and saves a CSV, with no network; the page passes axe", async ({ page }) => {
  const requests: string[] = [];
  page.on("request", (r) => {
    if (!r.url().startsWith("file:") && !r.url().startsWith("data:") && !r.url().startsWith("blob:")) requests.push(r.url());
  });
  await page.goto(PAGE);
  await page.getByLabel("your name or initials").fill("SK");
  for (const clip of ["clip-11111", "clip-22222"]) {
    for (const [score, v] of [["naturalness", "4"], ["clarity", "5"], ["numbers", "2"], ["suitability", "3"]]) {
      await page.getByLabel(`${score} for ${clip}`).selectOption(v);
    }
  }
  await page.getByLabel("comment for clip-22222").fill('too fast, "23" unclear');
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Save my ratings (CSV)" }).click();
  const file = await (await download).path();
  const csv = readFileSync(file!, "utf-8").trim().split("\n");
  expect(csv[0]).toBe("rater,clip,naturalness,clarity,numbers,suitability,comment");
  expect(csv[1]).toBe('SK,clip-11111,4,5,2,3,""');
  expect(csv[2]).toBe(`SK,clip-22222,4,5,2,3,"too fast, '23' unclear"`);
  expect(requests).toEqual([]); // offline: nothing is fetched
  const axe = await new AxeBuilder({ page }).analyze();
  expect(axe.violations.map((v) => v.id)).toEqual([]);
});
