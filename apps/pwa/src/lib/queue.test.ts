import { describe, expect, it, vi } from "vitest";
import { ageParts, canActivate, canApprove, oldestFirst, qcall, QueueError, REASONS } from "./queue";

describe("the review queue helpers", () => {
  it("shows hours under two days and days after that", () => {
    expect(ageParts(5.4)).toEqual({ unit: "hours", n: 5 });
    expect(ageParts(47)).toEqual({ unit: "hours", n: 47 });
    expect(ageParts(48)).toEqual({ unit: "days", n: 2 });
    expect(ageParts(100)).toEqual({ unit: "days", n: 4 });
  });

  it("lists the oldest first so nothing waits unseen", () => {
    expect(oldestFirst([{ age_hours: 1 }, { age_hours: 90 }, { age_hours: 30 }]).map((r) => r.age_hours)).toEqual([90, 30, 1]);
  });

  it("only an in-review version can take the coach's key, and only an approved one the officer's", () => {
    expect(canApprove({ status: "in_review" })).toBe(true);
    for (const s of ["draft", "approved", "active", "retired"] as const) expect(canApprove({ status: s })).toBe(false);
    expect(canActivate({ status: "approved" })).toBe(true);
    for (const s of ["draft", "in_review", "active", "retired"] as const) expect(canActivate({ status: s })).toBe(false);
  });

  it("offers the five structured reasons the server accepts", () => {
    expect([...REASONS]).toEqual(["wrong_maths", "culturally_off", "too_complex_for_medium", "tone_issue", "factually_shaky"]);
  });
});

describe("qcall", () => {
  it("sends the acting role and a JSON body, and returns the JSON", async () => {
    const f = vi.fn(async () => Response.json({ ok: 1 }));
    const out = await qcall<{ ok: number }>("/items/x/reject", "coach", { method: "POST", body: { reason: "tone_issue" } }, f as unknown as typeof fetch);
    expect(out.ok).toBe(1);
    const [url, init] = f.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/review/items/x/reject");
    expect((init.headers as Record<string, string>)["X-Role"]).toBe("coach");
    expect(init.body).toBe('{"reason":"tone_issue"}');
  });

  it("turns a refusal into a QueueError with the server's explanation", async () => {
    const f = vi.fn(async () => Response.json({ detail: { codes: ["arithmetic_wrong"], explanation: "A sum is wrong." } }, { status: 422 }));
    const err = (await qcall("/items/x/edit", "coach", { method: "POST", body: { script: "x" } }, f as unknown as typeof fetch).catch((e: unknown) => e)) as QueueError;
    expect(err).toBeInstanceOf(QueueError);
    expect(err.status).toBe(422);
    expect(err.explanation).toBe("A sum is wrong.");
  });

  it("reports no signal as status 0", async () => {
    const f = vi.fn(async () => {
      throw new TypeError("offline");
    });
    const err = (await qcall("/items", "officer", {}, f as unknown as typeof fetch).catch((e: unknown) => e)) as QueueError;
    expect(err.status).toBe(0);
  });
});
