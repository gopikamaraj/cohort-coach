// The assistant's API calls. The server decides the scope from the signed-in role; this only asks
// and shows. "view_as" is sent only when the judge picks a role, and the server refuses it for
// anyone else. Nothing here ever sends or approves anything on the teacher's behalf.
import { API_BASE } from "./api";
import { deviceId } from "./consent";

export interface ScopeInfo {
  role: string;
  title: string;
  can: string;
  cannot: string;
  answers_from: string;
  commit: string | null;
  provisional: boolean;
  can_view_as: boolean;
  view_as_roles: string[];
}
export interface Question {
  id: string;
  text: string;
  criteria?: string[];
}
export interface Source {
  type: string;
  label: string;
  url?: string | null;
  quote?: string | null;
}
export interface Answer {
  answer: string;
  status_labels: { claim?: string; status: string }[];
  sources: Source[];
  how_to_check: string;
  limits: string;
  abstained: boolean;
  label: string | null;
  commit: string | null;
  provisional: boolean;
}
export interface PathStep {
  n: number;
  title: string;
  route: string;
  role: string;
  sample_input: string;
  questions: string[];
}
export interface TestPath {
  minutes?: number;
  credentials?: string;
  steps: PathStep[];
}

export interface Ctx {
  viewAs: string | null;
  surface: "main" | "about";
  lang: string;
}

function qs(c: Ctx, extra: Record<string, string> = {}): string {
  const p = new URLSearchParams({ surface: c.surface, lang: c.lang, ...extra });
  if (c.viewAs) p.set("view_as", c.viewAs);
  return p.toString();
}

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}/api/assistant${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", "X-Device-Id": deviceId(), ...(init?.headers ?? {}) },
  });
  if (!res.ok) throw new Error(`assistant ${res.status}`);
  return (await res.json()) as T;
}

export const getScope = (c: Ctx) => json<ScopeInfo>(`/scope?${qs(c)}`);
export const getQuestions = (c: Ctx, screen: string, step?: number) =>
  json<{ questions: Question[] }>(`/questions?${qs(c, { screen, ...(step ? { step: String(step) } : {}) })}`).then((r) => r.questions);
export const getAnswer = (c: Ctx, id: string) => json<Answer>(`/answer/${encodeURIComponent(id)}?${qs(c)}`);
export const askText = (c: Ctx, text: string) =>
  json<Answer>("/ask", { method: "POST", body: JSON.stringify({ text, lang: c.lang, view_as: c.viewAs, surface: c.surface }) });
export const getPath = () => json<TestPath>("/path");
