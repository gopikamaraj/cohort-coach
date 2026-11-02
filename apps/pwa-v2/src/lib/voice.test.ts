import { describe, expect, it } from "vitest";
import { MAX_VOICE_FAILURES, slowLink, voiceDefault } from "./voice";

describe("when voice is the default", () => {
  it("needs the server, a recorder, a fast enough link, and no earlier choice of typing", () => {
    expect(voiceDefault(true, true, false, null)).toBe(true);
    expect(voiceDefault(false, true, false, null)).toBe(false);
    expect(voiceDefault(true, false, false, null)).toBe(false);
    expect(voiceDefault(true, true, true, null)).toBe(false);
    expect(voiceDefault(true, true, false, "0")).toBe(false);
    expect(voiceDefault(true, true, false, "1")).toBe(true);
  });
  it("treats 2g and slow-2g as slow, and 3g and 4g as fine", () => {
    expect(slowLink({ effectiveType: "2g" })).toBe(true);
    expect(slowLink({ effectiveType: "slow-2g" })).toBe(true);
    expect(slowLink({ effectiveType: "3g" })).toBe(false);
    expect(slowLink({ effectiveType: "4g" })).toBe(false);
    expect(slowLink(undefined)).toBe(false);
  });
  it("gives up on voice after two failures", () => {
    expect(MAX_VOICE_FAILURES).toBe(2);
  });
});
