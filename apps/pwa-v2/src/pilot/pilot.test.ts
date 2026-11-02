import "fake-indexeddb/auto";
import { describe, expect, it, vi } from "vitest";
import { PilotApiError, type Card, type Session } from "./api";
import { flushJobs, getAudioBlob, isSaved, queueGenerate, savePage, loadPage, type AudioDeps } from "./audioCache";
import { PilotDb } from "./db";
import { needsRedirect, resolveRoute } from "./route";
import { candidateTypes, canShareFiles, makeShareFile, messageWithLink, shareFiles, whatsappUrl } from "./share";
import { addFiles, clearFinished, fileMime, flushUploads, gate, retryUpload, tally } from "./uploads";

let n = 0;
const fresh = () => new PilotDb(`pilot-${n++}`);
const session: Session = { token: "t", name: "ops", roles: ["coordinator"] };
const META = { schoolCode: "SCH-01", classCode: "3A", teacherRef: "T-101", consentRef: "HM-LETTER-1" };
const file = (name: string, body: string, type = "image/jpeg") => new File([body], name, { type });
const keep = async (f: File) => f; // skip the canvas: node has none

describe("the pilot router", () => {
  it("knows two pages and sends every other address to Upload sheets", () => {
    expect(resolveRoute("#/upload")).toBe("/upload");
    expect(resolveRoute("#/audio")).toBe("/audio");
    for (const hash of ["", "#/home", "#/practice", "#/coach", "#/admin", "#/judge", "#/roles", "#/tour/3", "#/flow", "#/nonsense"]) {
      expect(resolveRoute(hash)).toBe("/upload");
      expect(needsRedirect(hash)).toBe(true);
    }
    expect(needsRedirect("#/audio")).toBe(false);
    expect(resolveRoute("#/audio?x=1")).toBe("/audio");
  });
});

describe("the consent gate", () => {
  it("blocks adding sheets until consent is confirmed with a reference and the codes are filled", () => {
    expect(gate(META, false)).toBe("consent");
    expect(gate({ ...META, consentRef: "" }, true)).toBe("consent");
    expect(gate({ ...META, consentRef: "  " }, true)).toBe("consent");
    expect(gate({ ...META, schoolCode: "" }, true)).toBe("codes");
    expect(gate({ ...META, teacherRef: "Mrs Lakshmi" }, true)).toBe("codes");
    expect(gate(META, true)).toBe("ok");
  });
});

describe("file kinds", () => {
  it("accepts JPG, PNG, HEIC and PDF, by type or extension", () => {
    expect(fileMime({ type: "image/jpeg", name: "a.jpg" })).toBe("image/jpeg");
    expect(fileMime({ type: "", name: "IMG_1.HEIC" })).toBe("image/heic");
    expect(fileMime({ type: "image/heif", name: "x" })).toBe("image/heic");
    expect(fileMime({ type: "application/pdf", name: "s.pdf" })).toBe("application/pdf");
    expect(fileMime({ type: "text/plain", name: "a.txt" })).toBeNull();
  });
});

describe("the upload queue", () => {
  it("skips a duplicate checksum for the same school and counts it", async () => {
    const s = fresh();
    const first = await addFiles([file("a.jpg", "same"), file("b.jpg", "other")], META, s, keep);
    expect(first).toEqual({ added: 2, skipped: 0, rejected: 0 });
    const again = await addFiles([file("c.jpg", "same")], META, s, keep);
    expect(again).toEqual({ added: 0, skipped: 1, rejected: 0 });
    const otherSchool = await addFiles([file("d.jpg", "same")], { ...META, schoolCode: "SCH-02" }, s, keep);
    expect(otherSchool.added).toBe(1);
  });

  it("rejects other file types and stores no file name", async () => {
    const s = fresh();
    const out = await addFiles([file("notes.txt", "x", "text/plain"), file("Meena-sheet.jpg", "y")], META, s, keep);
    expect(out).toEqual({ added: 1, skipped: 0, rejected: 1 });
    const row = (await s.uploads.toArray())[0]!;
    expect(JSON.stringify({ ...row, blob: 0 })).not.toContain("Meena");
    expect(row.status).toBe("queued");
  });

  const okFetch = (log: string[] = []) =>
    vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
      const u = String(url);
      log.push(`${init?.method ?? "GET"} ${u}`);
      if (u.endsWith("/sheets/init"))
        return Response.json({ id: "s1", duplicate: false, upload: { url: "https://store.test/put", headers: { "Content-Type": "image/jpeg" } } });
      if (u === "https://store.test/put") return new Response("", { status: 200 });
      return Response.json({ id: "s1", status: "stored" });
    });

  it("uploads in order and frees the photo once it is stored", async () => {
    const s = fresh();
    await addFiles([file("a.jpg", "one")], META, s, keep);
    const log: string[] = [];
    await flushUploads(session, s, okFetch(log) as unknown as typeof fetch);
    expect(log).toEqual(["POST /api/pilot/sheets/init", "PUT https://store.test/put", "POST /api/pilot/sheets/s1/complete"]);
    const row = (await s.uploads.toArray())[0]!;
    expect(row.status).toBe("stored");
    expect(row.blob.size).toBe(0);
    expect(row.sheetId).toBe("s1");
  });

  it("keeps a sheet queued with no signal and sends it when the signal returns", async () => {
    const s = fresh();
    await addFiles([file("a.jpg", "one"), file("b.jpg", "two")], META, s, keep);
    const down = vi.fn(async () => {
      throw new TypeError("offline");
    });
    await flushUploads(session, s, down as unknown as typeof fetch);
    expect(tally(await s.uploads.toArray())).toEqual({ queued: 2, uploading: 0, stored: 0, failed: 0 });
    await flushUploads(session, s, okFetch() as unknown as typeof fetch);
    expect(tally(await s.uploads.toArray()).stored).toBe(2);
  });

  it("marks a sheet failed on a server refusal, and a retry puts it back in the queue", async () => {
    const s = fresh();
    await addFiles([file("a.jpg", "one")], META, s, keep);
    const refuse = vi.fn(async () => new Response("{}", { status: 422 }));
    await flushUploads(session, s, refuse as unknown as typeof fetch);
    const row = (await s.uploads.toArray())[0]!;
    expect(row.status).toBe("failed");
    await retryUpload(row.id!, s);
    expect((await s.uploads.get(row.id!))!.status).toBe("queued");
    await flushUploads(session, s, okFetch() as unknown as typeof fetch);
    expect((await s.uploads.get(row.id!))!.status).toBe("stored");
  });

  it("stops and keeps the queue when the sign-in has ended", async () => {
    const s = fresh();
    await addFiles([file("a.jpg", "one")], META, s, keep);
    const ended = vi.fn(async () => new Response("{}", { status: 401 }));
    await flushUploads(session, s, ended as unknown as typeof fetch);
    expect(tally(await s.uploads.toArray()).queued).toBe(1);
  });

  it("treats a server-side duplicate as stored and clears finished rows on request", async () => {
    const s = fresh();
    await addFiles([file("a.jpg", "one")], META, s, keep);
    const dup = vi.fn(async () => Response.json({ id: "s9", duplicate: true, status: "read" }));
    await flushUploads(session, s, dup as unknown as typeof fetch);
    const row = (await s.uploads.toArray())[0]!;
    expect(row.status).toBe("stored");
    expect(row.duplicate).toBe(true);
    await clearFinished(s);
    expect(await s.uploads.count()).toBe(0);
  });
});

describe("sharing on WhatsApp", () => {
  const f = new File(["x"], "cc-pilot-slot1-ta.m4a", { type: "audio/mp4" });

  it("detects file sharing with navigator.canShare", () => {
    expect(canShareFiles([f], { canShare: () => true, share: async () => undefined })).toBe(true);
    expect(canShareFiles([f], { canShare: () => false, share: async () => undefined })).toBe(false);
    expect(canShareFiles([f], {})).toBe(false);
    expect(canShareFiles([f], { canShare: () => true })).toBe(false); // no share function
  });

  it("opens the share sheet with the files attached when it can", async () => {
    const share = vi.fn(async () => undefined);
    const out = await shareFiles([f], "hello", { canShare: () => true, share });
    expect(out).toBe("shared");
    expect(share).toHaveBeenCalledWith({ files: [f], text: "hello" });
  });

  it("reports unsupported so the fallback shows, and cancelled when she closes the sheet", async () => {
    expect(await shareFiles([f], "hi", {})).toBe("unsupported");
    const abort = async () => {
      throw new DOMException("closed", "AbortError");
    };
    expect(await shareFiles([f], "hi", { canShare: () => true, share: abort })).toBe("cancelled");
    const boom = async () => {
      throw new Error("x");
    };
    expect(await shareFiles([f], "hi", { canShare: () => true, share: boom })).toBe("failed");
  });

  it("builds the wa.me fallback with the message and the signed link", () => {
    const url = whatsappUrl(messageWithLink("Lesson 1. Listen.", "https://x.test/a?sig=1&e=2"));
    expect(url.startsWith("https://wa.me/?text=")).toBe(true);
    expect(decodeURIComponent(url.split("text=")[1]!)).toBe("Lesson 1. Listen.\nhttps://x.test/a?sig=1&e=2");
  });

  it("tries audio types until the phone accepts one", () => {
    const accepts = (t: string) => ({ canShare: (d: ShareData) => d.files?.[0]?.type === t });
    expect(makeShareFile(new Blob(["x"]), "a.m4a", "audio/mp4", accepts("audio/x-m4a")).type).toBe("audio/x-m4a");
    expect(makeShareFile(new Blob(["x"]), "a.m4a", "audio/mp4", accepts("nothing")).type).toBe("audio/mp4");
    expect(candidateTypes("audio/mpeg")[0]).toBe("audio/mpeg");
  });
});

class FakeCache {
  store = new Map<string, Response>();
  async match(k: string) {
    return this.store.get(k)?.clone();
  }
  async put(k: string, r: Response) {
    this.store.set(k, r);
  }
  async delete(k: string) {
    return this.store.delete(k);
  }
}
const fakeCaches = () => {
  const c = new FakeCache();
  return { caches: { open: async () => c } as unknown as CacheStorage, c };
};

describe("audio kept on the phone", () => {
  it("fetches a file once, saves it, and then works with no signal", async () => {
    const { caches, c } = fakeCaches();
    let calls = 0;
    const fetchFn = vi.fn(async () => {
      calls += 1;
      return new Response(new Blob(["audio-bytes"], { type: "audio/mp4" }));
    });
    const deps: AudioDeps = { caches, fetchFn: fetchFn as unknown as typeof fetch };
    const first = await getAudioBlob("a1", session, deps);
    expect(first.fromCache).toBe(false);
    expect(await isSaved("a1", deps)).toBe(true);
    const offline: AudioDeps = { caches, fetchFn: (async () => { throw new TypeError("offline"); }) as unknown as typeof fetch };
    const second = await getAudioBlob("a1", session, offline);
    expect(second.fromCache).toBe(true);
    expect(await second.blob.text()).toBe("audio-bytes");
    expect(calls).toBe(1);
    expect(c.store.size).toBe(1);
  });

  it("does not save a refusal", async () => {
    const { caches } = fakeCaches();
    const deps: AudioDeps = { caches, fetchFn: (async () => new Response("{}", { status: 409 })) as unknown as typeof fetch };
    await expect(getAudioBlob("a2", session, deps)).rejects.toBeInstanceOf(PilotApiError);
    expect(await isSaved("a2", deps)).toBe(false);
  });

  it("keeps the last list for viewing offline", async () => {
    const s = fresh();
    expect(await loadPage(s)).toBeNull();
    const card = { id: "c1", slot: 1 } as unknown as Card;
    await savePage({ cards: [card], audio_count: 3, sheets_read: 20, classes_read: 1 }, s);
    expect((await loadPage(s))!.cards[0]!.id).toBe("c1");
  });
});

describe("Generate with no signal", () => {
  it("queues one request per language and runs it when the signal returns", async () => {
    const s = fresh();
    await queueGenerate({ language: "ta", voice: "ritu", force: false }, s);
    await queueGenerate({ language: "ta", voice: "priya", force: false }, s);
    await queueGenerate({ language: "en", voice: "ritu", force: false }, s);
    expect(await s.jobs.count()).toBe(2);
    const down = vi.fn(async () => {
      throw new TypeError("offline");
    });
    expect(await flushJobs(session, s, down as unknown as typeof fetch)).toBe(0);
    expect(await s.jobs.count()).toBe(2);
    const bodies: string[] = [];
    const up = vi.fn(async (_u: RequestInfo | URL, init?: RequestInit) => {
      bodies.push(String(init?.body));
      return Response.json({ made: 3 });
    });
    expect(await flushJobs(session, s, up as unknown as typeof fetch)).toBe(2);
    expect(await s.jobs.count()).toBe(0);
    expect(bodies.some((b) => b.includes('"voice":"priya"'))).toBe(true);
  });
});
