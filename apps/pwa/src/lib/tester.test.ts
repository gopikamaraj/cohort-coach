import "fake-indexeddb/auto";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CohortDb, db } from "./db";
import {
  browserFamily, captureInvite, connectionClass, declineSharing, deleteMyData, deviceClassOf, deviceUuid, durationBucket,
  flush, getPrefs, giveConsent, inviteFromLocation, osFamily, pauseSharing, queueFeedback, queuedCounts, resetForTests, sha256Hex, track,
} from "./tester";

const SALT = "cc-tester-v1";
let n = 0;
let store: CohortDb;
let calls: { url: string; init?: RequestInit }[];
let online = true;
let failEvents = false;

function fakeFetch(): typeof fetch {
  return (async (url: string, init?: RequestInit) => {
    calls.push({ url, init });
    if (url.endsWith("/api/tester/config")) return Response.json({ enabled: true, salt: SALT });
    if (!online) throw new TypeError("offline");
    if (failEvents && url.endsWith("/api/tester/events")) return new Response("{}", { status: 503 });
    return Response.json({ ok: 1 });
  }) as typeof fetch;
}

beforeEach(async () => {
  await db.settings.clear(); // track() persists its queue in the default database
  n++;
  store = new CohortDb(`tester-${n}`);
  calls = [];
  online = true;
  failEvents = false;
  const mem = new Map<string, string>();
  vi.stubGlobal("localStorage", { getItem: (k: string) => mem.get(k) ?? null, setItem: (k: string, v: string) => void mem.set(k, v), removeItem: (k: string) => void mem.delete(k) });
  vi.stubGlobal("navigator", { onLine: true, userAgent: "Mozilla/5.0 (Linux; Android 13) Chrome/120 Mobile Safari/537.36" });
  vi.stubGlobal("window", { innerWidth: 390, location: { search: "", hash: "" }, matchMedia: () => ({ matches: false }) });
  vi.stubGlobal("document", { documentElement: { lang: "en" } });
  resetForTests();
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

const bodies = () => calls.filter((c) => !c.url.endsWith("/config")).map((c) => `${c.url} ${JSON.stringify(c.init?.headers ?? {})} ${String(c.init?.body ?? "")}`);

describe("coarse helpers", () => {
  it("buckets durations", () => {
    expect([5_000, 20_000, 60_000, 300_000].map(durationBucket)).toEqual(["under_10s", "10_30s", "30s_2m", "over_2m"]);
  });
  it("keeps family names only, never the user-agent string", () => {
    expect(browserFamily("Mozilla/5.0 (Linux; Android 13) Chrome/120 Mobile Safari/537.36")).toBe("chrome");
    expect(browserFamily("Mozilla/5.0 (iPhone; CPU iPhone OS 17) AppleWebKit Version/17 Mobile Safari/604")).toBe("safari");
    expect(osFamily("Mozilla/5.0 (Linux; Android 13)")).toBe("android");
    expect(osFamily("Mozilla/5.0 (Windows NT 10.0)")).toBe("windows");
  });
  it("classes the device from the screen width and the connection from the link", () => {
    expect([390, 800, 1400].map(deviceClassOf)).toEqual(["phone", "tablet", "desktop"]);
    expect(connectionClass(false)).toBe("offline");
    expect(connectionClass(true, "2g")).toBe("slow");
    expect(connectionClass(true, "4g")).toBe("fast");
  });
  it("reads ?src= and ?team= from the address, only well-formed values", () => {
    expect(inviteFromLocation("?src=edu-mentor", "")).toEqual({ src: "edu-mentor", team: null });
    expect(inviteFromLocation("", "#/roles?src=teachers&team=tok")).toEqual({ src: "teachers", team: "tok" });
    expect(inviteFromLocation("?src=Bad Value!", "").src).toBeNull();
  });
  it("keeps the first invite source it saw", () => {
    captureInvite("?src=teachers", "");
    captureInvite("?src=tech-mentor", "");
    expect(getPrefs().src).toBe("teachers");
  });
});

describe("consent first", () => {
  it("sends nothing, and the app still works, when sharing was declined", async () => {
    declineSharing();
    track("screen_viewed", { screen_id: "home" });
    queueFeedback({ rating: 5, tags: [] });
    await flush(fakeFetch(), store);
    expect(queuedCounts()).toEqual({ events: 0, feedback: 0 });
    expect(calls).toHaveLength(0);
  });
  it("sends nothing before a choice is made", async () => {
    track("screen_viewed", { screen_id: "home" });
    await flush(fakeFetch(), store);
    expect(calls).toHaveLength(0);
  });
  it("sends nothing while paused, and queues nothing", async () => {
    giveConsent("Asha", false);
    pauseSharing(true);
    track("screen_viewed", { screen_id: "home" });
    await flush(fakeFetch(), store);
    expect(calls).toHaveLength(0);
  });
});

describe("the device id", () => {
  it("is a stable random id kept on the device and is not derived from anything about it", async () => {
    const a = await deviceUuid(store);
    expect(await deviceUuid(store)).toBe(a);
    expect(a).toMatch(/^[0-9a-f-]{32,36}$/);
  });
  it("hashes with SHA-256 over the salt and the id", async () => {
    expect(await sha256Hex("abc")).toBe("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
  });
  it("never puts the raw id in any request; only the 64-character salted hash", async () => {
    const raw = await deviceUuid(store);
    giveConsent("Asha", true);
    track("screen_viewed", { screen_id: "home" });
    queueFeedback({ rating: 4, tags: ["easy"], comment: "fine" });
    await flush(fakeFetch(), store);
    const sent = bodies();
    expect(sent.length).toBeGreaterThanOrEqual(3);
    for (const s of sent) expect(s).not.toContain(raw);
    const hash = await sha256Hex(SALT + raw);
    expect(sent.some((s) => s.includes(hash))).toBe(true);
    expect(sent.join("\n")).not.toMatch(/Mozilla|userAgent|Android 13/);
  });
});

describe("queueing and batches", () => {
  it("keeps events while offline and sends them later in order", async () => {
    giveConsent("Asha", false);
    online = false;
    track("screen_viewed", { screen_id: "home" });
    track("feature_used", { feature_id: "practice_turn" });
    await flush(fakeFetch(), store);
    expect(queuedCounts().events).toBeGreaterThanOrEqual(2);
    online = true;
    await flush(fakeFetch(), store);
    expect(queuedCounts().events).toBe(0);
    const ev = calls.find((c) => c.url.endsWith("/events"));
    const types = (JSON.parse(String(ev?.init?.body)).events as { type: string }[]).map((e) => e.type);
    expect(types).toEqual(["session_start", "screen_viewed", "feature_used"]);
  });
  it("keeps a batch the server could not take, and sends it again", async () => {
    giveConsent("Asha", false);
    failEvents = true;
    await flush(fakeFetch(), store);
    expect(queuedCounts().events).toBe(1);
    failEvents = false;
    await flush(fakeFetch(), store);
    expect(queuedCounts().events).toBe(0);
  });
  it("sends at most 50 events a request", async () => {
    giveConsent("Asha", false);
    for (let i = 0; i < 120; i++) track("screen_viewed", { screen_id: "home" });
    await flush(fakeFetch(), store);
    const sizes = calls.filter((c) => c.url.endsWith("/events")).map((c) => JSON.parse(String(c.init?.body)).events.length as number);
    expect(sizes.every((s) => s <= 50)).toBe(true);
    expect(sizes.reduce((a, b) => a + b, 0)).toBe(121);
  });
  it("never lets tracking throw into the app", () => {
    vi.stubGlobal("navigator", undefined);
    expect(() => track("screen_viewed")).not.toThrow();
  });
});

describe("Delete my data", () => {
  it("asks the server to delete by hash, then clears the device and stops sharing", async () => {
    const before = await deviceUuid(store);
    giveConsent("Asha", true);
    await flush(fakeFetch(), store);
    const out = await deleteMyData(fakeFetch(), store);
    expect(out).toBe("deleted");
    const del = calls.find((c) => c.init?.method === "DELETE");
    expect(del?.url).toContain("/api/tester/me");
    expect((del?.init?.headers as Record<string, string>)["X-Device-Hash"]).toMatch(/^[0-9a-f]{64}$/);
    expect(getPrefs()).toMatchObject({ consent: "no", nickname: "" });
    expect(queuedCounts()).toEqual({ events: 0, feedback: 0 });
    expect(await deviceUuid(store)).not.toBe(before); // a new random id, if they ever opt in again
  });
  it("still clears the device when the server cannot be reached", async () => {
    giveConsent("Asha", true);
    await flush(fakeFetch(), store);
    online = false;
    expect(await deleteMyData(fakeFetch(), store)).toBe("device_only");
    expect(getPrefs().consent).toBe("no");
  });
});
