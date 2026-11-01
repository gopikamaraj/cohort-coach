// "Try to break it": ask the server to run one prepared adversarial line through the real checks.
import { API_BASE } from "./api";

export interface BreakResult {
  kind: string;
  line: string;
  blocked: boolean;
  codes: string[];
  explanation: string;
  layer: string;
}

export async function tryBreak(
  kind: "injection" | "harsh" | "phone" | "child_name",
  language: string,
  fetchFn: typeof fetch = (...a) => fetch(...a),
): Promise<BreakResult> {
  const res = await fetchFn(`${API_BASE}/api/judge/try-break`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ kind, language }),
  });
  if (!res.ok) throw new Error(`break ${res.status}`);
  return (await res.json()) as BreakResult;
}

export async function fetchHints(sessionId: string, fetchFn: typeof fetch = (...a) => fetch(...a)): Promise<{ move: string; line: string }[]> {
  const res = await fetchFn(`${API_BASE}/api/practice/sessions/${sessionId}/hints`);
  if (!res.ok) return [];
  return ((await res.json()) as { hints: { move: string; line: string }[] }).hints;
}
