import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getUser, installIdentity, normalise, register, signIn, signOut, userHeader } from "./identity";

const mem = new Map<string, string>();

beforeEach(() => {
  mem.clear();
  vi.stubGlobal("localStorage", { getItem: (k: string) => mem.get(k) ?? null, setItem: (k: string, v: string) => void mem.set(k, v), removeItem: (k: string) => void mem.delete(k) });
  vi.stubGlobal("window", { dispatchEvent: () => true });
});
afterEach(() => vi.unstubAllGlobals());

const reply = (status: number, body: unknown): typeof fetch => (async () => new Response(JSON.stringify(body), { status })) as unknown as typeof fetch;

describe("the nickname is the user id", () => {
  it("is normalised: NFKC, single spaces, lower case", () => {
    expect(normalise("  Priya   Devi ")).toBe("priya devi");
    expect(normalise("ＡＢＣ")).toBe("abc");
  });
  it("registering stores the user and the header carries the encoded id (a Tamil nickname survives a header)", async () => {
    expect(userHeader()).toEqual({});
    const res = await register("தமிழ் ஆசிரியர்", reply(201, { id: "தமிழ் ஆசிரியர்", nickname: "தமிழ் ஆசிரியர்" }));
    expect(res.ok).toBe(true);
    expect(getUser()?.id).toBe("தமிழ் ஆசிரியர்");
    expect(userHeader()["X-User"]).toBe(encodeURIComponent("தமிழ் ஆசிரியர்"));
    expect(getUser()).toBe(getUser()); // the same object until it changes, so React can subscribe
  });
  it("a taken nickname is reported as taken and signs no one in", async () => {
    const res = await register("ravi", reply(409, { detail: { code: "taken", message: "That nickname is taken." } }));
    expect(res).toMatchObject({ ok: false, code: "taken" });
    expect(getUser()).toBeNull();
  });
  it("signing in with an unknown nickname says so; with a known one it signs in; signing out forgets", async () => {
    expect(await signIn("nobody", reply(404, { detail: { code: "unknown", message: "" } }))).toMatchObject({ ok: false, code: "unknown" });
    expect((await signIn("ravi", reply(200, { id: "ravi", nickname: "Ravi" }))).ok).toBe(true);
    expect(getUser()?.nickname).toBe("Ravi");
    signOut();
    expect(getUser()).toBeNull();
  });
  it("no connection is reported as offline", async () => {
    const down = (async () => {
      throw new TypeError("no connection");
    }) as unknown as typeof fetch;
    expect(await signIn("ravi", down)).toMatchObject({ ok: false, code: "offline" });
  });
  it("every call to our own API carries the user, and calls elsewhere do not", async () => {
    mem.set("cc.user", JSON.stringify({ id: "ravi", nickname: "Ravi" }));
    const seen: { url: string; user: string | null }[] = [];
    vi.stubGlobal("window", {
      dispatchEvent: () => true,
      fetch: async (input: RequestInfo | URL, init?: RequestInit) => {
        seen.push({ url: String(input), user: new Headers(init?.headers).get("X-User") });
        return new Response("{}");
      },
    });
    installIdentity();
    await (window.fetch as typeof fetch)("/api/store");
    await (window.fetch as typeof fetch)("https://elsewhere.example/x");
    expect(seen).toEqual([{ url: "/api/store", user: "ravi" }, { url: "https://elsewhere.example/x", user: null }]);
  });
});
