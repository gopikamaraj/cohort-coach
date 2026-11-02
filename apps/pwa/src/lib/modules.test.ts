// The module screen's helpers and calls: the closed-button reason, the end banner, and the offline copy.
import { beforeEach, describe, expect, it, vi } from "vitest";
import { endBanner, getNext, loadTrack, ModuleError, nextBlocked, type TrackView } from "./modules";
import en from "../../../../strings/en.json";
import hi from "../../../../strings/hi.json";
import ta from "../../../../strings/ta.json";

function track(over: Partial<TrackView> = {}): TrackView {
  return {
    id: "trk-1",
    cohort_id: "cc-1",
    error: "ADD-NOCARRY",
    status: "active",
    stop_reason: null,
    start_date: "2026-11-02",
    end_date: "2026-11-30",
    language: "en",
    note: null,
    total: 3,
    current: 2,
    can_next: { enabled: false, code: "needs_feedback", number: 2, next: 3, due_date: "2026-11-17" },
    modules: [],
    ...over,
  };
}

function reply(body: unknown, status = 200): typeof fetch {
  return (async () => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } })) as typeof fetch;
}

beforeEach(() => {
  const store = new Map<string, string>();
  vi.stubGlobal("localStorage", {
    getItem: (k: string) => store.get(k) ?? null,
    setItem: (k: string, v: string) => void store.set(k, v),
    removeItem: (k: string) => void store.delete(k),
    clear: () => store.clear(),
  });
});

describe("the closed Get the next module button", () => {
  it("says which module to answer, which comes next, and when it arrives by itself", () => {
    expect(nextBlocked(track())).toEqual({ key: "module.next_blocked", slots: { n: 2, next: 3, date: "2026-11-17" } });
  });
  it("has no reason when it is open or the track is over", () => {
    expect(nextBlocked(track({ can_next: { enabled: true, code: "ok", next: 3 } }))).toBeNull();
    expect(nextBlocked(track({ can_next: { enabled: false, code: "track_cap" } }))).toBeNull();
  });
  it("has the reason sentence in all three languages, with the same slots", () => {
    for (const t of [en, hi, ta] as Record<string, string>[]) {
      const s = t["module.next_blocked"] ?? "";
      expect(s).toContain("{n}");
      expect(s).toContain("{next}");
      expect(s).toContain("{date}");
    }
  });
});

describe("the end of a track", () => {
  it("shows nothing while it runs", () => expect(endBanner(track())).toBeNull());
  it("sends her to a person at the cap and when no approach is left", () => {
    expect(endBanner(track({ status: "stopped", stop_reason: "cap" }))).toBe("module.cap_banner");
    expect(endBanner(track({ status: "stopped", stop_reason: "exhausted" }))).toBe("module.exhausted_banner");
  });
  it("says it is time for the next check when the plan finished or the date passed", () => {
    expect(endBanner(track({ status: "completed", stop_reason: "done" }))).toBe("module.end_banner");
    expect(endBanner(track({ status: "completed", stop_reason: "end_date" }))).toBe("module.end_banner");
  });
  it("uses no word lesson in the module strings of any language", () => {
    for (const [lang, t] of [["en", en], ["hi", hi], ["ta", ta]] as [string, Record<string, string>][]) {
      for (const [k, v] of Object.entries(t)) {
        if (k.startsWith("module.")) expect(v.toLowerCase(), `${lang}:${k}`).not.toContain("lesson");
      }
    }
  });
});

describe("loading the track", () => {
  it("reads it from the server and keeps a copy for when the phone is offline", async () => {
    const got = await loadTrack("cc-1", "ADD-NOCARRY", "en", reply([track()]));
    expect(got.offline).toBe(false);
    expect(got.track?.id).toBe("trk-1");
    const down = (async () => {
      throw new TypeError("network");
    }) as unknown as typeof fetch;
    const again = await loadTrack("cc-1", "ADD-NOCARRY", "en", down);
    expect(again.offline).toBe(true);
    expect(again.track?.id).toBe("trk-1");
  });
  it("drops the copy when the server no longer has the track", async () => {
    await loadTrack("cc-1", "ADD-NOCARRY", "en", reply([track()]));
    await loadTrack("cc-1", "ADD-NOCARRY", "en", reply([]));
    const down = (async () => {
      throw new TypeError("network");
    }) as unknown as typeof fetch;
    expect((await loadTrack("cc-1", "ADD-NOCARRY", "en", down)).track).toBeNull();
  });
  it("shows a refusal from the server as an error, not as being offline", async () => {
    await expect(loadTrack("cc-1", "ADD-NOCARRY", "en", reply({ detail: { code: "x" } }, 500))).rejects.toBeInstanceOf(ModuleError);
  });
  it("a closed button (409) comes back with its code", async () => {
    await expect(getNext("trk-1", "en", reply({ detail: { code: "needs_feedback" } }, 409))).rejects.toMatchObject({ status: 409, code: "needs_feedback" });
  });
});
