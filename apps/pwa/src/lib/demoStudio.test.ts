import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DemoError, LAST_STEP, STEPS, STEP_KEY, demoStep, detailText } from "./demoStudio";

describe("demo errors show the server's words (QA-DEMO W2)", () => {
  it("takes the message from a {message} body or a string body", () => {
    expect(new DemoError(503, { message: "Type the answers." }).message).toBe("Type the answers.");
    expect(new DemoError(409, "Make the paper first.").message).toBe("Make the paper first.");
  });
  it("is empty, never 'demo 503', when the server sent no words", () => {
    expect(new DemoError(503).message).toBe("");
    expect(new DemoError(0, { other: 1 }).message).toBe("");
    expect(detailText(null)).toBe("");
  });
});

describe("the demo bar counts 12 steps and keeps the optional 13th (QA-DEMO W1)", () => {
  const data = new Map<string, string>();
  beforeEach(() => {
    const localStorage = { getItem: (k: string) => data.get(k) ?? null, setItem: (k: string, v: string) => void data.set(k, v), removeItem: (k: string) => void data.delete(k) };
    vi.stubGlobal("window", { localStorage, dispatchEvent: () => true });
  });
  afterEach(() => {
    data.clear();
    vi.unstubAllGlobals();
  });
  it("has 12 counted steps and one optional step", () => {
    expect(LAST_STEP).toBe(12);
    expect(STEPS.length).toBe(13);
  });
  it("remembers step 13, so the bar stays on the two-classes screen", () => {
    data.set(STEP_KEY, "13");
    expect(demoStep()).toBe(13);
    data.set(STEP_KEY, "14");
    expect(demoStep()).toBeNull();
  });
});
