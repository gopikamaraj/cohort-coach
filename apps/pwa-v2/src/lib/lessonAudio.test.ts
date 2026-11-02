import { describe, expect, it } from "vitest";
import { forgetLesson, isSaved, saveLesson, savedBlob, type LessonAudioDeps } from "./lessonAudio";

function fakeCaches(): CacheStorage {
  const store = new Map<string, Response>();
  const cache = {
    match: async (k: string) => store.get(k)?.clone(),
    put: async (k: string, r: Response) => void store.set(k, r),
    delete: async (k: string) => store.delete(k),
  };
  return { open: async () => cache } as unknown as CacheStorage;
}

const ok = (body: string): typeof fetch => (async () => new Response(new Blob([body], { type: "audio/ogg" }))) as typeof fetch;

describe("lesson audio on the phone", () => {
  it("saves once, then reads the same bytes back with no network", async () => {
    const deps: LessonAudioDeps = { caches: fakeCaches(), fetchFn: ok("voice") };
    expect(await isSaved("/l/1", deps)).toBe(false);
    expect(await saveLesson("/l/1", deps)).toBe(true);
    const offline: LessonAudioDeps = { caches: deps.caches, fetchFn: (async () => { throw new Error("offline"); }) as typeof fetch };
    expect(await isSaved("/l/1", offline)).toBe(true);
    expect(await (await savedBlob("/l/1", offline))!.text()).toBe("voice");
  });

  it("a failed fetch saves nothing and says so", async () => {
    const down: LessonAudioDeps = { caches: fakeCaches(), fetchFn: (async () => { throw new Error("offline"); }) as typeof fetch };
    expect(await saveLesson("/l/1", down)).toBe(false);
    expect(await isSaved("/l/1", down)).toBe(false);
    const refused: LessonAudioDeps = { caches: fakeCaches(), fetchFn: (async () => new Response("no", { status: 403 })) as typeof fetch };
    expect(await saveLesson("/l/1", refused)).toBe(false);
  });

  it("a new address is a new file, and forget removes one", async () => {
    const deps: LessonAudioDeps = { caches: fakeCaches(), fetchFn: ok("a") };
    await saveLesson("/l/v1", deps);
    expect(await isSaved("/l/v2", deps)).toBe(false);
    await forgetLesson("/l/v1", deps);
    expect(await isSaved("/l/v1", deps)).toBe(false);
  });

  it("without Cache Storage it reports false and never throws", async () => {
    const none: LessonAudioDeps = { caches: undefined, fetchFn: ok("a") };
    expect(await saveLesson("/l/1", none)).toBe(false);
    expect(await savedBlob("/l/1", none)).toBeNull();
  });
});
