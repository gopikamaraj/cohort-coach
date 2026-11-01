// An answer key from a text file (.json, .csv or .txt), read in the browser. Only the question numbers and
// their answers are taken: anything else in the file (a pilot answer file also lists every child's roll
// number and answers) is dropped here and never sent. The server uses the key only to cross-check the
// answers code works out, and to fill a dictated question's number; it never replaces them.

export const MAX_KEY_ITEMS = 30;
export const MAX_KEY_BYTES = 2_000_000; // a pilot answer file is large; only its questions are read
export const MAX_ANSWER = 999;

export interface ParsedKey {
  /** question number -> answer */
  answers: Record<number, number>;
  items: number;
}

export class KeyFileError extends Error {}

function whole(v: unknown): number | null {
  if (typeof v === "number" && Number.isInteger(v)) return v;
  if (typeof v === "string" && /^\s*\d{1,4}\s*$/.test(v)) return Number(v);
  return null;
}

function check(n: number | null, a: number | null, where: string): [number, number] {
  if (n === null || n < 1 || n > MAX_KEY_ITEMS) throw new KeyFileError(`${where}: not a question number from 1 to ${MAX_KEY_ITEMS}`);
  if (a === null || a < 0 || a > MAX_ANSWER) throw new KeyFileError(`${where}: question ${n} needs a whole-number answer from 0 to ${MAX_ANSWER}`);
  return [n, a];
}

function finish(rows: [number, number][]): ParsedKey {
  if (rows.length === 0) throw new KeyFileError("no question and answer pairs found");
  const answers: Record<number, number> = {};
  for (const [n, a] of rows) answers[n] = a;
  return { answers, items: Object.keys(answers).length };
}

function fromJson(text: string): ParsedKey {
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    throw new KeyFileError("this is not valid JSON");
  }
  const root = data as Record<string, unknown>;
  // a list of { question_no, answer } (also read: no, n, q or question; key or correct_answer), alone or under
  // test.questions or questions. Anything else in the file, such as per-class or per-child rows, is ignored.
  const list = Array.isArray(data) ? data : Array.isArray((root?.["test"] as { questions?: unknown })?.questions) ? (root["test"] as { questions: unknown[] }).questions : Array.isArray(root?.["questions"]) ? (root["questions"] as unknown[]) : null;
  if (list) {
    return finish(
      list.map((q, i) => {
        const o = q as Record<string, unknown>;
        return check(whole(o["question_no"] ?? o["no"] ?? o["n"] ?? o["q"] ?? o["question"]), whole(o["answer"] ?? o["correct_answer"] ?? o["key"] ?? o["correct"]), `item ${i + 1}`);
      }),
    );
  }
  if (root && typeof root === "object") {
    // { "1": 346, "2": 728 }
    return finish(Object.entries(root).map(([k, v]) => check(whole(k), whole(v), `"${k.slice(0, 20)}"`)));
  }
  throw new KeyFileError("expected a list of questions or a table of question numbers and answers");
}

function fromLines(text: string, csv: boolean): ParsedKey {
  const rows: [number, number][] = [];
  const lines = text.replace(/^\uFEFF/, "").split(/\r?\n/);
  lines.forEach((raw, i) => {
    const line = raw.trim();
    if (!line || line.startsWith("#")) return;
    const parts = csv ? line.split(/[,;\t]/).map((p) => p.trim().replace(/^"|"$/g, "")) : (/^\s*(\d{1,3})\s*[).:=,\- ]\s*(\d{1,4})\s*$/.exec(line)?.slice(1, 3) ?? []);
    if (parts.length < 2) throw new KeyFileError(`line ${i + 1} is not a question number and an answer`);
    const n = whole(parts[0]);
    const a = whole(parts[parts.length === 2 ? 1 : parts.length - 1]);
    if (i === 0 && csv && (n === null || a === null) && rows.length === 0) return; // a header row
    rows.push(check(n, a, `line ${i + 1}`));
  });
  return finish(rows);
}

/** Parse the text of an answer-key file. The kind is taken from the file name. */
export function parseKeyFile(name: string, text: string): ParsedKey {
  const lower = name.toLowerCase();
  if (lower.endsWith(".json")) return fromJson(text);
  if (lower.endsWith(".csv")) return fromLines(text, true);
  if (lower.endsWith(".txt")) return fromLines(text, false);
  throw new KeyFileError("use a .json, .csv or .txt file");
}

export function isKeyFile(name: string): boolean {
  return /\.(json|csv|txt)$/i.test(name);
}
