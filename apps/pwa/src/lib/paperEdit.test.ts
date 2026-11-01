import { describe, expect, it } from "vitest";
import { parseQuestion } from "./paperEdit";

describe("parseQuestion", () => {
  it("reads two numbers and the sign of the item", () => {
    expect(parseQuestion("add", "38 + 47")).toEqual({ ok: true, a: 38, b: 47 });
    expect(parseQuestion("subtract", "52−29")).toEqual({ ok: true, a: 52, b: 29 });
    expect(parseQuestion("dictate", " 346 ")).toEqual({ ok: true, a: 346, b: 0 });
  });
  it("says what is wrong, not whether the maths fits", () => {
    expect(parseQuestion("add", "38 - 47")).toEqual({ ok: false, why: "sign" });
    expect(parseQuestion("add", "38")).toEqual({ ok: false, why: "shape" });
    expect(parseQuestion("dictate", "3.5")).toEqual({ ok: false, why: "shape" });
  });
});
