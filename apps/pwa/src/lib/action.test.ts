import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { actionHeaders, footerOn, getAction, measure, money, resetAction, runAction, seconds, setFooterOn, totalText, type UsageReply } from "./action";

function reply(over: Partial<UsageReply> = {}): UsageReply {
  const kind = { calls: 0, failed: 0, retried: 0, cost_usd: 0, priced: true };
  return {
    action_id: "x",
    name: "download_audio",
    complete: true,
    totals: { cost_usd: 0.0123, priced: true, entries: 3 },
    by_kind: { llm: { ...kind }, tts: { ...kind, calls: 2, characters: 300, cost_usd: 0.0123 }, stt: { ...kind }, cloud_run: { ...kind, calls: 1, request_ms: 2100, estimated: true } },
    time: { calls_sum_ms: 1800, calls_wall_ms: 900, request_ms: 2100 },
    display: { currency: "USD", inr_per_usd: null },
    ...over,
  };
}
const json = (body: unknown): Response => new Response(JSON.stringify(body), { status: 200 });

beforeEach(() => {
  vi.useFakeTimers();
  resetAction();
});
afterEach(() => {
  resetAction();
  vi.useRealTimers();
});

describe("an action", () => {
  it("sends its id on requests while it runs, and not after", async () => {
    const seen: Record<string, string>[] = [];
    await runAction(
      "download_audio",
      async () => {
        seen.push(actionHeaders());
      },
      (async () => json(reply())) as typeof fetch,
    );
    expect(seen[0]?.["X-Action-Name"]).toBe("download_audio");
    expect(seen[0]?.["X-Action-Id"]).toMatch(/[0-9a-f-]{8,}/);
    expect(actionHeaders()).toEqual({}); // the click's work is over: later requests are not its own
  });

  it("starts from nothing when the next action begins", async () => {
    await runAction("download_audio", async () => undefined, (async () => json(reply())) as typeof fetch);
    await vi.advanceTimersByTimeAsync(2000);
    const first = getAction();
    expect(first?.usage?.by_kind.tts.calls).toBe(2);
    let during: ReturnType<typeof getAction> = null;
    await runAction("print_pack", async () => {
      during = getAction();
    }, (async () => json(reply({ name: "print_pack" }))) as typeof fetch);
    expect(during).not.toBeNull();
    expect((during as unknown as { usage: unknown }).usage).toBeNull(); // no number of the first action
    expect((during as unknown as { id: string }).id).not.toBe(first?.id);
  });

  it("times the action from the click to its end", async () => {
    await runAction("print_pack", async () => {
      await vi.advanceTimersByTimeAsync(1500);
    }, (async () => json(reply())) as typeof fetch);
    expect(getAction()?.wallMs).toBeGreaterThanOrEqual(1500);
  });
});

describe("asking the server", () => {
  it("asks again until the server says complete, then once more, then stops", async () => {
    const answers = [reply({ complete: false }), reply({ complete: false }), reply({ complete: true }), reply({ complete: true })];
    let n = 0;
    const fetchFn = (async () => json(answers[Math.min(n++, answers.length - 1)])) as typeof fetch;
    await runAction("download_audio", async () => undefined, fetchFn);
    await vi.advanceTimersByTimeAsync(10_000);
    expect(n).toBe(4); // three until complete, one more for a late entry
    expect(getAction()?.phase).toBe("done");
    await vi.advanceTimersByTimeAsync(10_000);
    expect(n).toBe(4); // it does not keep asking
  });

  it("gives up after its time limit when the server never says complete", async () => {
    let n = 0;
    const now = vi.spyOn(Date, "now");
    let t = 0;
    now.mockImplementation(() => (t += 6000));
    const fetchFn = (async () => (n++, json(reply({ complete: false })))) as typeof fetch;
    await runAction("download_audio", async () => undefined, fetchFn);
    await vi.advanceTimersByTimeAsync(60_000);
    expect(n).toBeGreaterThan(1);
    expect(n).toBeLessThan(10);
    expect(getAction()?.phase).toBe("done");
    now.mockRestore();
  });

  it("a newer action stops the older one from asking", async () => {
    let asked = 0;
    const slow = (async () => (asked++, json(reply({ complete: false })))) as typeof fetch;
    await runAction("download_audio", async () => undefined, slow);
    await vi.advanceTimersByTimeAsync(1300);
    const before = asked;
    await runAction("print_pack", async () => undefined, (async () => json(reply({ name: "print_pack" }))) as typeof fetch);
    await vi.advanceTimersByTimeAsync(10_000);
    expect(asked).toBe(before); // the first action's loop ended when the second began
  });

  it("measure returns at once when its action is no longer the current one", async () => {
    const f = vi.fn(async () => json(reply()));
    await measure("old", -1, f as unknown as typeof fetch, async () => undefined);
    expect(f).not.toHaveBeenCalled();
  });
});

describe("what the footer says", () => {
  it("shows an unpriced line as n/a and never as zero", () => {
    expect(totalText(reply({ totals: { cost_usd: 0, priced: false, entries: 2 } }), "n/a")).toBe("n/a");
    expect(totalText(reply({ totals: { cost_usd: 0.02, priced: false, entries: 2 } }), "n/a")).toBe("$0.0200 + n/a");
    expect(totalText(reply(), "n/a")).toBe("$0.0123");
  });

  it("converts to rupees only when a rate is set", () => {
    expect(money(0.5, { currency: "INR", inr_per_usd: 80 })).toBe("₹40.00");
    expect(money(0.5, { currency: "INR", inr_per_usd: null })).toBe("$0.5000");
  });

  it("writes times in plain units", () => {
    expect(seconds(420)).toBe("420 ms");
    expect(seconds(2100)).toBe("2.1 s");
  });

  it("the bar can be hidden and shown again", () => {
    setFooterOn(false);
    expect(footerOn()).toBe(false);
    setFooterOn(true);
    expect(footerOn()).toBe(true);
  });
});
