// A paper's own answer key on this phone. The server works it out from the paper's numbers with the
// engine (every right answer, the wrong answer each error gives, the stage signatures); the phone only
// looks it up. Keys hold no child data, so they are kept in localStorage, where the error finder can
// read them without waiting. The built-in forms are still in generated/answer_keys.json for the
// judge's sample.
import { hcall, type HubIdentity } from "./paperHub";

const STORE = "cc.paperkeys";

// the same shape as one form of generated/answer_keys.json
export interface StoredForm {
  label: string;
  items: {
    n: number;
    type: string;
    a: number;
    b: number;
    correct: number;
    probes: string[];
    wrong: Record<string, string[]>;
    untracked: Record<string, string>;
    signatures?: Record<string, string[]>;
  }[];
}

function all(): Record<string, StoredForm> {
  try {
    return JSON.parse(localStorage.getItem(STORE) ?? "{}") as Record<string, StoredForm>;
  } catch {
    return {};
  }
}

export function registeredForm(id: string): StoredForm | undefined {
  return all()[id];
}

export function registerForm(id: string, form: StoredForm): void {
  try {
    localStorage.setItem(STORE, JSON.stringify({ ...all(), [id]: form }));
  } catch {
    /* private mode: the key lasts until the page closes only if it is fetched again */
  }
}

/** Fetch the key of a paper and keep it. Papers have ids like P-0123456789ab. */
export async function fetchPaperKey(id: string, who: HubIdentity): Promise<void> {
  if (registeredForm(id)) return;
  const out = await hcall<{ forms: Record<string, StoredForm> }>(`/papers/${encodeURIComponent(id)}/key`, who);
  const form = out.forms[id];
  if (form) registerForm(id, form);
}
