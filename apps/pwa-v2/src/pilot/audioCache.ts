// Audio files kept on the phone. A file is fetched once (with the sign-in token), then saved in the
// browser's Cache Storage, so Play, Download and Share still work with no signal. The list of cards
// is saved too, for viewing offline. Queued Generate requests wait here until a signal returns.
import { jsonInit, pilotFetch, pilotJson, PilotApiError, type AudioPage, type Session } from "./api";
import { kvGet, kvSet, pilotDb, type JobRow, type PilotDb } from "./db";

const CACHE_NAME = "cc-pilot-audio-v1";

export interface AudioDeps {
  caches: CacheStorage | undefined;
  fetchFn: typeof fetch;
}

export const realDeps = (): AudioDeps => ({
  caches: typeof caches === "undefined" ? undefined : caches,
  fetchFn: (...a) => fetch(...a),
});

// An absolute address that never leaves the browser: only the cache uses it.
const keyFor = (id: string): string => `https://pilot-audio.invalid/${id}`;

export async function isSaved(id: string, deps: AudioDeps = realDeps()): Promise<boolean> {
  if (!deps.caches) return false;
  const cache = await deps.caches.open(CACHE_NAME);
  return !!(await cache.match(keyFor(id)));
}

export async function forgetAudio(id: string, deps: AudioDeps = realDeps()): Promise<void> {
  if (!deps.caches) return;
  await (await deps.caches.open(CACHE_NAME)).delete(keyFor(id));
}

/** The file for one card: from the phone if saved, else fetched once and saved. */
export async function getAudioBlob(
  id: string,
  session: Session,
  deps: AudioDeps = realDeps(),
): Promise<{ blob: Blob; fromCache: boolean }> {
  const cache = deps.caches ? await deps.caches.open(CACHE_NAME) : null;
  const hit = cache ? await cache.match(keyFor(id)) : undefined;
  if (hit) return { blob: await hit.blob(), fromCache: true };
  const res = await pilotFetch(`/api/pilot/audio/${id}/file`, {}, session, deps.fetchFn);
  if (!res.ok) throw new PilotApiError(res.status);
  const blob = await res.blob();
  if (cache) {
    try {
      await cache.put(keyFor(id), new Response(blob.slice(), { headers: { "Content-Type": blob.type } }));
    } catch {
      /* storage full: play it this once without saving */
    }
  }
  return { blob, fromCache: false };
}

// ---- the saved list --------------------------------------------------------------------------

const PAGE_KEY = "audio.page";

export async function savePage(page: AudioPage, store: PilotDb = pilotDb): Promise<void> {
  await kvSet(PAGE_KEY, page, store);
}

export async function loadPage(store: PilotDb = pilotDb): Promise<AudioPage | null> {
  return kvGet<AudioPage | null>(PAGE_KEY, null, store);
}

// ---- queued Generate requests ------------------------------------------------------------------

export type GenerateBody = JobRow["body"];

export async function queueGenerate(body: GenerateBody, store: PilotDb = pilotDb): Promise<void> {
  // one waiting request per language is enough: a newer one replaces it
  const waiting = await store.jobs.toArray();
  const same = waiting.filter((j) => j.body.language === body.language);
  await store.jobs.bulkDelete(same.map((j) => j.id!).filter((id) => id !== undefined));
  await store.jobs.add({ kind: "generate", body, createdAt: Date.now() });
}

export async function waitingJobs(store: PilotDb = pilotDb): Promise<JobRow[]> {
  return store.jobs.toArray();
}

/** Run the waiting Generate requests. Stops at the first sign of no signal. Returns how many ran. */
export async function flushJobs(
  session: Session,
  store: PilotDb = pilotDb,
  fetchFn: typeof fetch = (...a) => fetch(...a),
): Promise<number> {
  let ran = 0;
  for (const job of await store.jobs.toArray()) {
    try {
      await pilotJson("/api/pilot/audio/generate", jsonInit("POST", job.body), session, fetchFn);
    } catch (e) {
      if (e instanceof PilotApiError && e.offline) return ran;
      // a refusal such as "no sheets read yet" will not change by waiting: drop the request
    }
    if (job.id !== undefined) await store.jobs.delete(job.id);
    ran += 1;
  }
  return ran;
}
