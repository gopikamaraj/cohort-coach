// Two classes to a cohort (#/two-classes?step=n): two teachers enter their checks, a cohort forms,
// the coach approves lesson 1, a teacher answers and gets her next lesson, the cohort chat, and the
// coach's Cohorts view with its timeline. Every step runs the product's own code on the server
// (services/cohort_run); this screen only shows steps and sends answers. "View as" switches who is
// acting; each person sees only what their role may see. Simulated, and labelled so.
import { useCallback, useEffect, useState } from "react";
import { Busy } from "../components/Busy";
import { RecordedChip, SimulatedBanner } from "../components/parts";
import type { Key } from "../i18n";
import { API_BASE } from "../lib/api";
import { useQuery } from "../lib/router";
import { useApp } from "../state";

type Who = "T1" | "T2" | "T3" | "C1" | "M1" | "M2" | "officer";
const WHO: Who[] = ["T1", "T2", "T3", "C1", "M1", "M2", "officer"];
const RUN_KEY = "cc.run.id";
const OUTBOX_KEY = "cc.run.outbox";

interface Reason { in?: boolean; code: string; showing: number; checked: number; single: number; ignored_single: number; min_checked?: number }
interface ClassRow { code: string; checked: number; track: string | null; errors: Record<string, Reason> }
interface Mentor { suggested: boolean; reason?: string; class?: string }
interface CohortBrief { id: string; error: string; labels: string[]; classes: number; teachers: number; mentor: Mentor }
interface Decision { day: number; mode: string; reason: string; skipped: string[]; answer?: string | null }
interface Source { kind: string; id: string; label: string; status: string }
interface LessonT {
  id: string; n: number; language: string; status: string; script: string | null; source: string; sources: Source[];
  decision: Decision | null; audio: { seconds: number } | null; voice_error: string | null; played: number; heard: boolean;
  feedback: { answer: string; note: string } | null; can_feedback: boolean; can_generate: boolean;
}
interface LessonC { id: string; n: number; language: string; for: string[]; status: string; source: string; decision: Decision | null; sources: Source[]; script: string }
interface Summary extends CohortBrief {
  showing: number; checked: number;
  lesson1: { by_language: { language: string; status: string }[]; plays: number; heard: number; feedback: Record<string, number>; no_answer: number; notes: { from: string; note: string }[] };
  lesson2: Record<string, number>;
  chat: { open: number; drafts_waiting: number; auto_sent: number; corrected: number };
}
interface Ev { seq: number; day: number; kind: string; link: string | null; facts: Record<string, unknown> }
interface Pending { id: string; from: string; body: string; draft: { text?: string; sources?: { title?: string; label?: string }[] } | null; seconds_left: number | null }
interface View {
  as: Who; simulated: boolean; clock: number; classes_in: string[]; expected: string[];
  settings: { min_classes: number; allow_single_item_probes: boolean };
  status?: string | null; waiting?: { have: number; min_classes: number }[];
  class?: ClassRow | null; cohort?: CohortBrief | null; lessons?: (LessonT | LessonC)[];
  cohorts?: Summary[]; timeline?: Ev[]; inbox?: { pending: Pending[]; needs_review: { id: string; answer: string }[] };
  totals?: { cohorts: number; classes: number | null; min_cell: number };
}
interface ChatQ { id: string; body: string; shared?: boolean; answers: { id: string; body: string; author_label: string; label: string | null }[] }
interface ChatView { questions: ChatQ[]; cohort_shared: { id: string; from: string; body: string; answers: ChatQ["answers"] }[]; wait_seconds: number }

class RunError extends Error {
  constructor(public status: number, public detail: unknown = null) {
    super(`run ${status}`);
  }
}

function store(): Storage | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function runId(): string {
  const s = store();
  const have = s?.getItem(RUN_KEY);
  if (have && /^run-[0-9a-f]{16}$/.test(have)) return have;
  const bytes = new Uint8Array(8);
  crypto.getRandomValues(bytes);
  const id = "run-" + Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  s?.setItem(RUN_KEY, id);
  return id;
}

async function call<T>(path: string, body?: unknown, method?: string): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/cohort-run${path}`, {
      method: method ?? (body === undefined ? "GET" : "POST"),
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new RunError(0);
  }
  if (!res.ok) {
    let detail: unknown = null;
    try {
      detail = ((await res.json()) as { detail?: unknown }).detail ?? null;
    } catch {
      /* no body */
    }
    throw new RunError(res.status, detail);
  }
  return (await res.json()) as T;
}

interface Queued { as: Who; text: string; share: boolean }
function outbox(): Queued[] {
  try {
    return JSON.parse(store()?.getItem(OUTBOX_KEY) ?? "[]") as Queued[];
  } catch {
    return [];
  }
}
function setOutbox(q: Queued[]): void {
  try {
    if (q.length) store()?.setItem(OUTBOX_KEY, JSON.stringify(q));
    else store()?.removeItem(OUTBOX_KEY);
  } catch {
    /* private window: the question stays in memory only */
  }
}

export default function TwoClasses() {
  const { tr } = useApp();
  const query = useQuery();
  const step = Math.min(5, Math.max(1, Number(query.get("step") ?? "1")));
  const [rid, setRid] = useState(runId);
  const [who, setWho] = useState<Who>((query.get("as") as Who) || "T1");
  const [view, setView] = useState<View | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const base = `/runs/${rid}`;

  const load = useCallback(async () => {
    try {
      await call(`/runs`, { run: rid });
      setView(await call<View>(`${base}?as=${who}`));
      setMsg("");
    } catch (e) {
      if (e instanceof RunError && e.status === 0) return; // offline: keep what is on screen
      setMsg(e instanceof RunError && e.status === 404 ? tr("run.judge_only") : tr("run.error"));
    }
  }, [rid, who, base, tr]);
  useEffect(() => {
    void load();
  }, [load]);

  async function act(path: string, body: unknown, after: Who = who) {
    setBusy(true);
    setMsg("");
    try {
      await call(path, body);
      setView(await call<View>(`${base}?as=${after}`));
    } catch (e) {
      setMsg(e instanceof RunError && typeof e.detail === "string" ? e.detail : tr("run.error"));
    } finally {
      setBusy(false);
    }
  }

  async function startAgain() {
    try {
      await call(`${base}`, undefined, "DELETE");
    } catch {
      /* already gone */
    }
    store()?.removeItem(RUN_KEY);
    setRid(runId());
  }

  return (
    <section className="stack" aria-labelledby="run-title" data-testid="two-classes">
      <h1 id="run-title">{tr("run.title")}</h1>
      {view?.simulated !== false ? <SimulatedBanner /> : null}
      <p>{tr("run.intro")}</p>
      <nav className="row wrap" aria-label={tr("run.title")}>
        {[1, 2, 3, 4, 5].map((n) => (
          <a key={n} className={`chip ${n === step ? "chip-on" : ""}`} aria-current={n === step ? "step" : undefined} href={`#/two-classes?step=${n}&as=${who}`} data-testid={`run-step-${n}`}>
            {tr(`run.step.${n}` as Key)}
          </a>
        ))}
      </nav>
      <label className="field">
        <span>{tr("run.view_as")}</span>
        <select value={who} onChange={(e) => setWho(e.target.value as Who)} data-testid="run-as">
          {WHO.map((w) => (
            <option key={w} value={w}>
              {tr(`run.who.${w}` as Key)}
            </option>
          ))}
        </select>
      </label>
      {busy ? <Busy text={tr("run.title")} testId="run-busy" /> : null}
      {msg ? (
        <p className="error" role="alert" data-testid="run-msg">
          {msg}
        </p>
      ) : null}
      {view && view.as === who ? (
        <>
          {step === 1 ? <Checks view={view} who={who} act={act} base={base} setWho={setWho} /> : null}
          {step === 2 || step === 3 ? <Lessons view={view} who={who} act={act} base={base} step={step} rid={rid} /> : null}
          {step === 4 ? <Chat view={view} who={who} base={base} refresh={load} /> : null}
          {step === 5 ? <Coach view={view} who={who} /> : null}
        </>
      ) : null}
      <button type="button" className="btn btn-secondary" onClick={() => void startAgain()} data-testid="run-reset">
        {tr("run.reset")}
      </button>
    </section>
  );
}

type Act = (path: string, body: unknown, after?: Who) => Promise<void>;

function Labels({ labels }: { labels: string[] }) {
  const { tr } = useApp();
  return (
    <p className="row wrap">
      {labels.map((l) => (
        <span key={l} className="badge" data-testid="run-label">
          {tr(`run.label.${l}` as Key)}
        </span>
      ))}
    </p>
  );
}

function MentorLine({ m }: { m: Mentor }) {
  const { tr } = useApp();
  return <p data-testid="run-mentor">{m.suggested ? tr("run.mentor.yes", { cls: m.class ?? "" }) : tr(`run.mentor.${m.reason}` as Key)}</p>;
}

function ReasonLine({ code, r }: { code: string; r: Reason }) {
  const { tr } = useApp();
  const main = tr(`run.reason.${r.code}` as Key, { n: r.showing, checked: r.checked, min: r.min_checked ?? 10 });
  return (
    <li data-testid={`run-reason-${code}`}>
      <strong>{tr(`err.${code}` as Key)}</strong>: {main}
      {r.single ? " " + tr("run.reason.single", { n: r.single }) : ""}
      {r.ignored_single ? " " + tr("run.reason.ignored_single", { n: r.ignored_single }) : ""}
    </li>
  );
}

function Checks({ view, who, act, base, setWho }: { view: View; who: Who; act: Act; base: string; setWho: (w: Who) => void }) {
  const { tr } = useApp();
  const teacherOf: Record<string, Who> = { "3A": "T1", "3B": "T2" };
  const s = view.settings;
  return (
    <div className="stack" data-testid="run-checks">
      <p className="muted" data-testid="run-settings">
        {tr("run.settings", { n: s.min_classes, single: tr(s.allow_single_item_probes ? "run.single.on" : "run.single.off") })}
      </p>
      {view.expected.map((code) => {
        const t = teacherOf[code] as Who;
        const done = view.classes_in.includes(code);
        return (
          <div key={code} className="card stack">
            <h2>{tr(`run.who.${t}` as Key)}</h2>
            {done ? (
              <p data-testid={`run-done-${code}`}>{tr("run.done", { cls: code })}</p>
            ) : (
              <>
                <button type="button" className="btn btn-primary" disabled={who !== t} onClick={() => void act(`${base}/classes/${code}/check`, { as: t })} data-testid={`run-submit-${code}`}>
                  {tr("run.submit", { cls: code })}
                </button>
                {who !== t ? (
                  <button type="button" className="btn btn-text" onClick={() => setWho(t)} data-testid={`run-become-${t}`}>
                    {tr("run.view_as")}: {tr(`run.who.${t}` as Key)}
                  </button>
                ) : null}
                <p className="muted">{tr("run.submit_note")}</p>
              </>
            )}
          </div>
        );
      })}
      {who === "C1" ? (
        <button type="button" className="btn btn-secondary" onClick={() => void act(`${base}/form`, {}, "C1")} data-testid="run-form-now">
          {tr("run.form_now")}
        </button>
      ) : null}
      <Status view={view} />
      {view.class ? (
        <div className="card stack" data-testid="run-your-class">
          <h2>{tr("run.your_class", { cls: view.class.code, n: view.class.checked })}</h2>
          <ul>
            {Object.entries(view.class.errors).map(([code, r]) => (
              <ReasonLine key={code} code={code} r={r} />
            ))}
          </ul>
        </div>
      ) : null}
      {view.cohort ? <CohortCard c={view.cohort} /> : null}
      {view.cohorts?.map((c) => <CohortCard key={c.id} c={c} />)}
    </div>
  );
}

function Status({ view }: { view: View }) {
  const { tr } = useApp();
  if (!view.status) return null;
  const w = view.waiting?.[0];
  return (
    <p role="status" data-testid="run-status" data-status={view.status}>
      {view.status === "waiting_for_classes" && w ? tr("run.status.waiting_for_classes", { have: w.have, need: w.min_classes }) : tr(`run.status.${view.status}` as Key)}
    </p>
  );
}

function CohortCard({ c }: { c: CohortBrief }) {
  const { tr } = useApp();
  return (
    <div className="card stack" data-testid="run-cohort">
      <p>
        <strong>{tr("run.cohort_line", { err: tr(`err.${c.error}` as Key), classes: c.classes, teachers: c.teachers })}</strong>
      </p>
      <Labels labels={c.labels} />
      <MentorLine m={c.mentor} />
    </div>
  );
}

function DecisionLine({ d }: { d: Decision }) {
  const { tr } = useApp();
  return (
    <p className="muted" data-testid="run-decision" data-mode={d.mode}>
      {tr(`run.next.${d.reason}` as Key)}
      {d.skipped.length ? " " + tr("run.next.skipped", { list: d.skipped.join(", ") }) : ""} {tr("run.next.who")}
    </p>
  );
}

function Lessons({ view, who, act, base, step, rid }: { view: View; who: Who; act: Act; base: string; step: number; rid: string }) {
  const { tr } = useApp();
  if (who === "C1") {
    const lessons = (view.lessons ?? []) as LessonC[];
    return (
      <div className="stack" data-testid="run-coach-lessons">
        {lessons.length === 0 ? <p>{tr("run.coach.none")}</p> : null}
        {lessons.map((x) => (
          <div key={x.id} className="card stack" data-testid={`run-cl-${x.id}`}>
            <h2>
              {tr("run.lesson.title", { n: x.n })} · {tr(`run.lang.${x.language}` as Key)} · {tr("run.for", { who: x.for.join(", ") })}
            </h2>
            <p data-testid="run-cl-status">{tr(`run.lesson.status.${x.status}` as Key)}</p>
            <p className="muted">
              {tr(`run.lesson.source.${x.source}` as Key)} {x.source === "ai" ? <RecordedChip /> : null}
            </p>
            {x.decision ? <DecisionLine d={x.decision} /> : null}
            <details>
              <summary>{tr("run.lesson.sources")}</summary>
              <ul>
                {x.sources.map((s) => (
                  <li key={s.id}>{s.label}</li>
                ))}
              </ul>
              <p className="pre-wrap">{x.script}</p>
            </details>
            {x.status === "in_review" ? (
              <div className="row wrap">
                <button type="button" className="btn btn-primary" onClick={() => void act(`${base}/lessons/${x.id}/decide`, { decision: "approve" })} data-testid={`run-approve-${x.id}`}>
                  {tr("run.approve")}
                </button>
                <button type="button" className="btn btn-secondary" onClick={() => void act(`${base}/lessons/${x.id}/decide`, { decision: "reject", reason: "tone_issue" })}>
                  {tr("run.reject")}
                </button>
              </div>
            ) : null}
          </div>
        ))}
        {step === 3 ? (
          <>
            {(["T1", "T2"] as Who[]).map((t) => (
              <button key={t} type="button" className="btn btn-secondary" onClick={() => void act(`${base}/next`, { as: "C1", teacher: t })} data-testid={`run-next-for-${t}`}>
                {tr("run.next.for", { who: tr(`run.who.${t}` as Key) })}
              </button>
            ))}
            <button type="button" className="btn btn-secondary" onClick={() => void act(`${base}/tick`, { days: 3 })} data-testid="run-tick">
              {tr("run.tick")}
            </button>
            <p className="muted">{tr("run.tick_note")}</p>
          </>
        ) : null}
        <a className="btn btn-text" href="#/review">
          {tr("run.coach.to_queue")}
        </a>
      </div>
    );
  }
  if (!who.startsWith("T")) return <Coach view={view} who={who} />;
  const lessons = (view.lessons ?? []) as LessonT[];
  const shown = step === 2 ? lessons.filter((x) => x.n === 1) : lessons;
  if (lessons.length === 0) return <p data-testid="run-no-lesson">{tr("run.lesson.none")}</p>;
  return (
    <div className="stack">
      {shown.map((x) => (
        <TeacherLesson key={x.id} x={x} who={who} act={act} base={base} rid={rid} step={step} />
      ))}
    </div>
  );
}

function TeacherLesson({ x, who, act, base, rid, step }: { x: LessonT; who: Who; act: Act; base: string; rid: string; step: number }) {
  const { tr } = useApp();
  const [note, setNote] = useState("");
  const audio = `${API_BASE}/api/cohort-run/runs/${rid}/lessons/${x.id}/audio?as=${who}`;
  return (
    <div className="card stack" data-testid={`run-lesson-${x.id}`}>
      <h2>
        {tr("run.lesson.title", { n: x.n })} · {tr(`run.lesson.status.${x.status}` as Key)}
      </h2>
      {x.decision ? <DecisionLine d={x.decision} /> : null}
      {x.status !== "released" ? <p data-testid="run-lesson-waiting">{tr("run.lesson.waiting")}</p> : null}
      {x.status === "released" ? (
        <>
          {x.audio ? (
            <>
              <audio controls preload="none" src={audio} onPlay={() => void act(`${base}/lessons/${x.id}/played`, { as: who })} data-testid="run-audio" />
              <p className="muted">{tr("run.lesson.seconds", { s: x.audio.seconds })}</p>
              <a className="btn btn-text" href={`${audio}&download=true`} download data-testid="run-download">
                {tr("run.lesson.download")}
              </a>
            </>
          ) : (
            <p data-testid="run-voice-failed">
              {tr("run.lesson.voice_failed")}
              <button type="button" className="btn btn-text" onClick={() => void act(`${base}/lessons/${x.id}/voice`, { as: who })} data-testid="run-voice-retry">
                {tr("run.lesson.retry")}
              </button>
            </p>
          )}
          <p className="muted">
            {tr(`run.lesson.source.${x.source}` as Key)} {x.source === "ai" ? <RecordedChip /> : null}
          </p>
          <p className="pre-wrap" lang={x.language} data-testid="run-script">
            {x.script}
          </p>
          <details>
            <summary>{tr("run.lesson.sources")}</summary>
            <ul>
              {x.sources.map((s) => (
                <li key={s.id}>{s.label}</li>
              ))}
            </ul>
          </details>
          {!x.played && !x.heard ? (
            <button type="button" className="btn btn-secondary" onClick={() => void act(`${base}/lessons/${x.id}/played`, { as: who, heard: true })} data-testid="run-heard">
              {tr("run.lesson.heard")}
            </button>
          ) : null}
        </>
      ) : null}
      {step === 3 && x.status === "released" ? (
        x.feedback ? (
          <p data-testid="run-fb-saved">{tr("run.fb.saved", { answer: tr(`run.fb.${x.feedback.answer}` as Key) })}</p>
        ) : x.can_feedback ? (
          <fieldset className="stack" data-testid="run-feedback">
            <legend>{tr("run.fb.title")}</legend>
            <label className="field">
              <span>{tr("run.fb.note")}</span>
              <textarea value={note} maxLength={300} rows={2} onChange={(e) => setNote(e.target.value)} data-testid="run-fb-note" />
            </label>
            <div className="row wrap">
              {(["tried", "partly", "not_yet"] as const).map((a) => (
                <button key={a} type="button" className="btn btn-secondary" onClick={() => void act(`${base}/lessons/${x.id}/feedback`, { as: who, answer: a, note })} data-testid={`run-fb-${a}`}>
                  {tr(`run.fb.${a}` as Key)}
                </button>
              ))}
            </div>
          </fieldset>
        ) : (
          <p className="muted">{tr("run.fb.play_first")}</p>
        )
      ) : null}
      {step === 3 && x.can_generate ? (
        <button type="button" className="btn btn-primary" onClick={() => void act(`${base}/next`, { as: who })} data-testid="run-next">
          {tr("run.next.button")}
        </button>
      ) : null}
    </div>
  );
}

function Chat({ view, who, base, refresh }: { view: View; who: Who; base: string; refresh: () => Promise<void> }) {
  const { tr } = useApp();
  const [chat, setChat] = useState<ChatView | null>(null);
  const [text, setText] = useState("");
  const [share, setShare] = useState(true);
  const [own, setOwn] = useState("");
  const [queued, setQueued] = useState(outbox().length);
  const [msg, setMsg] = useState("");

  const loadChat = useCallback(async () => {
    if (!who.startsWith("T")) return;
    try {
      setChat(await call<ChatView>(`${base}/chat?as=${who}`));
      setMsg("");
    } catch (e) {
      if (e instanceof RunError && e.status === 0) return; // offline: keep what is on screen
      setChat(null);
      setMsg(e instanceof RunError && e.status === 403 ? tr("run.chat.not_member") : e instanceof RunError && typeof e.detail === "string" ? e.detail : tr("run.error"));
    }
  }, [base, who, tr]);
  useEffect(() => {
    void loadChat();
  }, [loadChat]);

  const flush = useCallback(async () => {
    const q = outbox();
    const left: Queued[] = [];
    for (const item of q) {
      try {
        await call(`${base}/chat/ask`, item);
      } catch (e) {
        if (e instanceof RunError && e.status === 0) left.push(item);
      }
    }
    setOutbox(left);
    setQueued(left.length);
    await loadChat();
  }, [base, loadChat]);
  useEffect(() => {
    const on = () => void flush();
    window.addEventListener("online", on);
    return () => window.removeEventListener("online", on);
  }, [flush]);
  useEffect(() => {
    // the online event can come before requests work again: retry while anything waits
    if (!queued) return;
    const t = setInterval(() => {
      if (navigator.onLine) void flush();
    }, 3000);
    return () => clearInterval(t);
  }, [queued, flush]);

  async function ask() {
    const item: Queued = { as: who, text, share };
    if (!navigator.onLine) {
      setOutbox([...outbox(), item]);
      setQueued(outbox().length);
      setText("");
      return;
    }
    try {
      setChat(await call<ChatView>(`${base}/chat/ask`, item));
      setText("");
    } catch (e) {
      if (e instanceof RunError && e.status === 0) {
        setOutbox([...outbox(), item]);
        setQueued(outbox().length);
        setText("");
      } else setMsg(e instanceof RunError && typeof e.detail === "string" ? e.detail : tr("run.error"));
    }
  }

  async function coach(path: string, body: unknown) {
    try {
      await call(path, body);
      await refresh();
    } catch (e) {
      setMsg(e instanceof RunError && typeof e.detail === "string" ? e.detail : tr("run.error"));
    }
  }

  if (who === "C1") {
    const pending = view.inbox?.pending ?? [];
    return (
      <div className="stack" data-testid="run-inbox">
        <h2>{tr("run.chat.inbox")}</h2>
        {msg ? <p role="alert">{msg}</p> : null}
        {pending.length === 0 ? <p>{tr("run.chat.none")}</p> : null}
        {pending.map((q) => (
          <div key={q.id} className="card stack" data-testid="run-pending">
            <p>
              <strong>{q.from}</strong>: {q.body}
            </p>
            {q.draft ? (
              <>
                <p className="muted">{tr("run.chat.draft")}</p>
                <p>{q.draft.text}</p>
                <button type="button" className="btn btn-primary" onClick={() => void coach(`${base}/chat/${q.id}/reply`, { mode: "as_is" })} data-testid="run-send-draft">
                  {tr("run.chat.send_as_is")}
                </button>
              </>
            ) : (
              <p className="muted" data-testid="run-abstained">
                {tr("run.chat.abstained")}
              </p>
            )}
            <label className="field">
              <span>{tr("run.chat.own")}</span>
              <textarea value={own} rows={2} maxLength={1000} onChange={(e) => setOwn(e.target.value)} data-testid="run-own" />
            </label>
            <button type="button" className="btn btn-secondary" disabled={own.trim().length < 3} onClick={() => void coach(`${base}/chat/${q.id}/reply`, { mode: "own", text: own }).then(() => setOwn(""))} data-testid="run-send-own">
              {tr("run.chat.send_own")}
            </button>
          </div>
        ))}
        {pending.length ? (
          <button type="button" className="btn btn-secondary" onClick={() => void coach(`${base}/chat/skip`, {})} data-testid="run-skip">
            {tr("run.chat.skip")}
          </button>
        ) : null}
        {(view.inbox?.needs_review ?? []).map((a) => (
          <div key={a.id} className="card" data-testid="run-auto">
            <p className="muted">{tr("run.chat.auto_review")}</p>
            <p>{a.answer}</p>
          </div>
        ))}
        <p className="muted">{tr("run.chat.wait", { s: 60 })}</p>
      </div>
    );
  }
  if (!who.startsWith("T")) return <Coach view={view} who={who} />;
  return (
    <div className="stack" data-testid="run-chat">
      {msg ? (
        <p role="alert" data-testid="run-chat-msg">
          {msg}
        </p>
      ) : null}
      {chat ? (
        <>
          <label className="field">
            <span>{tr("run.chat.ask")}</span>
            <textarea value={text} rows={3} maxLength={500} onChange={(e) => setText(e.target.value)} data-testid="run-chat-text" />
          </label>
          <label className="row">
            <input type="checkbox" checked={share} onChange={(e) => setShare(e.target.checked)} data-testid="run-chat-share" /> {tr("run.chat.share")}
          </label>
          <button type="button" className="btn btn-primary" disabled={text.trim().length < 3} onClick={() => void ask()} data-testid="run-chat-send">
            {tr("run.chat.send")}
          </button>
          {queued ? (
            <p role="status" data-testid="run-chat-queued">
              {tr("run.chat.queued", { n: queued })}
            </p>
          ) : null}
          <p className="muted">{tr("run.chat.wait", { s: chat.wait_seconds })}</p>
          <h2>{tr("run.chat.mine")}</h2>
          {chat.questions.length === 0 ? <p>{tr("run.chat.none")}</p> : null}
          {chat.questions.map((q) => (
            <Thread key={q.id} from="" body={q.body} answers={q.answers} testid="run-mine" />
          ))}
          <h2>{tr("run.chat.shared")}</h2>
          {chat.cohort_shared.length === 0 ? <p>{tr("run.chat.none")}</p> : null}
          {chat.cohort_shared.map((q) => (
            <Thread key={q.id} from={q.from} body={q.body} answers={q.answers} testid="run-shared" />
          ))}
        </>
      ) : null}
    </div>
  );
}

function Thread({ from, body, answers, testid }: { from: string; body: string; answers: ChatQ["answers"]; testid: string }) {
  const { tr } = useApp();
  return (
    <div className="card stack" data-testid={testid}>
      <p>
        {from ? <strong>{from}: </strong> : null}
        {body}
      </p>
      {answers.map((a) => (
        <p key={a.id} className="answer">
          <strong>{a.author_label}</strong>
          {a.label ? ` (${tr(a.label as Key)})` : ""}: {a.body} {a.label?.startsWith("chat.label.a") ? <RecordedChip /> : null}
        </p>
      ))}
    </div>
  );
}

function Coach({ view, who }: { view: View; who: Who }) {
  const { tr } = useApp();
  if (who === "officer" && view.totals) {
    return (
      <p className="card" data-testid="run-officer">
        {tr("run.officer.totals", { n: view.totals.cohorts, min: view.totals.min_cell })}
      </p>
    );
  }
  if (who.startsWith("T")) return <Checks view={view} who={who} act={async () => undefined} base="" setWho={() => undefined} />;
  const cohorts = view.cohorts ?? [];
  if (who === "M2" || (who === "M1" && cohorts.length === 0 && view.status === undefined)) return <p data-testid="run-mentor-empty">{tr("run.mentor.empty")}</p>;
  return (
    <div className="stack" data-testid="run-coach">
      <h2>{tr("run.coach.title")}</h2>
      {cohorts.length === 0 ? <p>{tr("run.coach.none")}</p> : null}
      {cohorts.map((c) => (
        <div key={c.id} className="card stack" data-testid="run-coach-cohort">
          <p>
            <strong>{tr("run.cohort_line", { err: tr(`err.${c.error}` as Key), classes: c.classes, teachers: c.teachers })}</strong>
          </p>
          <Labels labels={c.labels} />
          <p>{tr("run.coach.children", { n: c.showing, checked: c.checked })}</p>
          <MentorLine m={c.mentor} />
          <h3>{tr("run.coach.l1")}</h3>
          <ul>
            {c.lesson1.by_language.map((l) => (
              <li key={l.language}>
                {tr(`run.lang.${l.language}` as Key)}: {tr(`run.lesson.status.${l.status}` as Key)}
              </li>
            ))}
          </ul>
          <p data-testid="run-coach-plays">{tr("run.coach.plays", { n: c.lesson1.plays })}</p>
          <p>{tr("run.coach.heard", { n: c.lesson1.heard })}</p>
          <p data-testid="run-coach-fb">{tr("run.coach.fb", { tried: c.lesson1.feedback.tried ?? 0, partly: c.lesson1.feedback.partly ?? 0, not_yet: c.lesson1.feedback.not_yet ?? 0 })}</p>
          <p>{tr("run.coach.no_answer", { n: c.lesson1.no_answer })}</p>
          {c.lesson1.notes.length ? (
            <details>
              <summary>{tr("run.coach.notes")}</summary>
              <ul>
                {c.lesson1.notes.map((n, i) => (
                  <li key={i}>
                    {n.from}: {n.note}
                  </li>
                ))}
              </ul>
            </details>
          ) : null}
          <p data-testid="run-coach-l2">
            {tr("run.coach.l2", {
              list:
                Object.entries(c.lesson2)
                  .map(([s, n]) => `${tr(`run.lesson.status.${s}` as Key)} ${n}`)
                  .join(", ") || "0",
            })}
          </p>
          <p data-testid="run-coach-chat">{tr("run.coach.chat", { open: c.chat.open, drafts: c.chat.drafts_waiting, auto: c.chat.auto_sent, corrected: c.chat.corrected })}</p>
          <p>{tr("run.coach.next_check")}</p>
          <div className="row wrap">
            <a className="btn btn-text" href="#/review">
              {tr("run.coach.to_queue")}
            </a>
            <a className="btn btn-text" href="#/two-classes?step=4&as=C1">
              {tr("run.coach.to_chat")}
            </a>
          </div>
        </div>
      ))}
      {view.timeline?.length ? (
        <details open data-testid="run-timeline">
          <summary>{tr("run.coach.timeline")}</summary>
          <ol>
            {view.timeline.map((e) => (
              <li key={e.seq}>
                {tr("run.coach.day", { d: e.day })}: {tr(`run.ev.${e.kind}` as Key, Object.fromEntries(Object.entries(e.facts).map(([k, v]) => [k, Array.isArray(v) ? v.join(", ") : String(v)])))}
              </li>
            ))}
          </ol>
        </details>
      ) : null}
    </div>
  );
}
