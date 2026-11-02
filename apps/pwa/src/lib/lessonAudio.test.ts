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

describe("following the lesson text as it plays", () => {
  const timing = [
    { i: 0, start: 0, end: 2.5 },
    { i: 1, start: 2.75, end: 5 },
    { i: 2, start: 5.5, end: 8 },
  ];

  it("finds the sentence being said, and none in a pause or after the end", async () => {
    const { sentenceAt } = await import("./lessonAudio");
    expect(sentenceAt(timing, 0)).toBe(0);
    expect(sentenceAt(timing, 2.6)).toBeNull(); // the 250 ms pause between sentences
    expect(sentenceAt(timing, 3)).toBe(1);
    expect(sentenceAt(timing, 5.2)).toBeNull(); // the 500 ms pause between sections
    expect(sentenceAt(timing, 7.99)).toBe(2);
    expect(sentenceAt(timing, 8)).toBeNull();
  });

  it("shows a file size as a count", async () => {
    const { sizeLabel } = await import("./lessonAudio");
    expect(sizeLabel(1_234_567)).toBe("1.2 MB");
    expect(sizeLabel(350_400)).toBe("350 KB");
    expect(sizeLabel(10)).toBe("1 KB");
  });
});
