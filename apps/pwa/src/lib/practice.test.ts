import "fake-indexeddb/auto";
import { describe, expect, it } from "vitest";
import { CohortDb } from "./db";
import { appendTurn, createSession, endSession, finishTranscript, PracticeError, postTurn, scenarioFor, startTranscript, type FeedbackCard } from "./practice";

let n = 0;
const fresh = () => new CohortDb(`practice-${n++}`);
const reply = (status: number, body: unknown = {}) =>
  (async () => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } })) as unknown as typeof fetch;

describe("scenarioFor", () => {
  it("rehearses the class's focus when a scenario exists, else SUB-SFL", () => {
    expect(scenarioFor("ADD-NOCARRY")).toBe("ADD-NOCARRY");
    expect(scenarioFor("PV-HEARD")).toBe("PV-HEARD");
    expect(scenarioFor("PV-REVERSE")).toBe("SUB-SFL"); // detected only: no scenario yet
    expect(scenarioFor(null)).toBe("SUB-SFL");
  });
});

describe("the practice API client", () => {
  it("posts what it is given and returns the JSON", async () => {
    const seen: { url: string; body: string }[] = [];
    const fake = (async (url: string, init: RequestInit) => {
      seen.push({ url, body: String(init.body) });
      return new Response(JSON.stringify({ session_id: "s1", seed: 5 }), { status: 200 });
    }) as unknown as typeof fetch;
    const out = await createSession({ scenario: "SUB-SFL", language: "en", judge: false, counts: { "SUB-SFL": 11 }, checked: 28 }, fake);
    expect(out.session_id).toBe("s1");
    expect(seen[0]!.url).toBe("/api/practice/sessions");
    expect(JSON.parse(seen[0]!.body)).toEqual({ scenario: "SUB-SFL", language: "en", judge: false, counts: { "SUB-SFL": 11 }, checked: 28 });
  });

  it.each([
    [503, "paused"],
    [404, "expired"],
    [409, "finished"],
    [422, "invalid"],
    [500, "other"],
  ])("maps HTTP %i to a plain failure kind (%s)", async (status, kind) => {
    await expect(postTurn("s1", { text: "hi" }, reply(status))).rejects.toMatchObject({ kind, status });
  });

  it("treats no signal as offline, so she can try again", async () => {
    const down = (async () => {
      throw new TypeError("network");
    }) as unknown as typeof fetch;
    const err = await endSession("s1", down).catch((e: unknown) => e);
    expect(err).toBeInstanceOf(PracticeError);
    expect((err as PracticeError).kind).toBe("offline");
  });
});

describe("the transcript stays on the phone", () => {
  it("is kept in IndexedDB, turn by turn, with the card at the end", async () => {
    const store = fresh();
    const id = await startTranscript("s1", "c-1", "SUB-SFL", store);
    await appendTurn(id, { turn: 1, teacher: "Meena, what is 52 minus 29?", child: "37, Miss!", speaker: "Meena" }, store);
    await appendTurn(id, { turn: 2, teacher: "Tell me how you got that.", child: "I did 9 minus 2.", speaker: "Meena" }, store);
    const card: FeedbackCard = { strengths: [], try_next: { point: "x", text: "", suggestion: "s", quote: null, turn_id: null }, note: null, source: "ai", badge: "checked" };
    await finishTranscript(id, card, store);
    const row = (await store.transcripts.get(id))!;
    expect(row.turns).toHaveLength(2);
    expect(row.ended).toBe(true);
    expect(row.sessionId).toBe("s1");
    // Practice calls queue nothing for sending: the transcript never enters the sync queue.
    expect(await store.syncQueue.count()).toBe(0);
  });
});
