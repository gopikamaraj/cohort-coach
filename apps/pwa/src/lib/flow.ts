// Client for the step API (/api/flow). It only fetches steps and posts answers: the flows, the
// words and every number come from the server, the same as in the Telegram bot.
import { API_BASE } from "./api";
import { deviceId } from "./consent";

export interface FlowButton {
  id: string;
  label: string;
}
export interface FlowMessage {
  step_id: string;
  kind: string;
  text: string;
  buttons: FlowButton[];
  url: string | null;
  url_label: string | null;
  audio: string | null;
}
export interface FlowTurn {
  lang: "en" | "hi" | "ta";
  consent: Record<string, unknown> | null;
  messages: FlowMessage[];
}

function headers(judge: boolean): Record<string, string> {
  const h: Record<string, string> = { "Content-Type": "application/json", "X-Device-Id": deviceId() };
  if (judge) h["X-Judge"] = "1";
  return h;
}

export async function currentTurn(judge: boolean, fetchFn: typeof fetch = (...a) => fetch(...a)): Promise<FlowTurn> {
  const res = await fetchFn(`${API_BASE}/api/flow/current`, { headers: headers(judge) });
  if (!res.ok) throw new Error(`flow ${res.status}`);
  return (await res.json()) as FlowTurn;
}

/** `key` makes a resend after a dropped connection harmless: the server ignores a key it has seen. */
export async function sendAnswer(
  stepId: string,
  value: string,
  key: string,
  fetchFn: typeof fetch = (...a) => fetch(...a),
): Promise<FlowTurn> {
  const res = await fetchFn(`${API_BASE}/api/flow/answer`, {
    method: "POST",
    headers: headers(false),
    body: JSON.stringify({ step_id: stepId, value, key }),
  });
  if (!res.ok) throw new Error(`flow ${res.status}`);
  return (await res.json()) as FlowTurn;
}

/** The server's consent choices, as the phone's local consent: only a server "yes" turns a scope on. */
export function consentFromServer(c: Record<string, unknown> | null): Record<string, boolean> | null {
  if (!c || c["core"] !== true) return null;
  const out: Record<string, boolean> = {};
  for (const s of ["core", "counts", "practice_ai", "share_rehearsal", "feedback"]) out[s] = c[s] === true;
  return out;
}
