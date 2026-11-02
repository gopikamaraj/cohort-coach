import { describe, expect, it } from "vitest";
import { t } from "./index";

describe("a missing string never blanks the screen", () => {
  it("shows the key instead of throwing", () => {
    expect(t("en", "no.such.string" as never)).toBe("no.such.string");
  });
});
