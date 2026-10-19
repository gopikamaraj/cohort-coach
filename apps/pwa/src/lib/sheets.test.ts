import { describe, expect, it } from "vitest";
import { BLANK } from "./check";
import { applyReads, readSheet, SheetError, type SheetCell } from "./sheets";

const ok = (text: string): SheetCell => ({ text, status: "ok" });

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
