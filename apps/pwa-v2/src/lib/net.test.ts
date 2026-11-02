import { describe, expect, it } from "vitest";
import { describeLink } from "./net";

describe("describeLink", () => {
  it("names the signal from the effective type and rounds the download estimate", () => {
    expect(describeLink({ effectiveType: "4g", downlink: 5.025 })).toEqual({ signal: "good", mbps: "5" });
    expect(describeLink({ effectiveType: "3g", downlink: 1.65 })).toEqual({ signal: "slow", mbps: "1.7" });
    expect(describeLink({ effectiveType: "2g", downlink: 0.35 })).toEqual({ signal: "veryslow", mbps: "0.4" });
    expect(describeLink({ effectiveType: "slow-2g", downlink: 0.05 })).toEqual({ signal: "veryslow", mbps: "0.1" });
  });
  it("says 10+ because the browser stops counting at 10", () => {
    expect(describeLink({ effectiveType: "4g", downlink: 10 })?.mbps).toBe("10+");
  });
  it("shows nothing when the browser gives no estimate", () => {
    expect(describeLink(undefined)).toBeNull();
    expect(describeLink({})).toBeNull();
    expect(describeLink({ effectiveType: "4g" })).toBeNull();
    expect(describeLink({ effectiveType: "4g", downlink: 0 })).toBeNull();
    expect(describeLink({ effectiveType: "5g", downlink: 20 })).toBeNull();
  });
});
