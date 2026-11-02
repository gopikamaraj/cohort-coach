import { describe, expect, it } from "vitest";
import { BLANK, hasAnswers } from "./check";
import { applyReads, readSheet, SheetError, type SheetCell } from "./sheets";

const ok = (text: string): SheetCell => ({ text, status: "ok" });

describe("applyReads with number words", () => {
  it("types the number a box of words came to and keeps the words to show under the box", () => {
    const cells: SheetCell[] = [
      { text: "305", status: "check", words: "three hundred five" },
      { text: "496", status: "check", words: "four hundred ninety six" },
      { text: "43", status: "ok" },
    ];
    const { row, flagged, words } = applyReads(cells, 3);
    expect(row).toEqual(["305", "496", "43"]);
    expect(flagged).toEqual([0, 1]); // the teacher looks at both
    expect(words).toEqual({ 0: "three hundred five", 1: "four hundred ninety six" }); // a box of digits has none
  });
});

describe("applyReads", () => {
  it("fills confident reads, marks blanks, and flags the boxes to look at first", () => {
    const cells: SheetCell[] = [ok("346"), { text: "999", status: "check" }, { text: "", status: "blank" }, { text: "", status: "check" }];
    const { row, flagged } = applyReads(cells, 4);
    expect(row).toEqual(["346", "999", BLANK, ""]);
    expect(flagged).toEqual([1, 3]);
  });
  it("pads a short answer to the item count and flags the missing boxes", () => {
    const { row, flagged } = applyReads([ok("1")], 3);
    expect(row).toEqual(["1", "", ""]);
    expect(flagged).toEqual([1, 2]);
  });
});

describe("readSheet", () => {
  const photo = new Blob(["x"], { type: "image/jpeg" });
  const reply = (status: number, body: unknown = {}) => (async () => new Response(JSON.stringify(body), { status })) as unknown as typeof fetch;

  it("returns the cells and sends only the image and the form id", async () => {
    let sent: FormData | undefined;
    const fetchFn = (async (_url: string, init: RequestInit) => {
      sent = init.body as FormData;
      return new Response(JSON.stringify({ cells: [ok("85")] }), { status: 200 });
    }) as unknown as typeof fetch;
    expect(await readSheet(photo, "A", fetchFn)).toEqual([ok("85")]);
    expect([...sent!.keys()].sort()).toEqual(["form", "image"]);
  });
  it("maps failures to what she should do next", async () => {
    await expect(readSheet(photo, "A", reply(503))).rejects.toMatchObject({ kind: "typing" });
    await expect(readSheet(photo, "A", reply(422))).rejects.toMatchObject({ kind: "bad_photo" });
    await expect(readSheet(photo, "A", reply(500))).rejects.toMatchObject({ kind: "other" });
    const offline = (async () => {
      throw new TypeError("network");
    }) as unknown as typeof fetch;
    await expect(readSheet(photo, "A", offline)).rejects.toBeInstanceOf(SheetError);
    await expect(readSheet(photo, "A", offline)).rejects.toMatchObject({ kind: "offline" });
  });
});

describe("hasAnswers (when the photo asks before replacing)", () => {
  it("is false for an empty row, a row of blank marks, and unreadable marks", () => {
    expect(hasAnswers(["", "", ""])).toBe(false);
    expect(hasAnswers([BLANK, BLANK, ""])).toBe(false);
    expect(hasAnswers(["?", "", BLANK])).toBe(false);
    expect(hasAnswers([])).toBe(false);
  });
  it("is true as soon as one box has a digit", () => {
    expect(hasAnswers(["", "7", ""])).toBe(true);
    expect(hasAnswers([BLANK, "346"])).toBe(true);
  });
});
