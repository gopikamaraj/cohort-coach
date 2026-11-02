// A lesson's voice note kept on the phone. A teacher taps Save once, with a signal; the file goes
// into the browser's Cache Storage, and from then on it plays with no signal. The address is the
// key, so a new lesson version (a new address) is a new file. Nothing here touches the server.
const CACHE_NAME = "cc-lesson-audio-v1";

export interface LessonAudioDeps {
  caches: CacheStorage | undefined;
  fetchFn: typeof fetch;
}

export const realDeps = (): LessonAudioDeps => ({
  caches: typeof caches === "undefined" ? undefined : caches,
  fetchFn: (...a) => fetch(...a),
});

export async function isSaved(url: string, deps: LessonAudioDeps = realDeps()): Promise<boolean> {
  if (!deps.caches) return false;
  return !!(await (await deps.caches.open(CACHE_NAME)).match(url));
}

/** The saved file, or null if this lesson is not on the phone. */
export async function savedBlob(url: string, deps: LessonAudioDeps = realDeps()): Promise<Blob | null> {
  if (!deps.caches) return null;
  const hit = await (await deps.caches.open(CACHE_NAME)).match(url);
  return hit ? hit.blob() : null;
}

/** Fetch once and save. Returns false if there is no storage or the fetch failed. */
export async function saveLesson(url: string, deps: LessonAudioDeps = realDeps()): Promise<boolean> {
  if (!deps.caches) return false;
  try {
    const res = await deps.fetchFn(url);
    if (!res.ok) return false;
    const blob = await res.blob();
    await (await deps.caches.open(CACHE_NAME)).put(
      url,
      new Response(blob, { headers: { "Content-Type": blob.type || "audio/ogg" } }),
    );
    return true;
  } catch {
    return false; // no signal, or storage full: the lesson still plays online
  }
}

export async function forgetLesson(url: string, deps: LessonAudioDeps = realDeps()): Promise<void> {
  if (!deps.caches) return;
  await (await deps.caches.open(CACHE_NAME)).delete(url);
}
