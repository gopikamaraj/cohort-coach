// The gated cohort chat client: types and calls. The server decides who may post, what is hidden, when the
// AI answers and who may correct; nothing here decides any of that. No name or id comes back, only labels.
import { API_BASE } from "./api";
import { deviceId } from "./consent";

export type ChatRole = "teacher" | "mentor" | "coach";
export type MessageKind = "question" | "reply" | "tip" | "ai_reply" | "correction" | "system";
export type QStatus = "waiting" | "answering" | "answered_human" | "answered_ai" | "corrected" | "resolved";

export interface ChatMessage {
  id: string;
  kind: MessageKind;
  author: string;
  role: string;
  text: string | null;
  hidden: boolean;
  created_at: string;
  reply_to: string | null;
  qstatus: QStatus | null;
  ai_due_at: string | null;
  after_seconds: number | null;
  ai_label: "ai" | "recorded" | null;
  sources: { id: string; title: string }[];
  corrected: boolean;
  corrects: string | null;
  abstained: boolean;
  demo: boolean;
  pinned: boolean;
  masked: string[];
}

export interface ChatThread {
  cohort: { id: string; error: string; status: string; teachers: number; mentors: number; coaches: number };
  me: string;
  role: ChatRole;
  timeout: { seconds: number; source: "cohort" | "env" | "demo" | "default" };
  ai_mode: string;
  state: "open" | "read_only";
  pinned: ChatMessage | null;
  messages: ChatMessage[];
  server_time: string;
}

export interface InboxItem {
  id: string;
  cohort_id: string;
  error: string;
  author: string;
  text: string | null;
  qstatus: QStatus;
  abstained: boolean;
  seconds_left: number | null;
  created_at: string;
}

export class ChatError extends Error {
  constructor(
    public status: number,
    public codes: string[] = [],
  ) {
    super(`chat ${status}`);
  }
}

async function call<T>(path: string, role: ChatRole, init: { method?: string; body?: unknown } = {}, fetchFn: typeof fetch = (...a) => fetch(...a)): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json", "X-Role": role };
  if (role === "teacher") headers["X-Device-Id"] = deviceId();
  let res: Response;
  try {
    res = await fetchFn(`${API_BASE}/api/cohort-chat${path}`, { method: init.method ?? "GET", headers, body: init.body === undefined ? undefined : JSON.stringify(init.body) });
  } catch {
    throw new ChatError(0);
  }
  if (!res.ok) {
    let codes: string[] = [];
    try {
      const j = (await res.json()) as { detail?: { codes?: string[] } };
      codes = j.detail?.codes ?? [];
    } catch {
      /* no body */
    }
    throw new ChatError(res.status, codes);
  }
  return (await res.json()) as T;
}

export const loadThread = (cohortId: string, role: ChatRole) => call<ChatThread>(`/${cohortId}`, role);
export const loadInbox = (role: ChatRole) => call<{ items: InboxItem[]; count: number; ai_mode: string }>("/inbox", role);
export const postMessage = (cohortId: string, role: ChatRole, kind: "question" | "reply" | "tip", text: string, language: string, replyTo?: string) =>
  call<{ id: string; text: string; hidden: string[] }>(`/${cohortId}/messages`, role, { method: "POST", body: { kind, text, language, reply_to: replyTo } });
export const resolveQuestion = (cohortId: string, role: ChatRole, id: string) => call<{ ok: boolean }>(`/${cohortId}/messages/${id}/resolve`, role, { method: "POST" });
export const correctAi = (cohortId: string, role: ChatRole, id: string, text: string, language: string) => call<{ id: string }>(`/${cohortId}/messages/${id}/correct`, role, { method: "POST", body: { text, language } });
export const moderate = (cohortId: string, role: ChatRole, id: string, action: "hide" | "restore" | "pin" | "unpin") => call<{ ok: boolean }>(`/${cohortId}/messages/${id}/moderate`, role, { method: "POST", body: { action } });
export const reportMessage = (cohortId: string, role: ChatRole, id: string) => call<{ ok: boolean }>(`/${cohortId}/messages/${id}/report`, role, { method: "POST" });
export const setTimeoutSeconds = (cohortId: string, role: ChatRole, seconds: number) => call<{ seconds: number }>(`/${cohortId}/timeout`, role, { method: "PUT", body: { seconds } });

/** Seconds left on a waiting question, by the server's clock (the phone's clock is never trusted). */
export function secondsLeft(dueAt: string | null, serverTime: string, fetchedAt: number, now: number = Date.now()): number | null {
  if (!dueAt) return null;
  const elapsed = (now - fetchedAt) / 1000;
  return Math.max(0, Math.ceil((Date.parse(dueAt) - Date.parse(serverTime)) / 1000 - elapsed));
}

/** Replies sit under their question, oldest first; everything else keeps the server's order. */
export function threaded(messages: ChatMessage[]): { message: ChatMessage; replies: ChatMessage[] }[] {
  const questions = new Set(messages.filter((m) => m.kind === "question").map((m) => m.id));
  const byQuestion = new Map<string, ChatMessage[]>();
  for (const m of messages) if (m.reply_to && questions.has(m.reply_to) && (m.kind === "reply" || m.kind === "ai_reply" || m.kind === "correction" || m.kind === "system")) byQuestion.set(m.reply_to, [...(byQuestion.get(m.reply_to) ?? []), m]);
  return messages.filter((m) => !(m.reply_to && byQuestion.has(m.reply_to) && m.kind !== "question")).map((m) => ({ message: m, replies: byQuestion.get(m.id) ?? [] }));
}
