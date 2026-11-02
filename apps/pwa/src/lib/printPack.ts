// The answer-sheet pages of the printed pack: for each roll number that showed the mistake, the kept photo of
// that child's sheet (only if she agreed to keep sheets) with a box round each question and answer that had it.
// The photos come back from the private bucket to this phone only, are boxed here, and are printed from here.
import { API_BASE } from "./api";
import { fetchKept } from "./keptSheets";
import { annotate, type LayoutMap } from "./sheetBoxes";
import type { AnswerMap } from "./results";

export interface PrintQuestion {
  n: number;
  question: string; // "703 − 468"
  wrote: string; // what the child wrote ("blank" and "unreadable" are words, not numbers)
}

export interface PrintSheet {
  roll: number;
  possible: boolean; // seen on one question only (not confirmed on enough questions)
  questions: PrintQuestion[];
  url: string | null; // the photo to print; null when none is kept for this roll number
  placed: boolean; // the boxes were drawn on it
}

async function layoutFor(paperId: string | null | undefined, role: string, fetchFn: typeof fetch): Promise<LayoutMap | null> {
  if (!paperId) return null;
  try {
    const res = await fetchFn(`${API_BASE}/api/papers/${encodeURIComponent(paperId)}/layout.json`, { headers: { "X-Role": role === "mentor" ? "mentor" : "teacher" } });
    return res.ok ? ((await res.json()) as LayoutMap) : null;
  } catch {
    return null;
  }
}

/** Which questions of this roll number showed the error (the ones the answer map marks for it). */
export function questionsWith(map: AnswerMap, roll: number, code: string): PrintQuestion[] {
  const row = map.rolls.find((r) => r.roll === roll);
  if (!row) return [];
  return row.cells
    .filter((c) => c.codes.includes(code))
    .map((c) => {
      const item = map.items.find((i) => i.n === c.n);
      return { n: c.n, question: item ? item.question : String(c.n), wrote: String(c.given) };
    });
}

export async function loadSheets(input: {
  role: string;
  classId: string;
  checkId: string;
  paperId?: string | null;
  map: AnswerMap;
  code: string;
  rolls: { confirmed: number[]; possible: number[] };
  fetchFn?: typeof fetch;
}): Promise<PrintSheet[]> {
  const fetchFn = input.fetchFn ?? ((...a: Parameters<typeof fetch>) => fetch(...a));
  const layout = await layoutFor(input.paperId, input.role, fetchFn);
  const out: PrintSheet[] = [];
  const all = [...input.rolls.confirmed.map((roll) => ({ roll, possible: false })), ...input.rolls.possible.map((roll) => ({ roll, possible: true }))];
  for (const { roll, possible } of all) {
    const questions = questionsWith(input.map, roll, input.code);
    try {
      const photo = await fetchKept(input.role, input.classId, input.checkId, roll, fetchFn);
      const made = await annotate(photo, layout, questions.map((q) => q.n));
      out.push({ roll, possible, questions, url: made.url, placed: made.placed });
    } catch {
      out.push({ roll, possible, questions, url: null, placed: false });
    }
  }
  return out;
}
