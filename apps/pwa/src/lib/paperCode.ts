// Terms are off (correction 9, DECISIONS 2026-11-03): a paper's code no longer carries a term. Papers made before
// that have a code ending in " · T1" (or T2 for a post-test twin). The stored code is not changed (nobody's data is
// rewritten); the term is only left out where a code is shown. New codes are made without it by the server.
const TERM_SUFFIX = / · T\d+$/;

/** A paper code as it is shown: without the old term suffix. */
export function shownCode(code: string): string;
export function shownCode(code: string | null | undefined): string | null;
export function shownCode(code: string | null | undefined): string | null {
  return typeof code === "string" ? code.replace(TERM_SUFFIX, "") : null;
}

/** Every `check_code` in a reply from the papers API, as it is shown. Nothing else in the reply is touched. */
export function withoutTerms<T>(value: T): T {
  if (Array.isArray(value)) return value.map((v) => withoutTerms(v)) as unknown as T;
  if (value && typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      out[k] = k === "check_code" && typeof v === "string" ? shownCode(v) : withoutTerms(v);
    }
    return out as T;
  }
  return value;
}
