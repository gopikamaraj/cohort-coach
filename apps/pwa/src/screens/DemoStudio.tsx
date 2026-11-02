// Demo Studio: the judge's guided path through the product on a made-up class (#/demo?step=n).
// Each step drives the product's own code on the server: Paper Studio, the sheet reader, the error
// finder on the phone, cohort formation, the track drafter and voice, the cohort chat, the coach's
// queues and the officer's view. Every made-up number on these screens carries a Demo or Simulated
// label. Steps 2 and 9 open the product's own screens (Start a check, Practice Class).
import { useCallback, useEffect, useState } from "react";
import { BeforeAfter } from "../components/BeforeAfter";
import { Busy } from "../components/Busy";
import { DemoEntry, PilotBanner } from "../components/DemoEntry";
import { AiOffNote, RecordedChip, SimulatedBanner } from "../components/parts";
import type { Key } from "../i18n";
import { API_BASE } from "../lib/api";
import { db, newClassId, setSetting } from "../lib/db";
import { DemoError, dcall, demoBlob, demoSession, demoSource, saveReads, setDemoStep, startDemo, type DemoSummary, type ReadsFile } from "../lib/demoStudio";
import { useQuery } from "../lib/router";
import { track } from "../lib/tester";
import { fetchPaperKey } from "../lib/paperKeys";
import { useApp } from "../state";

interface Cohort {
  id: string;
  error: string;
  classes: number;
  simulated_classes: number;
  undersized: boolean;
  includes_you: boolean;
  you_eligible: boolean;
  you_next_term: boolean;
  mentor: { class: string; showing: number; checked: number; kind: string } | null;
}

interface Plan {
  simulated: boolean;
  other_classes: number;
  schools: number;
  cohorts: Cohort[];
  you: { checked: number; counts: Record<string, number>; eligible: string[]; track: string | null; arm: string | null; reason: string | null };
}

function useDemo() {
  const [summary, setSummary] = useState<DemoSummary | null>(null);
  const [error, setError] = useState("");
  const refresh = useCallback(async () => {
    try {
      setSummary(await startDemo());
    } catch (e) {
      setError(e instanceof DemoError && e.status === 404 ? "demo.judge_only" : "demo.error");
    }
  }, []);
  useEffect(() => {
    void refresh();
  }, [refresh]);
  return { summary, error, refresh };
}

export default function DemoStudio() {
  const { tr } = useApp();
  const query = useQuery();
  const step = Number(query.get("step") ?? "1");
  const { summary, error, refresh } = useDemo();

  useEffect(() => {
    if (step >= 1 && step <= 12) {
      setDemoStep(step);
      track("feature_used", { feature_id: `demo_step_${step}` });
    }
  }, [step]);

  if (error) return <p role="alert">{tr(error as "demo.error")}</p>;
  if (!summary) return <p role="status">{tr("demo.working")}</p>;
  return (
    <section className="stack" aria-labelledby="demo-title" data-testid="demo-studio">
      <h1 id="demo-title">{tr("demo.title")}</h1>
      <p className="chip" data-testid="demo-label">
        {tr("demo.label.class", { code: summary.class_code })}
      </p>
      {step >= 6 && demoSource() === "pilot" ? <PilotBanner /> : null}
      {step === 1 ? <StepStart summary={summary} onSeed={refresh} /> : null}
      {step === 3 ? <StepSheets summary={summary} /> : null}
      {step === 4 || step === 5 ? <DemoEntry strength={summary.strength} classCode={summary.class_code} onFinished={() => (window.location.hash = "#/demo?step=6")} /> : null}
      {step === 6 ? <StepSimulate /> : null}
      {step === 7 ? <StepCohorts /> : null}
      {step === 8 ? <StepAudio /> : null}
      {step === 10 ? <StepChat /> : null}
      {step === 11 ? <StepCoach /> : null}
      {step === 12 ? <StepPost /> : null}
    </section>
  );
}

// --- step 1 ----------------------------------------------------------------------------------

function StepStart({ summary, onSeed }: { summary: DemoSummary; onSeed: () => Promise<void> }) {
  const { tr, setRole, setLang, reload, klass } = useApp();
  const [ready, setReady] = useState(klass?.name === "Class 3A (demo)");

  async function begin() {
    setRole("teacher");
    setLang("en");
    if (klass?.name !== "Class 3A (demo)") {
      const id = newClassId(true);
      await db.classes.put({ id, name: `Class ${summary.class_code} (demo)`, simulated: true, createdAt: Date.now() });
      await setSetting("activeClass", id);
      await reload();
    }
    setReady(true);
    window.location.hash = "#/papers";
    setDemoStep(2);
  }

  return (
    <div className="stack" data-testid="demo-step-1">
      <h2>{tr("demo.s1.title")}</h2>
      <p>{tr("demo.s1.body", { n: summary.strength, code: summary.class_code })}</p>
      <ul>
        <li>{tr("demo.s1.point_ai")}</li>
        <li>{tr("demo.s1.point_labels")}</li>
        <li>{tr("demo.s1.point_reset")}</li>
      </ul>
      <button type="button" className="btn btn-primary" onClick={() => void begin()} data-testid="demo-begin">
        {ready ? tr("demo.s1.continue") : tr("demo.s1.begin")}
      </button>
      <button
        type="button"
        className="btn btn-secondary"
        onClick={() =>
          void startDemo(summary.seed + 1)
            .then(onSeed)
            .catch(() => undefined)
        }
        data-testid="demo-regenerate"
      >
        {tr("demo.s1.regenerate", { seed: summary.seed })}
      </button>
    </div>
  );
}

// --- step 3 ----------------------------------------------------------------------------------

function download(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function StepSheets({ summary }: { summary: DemoSummary }) {
  const { tr } = useApp();
  const sid = demoSession();
  const paperId = localStorage.getItem("cc.demo.paper");
  const [sheets, setSheets] = useState<{ name: string; roll: number }[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  async function make() {
    if (!sid || !paperId) return;
    setBusy(true);
    setMsg("");
    try {
      const out = await dcall<{ sheets: { name: string; roll: number }[] }>(`/${sid}/sheets`, { body: { paper_id: paperId } });
      saveReads(await dcall<ReadsFile>(`/${sid}/reads.json`));
      setSheets(out.sheets);
    } catch (e) {
      setMsg(e instanceof DemoError && e.message ? e.message : tr("demo.error"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack" data-testid="demo-step-3">
      <h2>{tr("demo.s3.title")}</h2>
      <p>{tr("demo.s3.body", { n: summary.strength })}</p>
      {!paperId ? <p role="status">{tr("demo.s3.need_paper")}</p> : null}
      <button type="button" className="btn btn-primary" disabled={busy || !paperId} onClick={() => void make()} data-testid="demo-make-sheets">
        {busy ? tr("demo.s3.making", { n: summary.strength }) : tr("demo.s3.make", { n: summary.strength })}
      </button>
      {busy ? <Busy text={tr("demo.busy.sheets", { n: summary.strength })} testId="demo-busy" /> : null}
      {msg ? <p role="alert">{msg}</p> : null}
      {sheets ? (
        <>
          <p className="chip" data-testid="demo-sheets-label">
            {tr("demo.label.sheets")}
          </p>
          <div className="row">
            <button type="button" className="btn btn-secondary" onClick={() => void demoBlob(`/${sid}/sheets.zip`).then((b) => download(b, `${summary.class_code}-demo-sheets.zip`))} data-testid="demo-zip">
              {tr("demo.s3.zip")}
            </button>
            <a className="btn btn-secondary" href={`${API_BASE}/api/demo/${sid}/reads.json`} download="reads.json" data-testid="demo-reads">
              {tr("demo.s3.reads")}
            </a>
          </div>
          <ul className="plain demo-sheet-list" data-testid="demo-sheet-list">
            {sheets.map((s) => (
              <li key={s.name}>
                <button type="button" className="chip-btn" onClick={() => void demoBlob(`/${sid}/sheets/${s.name}`).then((b) => download(b, s.name))}>
                  {s.name}
                </button>
              </li>
            ))}
          </ul>
          <a className="btn btn-primary" href="#/demo?step=4" data-testid="demo-to-4">
            {tr("demo.next_step", { n: 4 })}
          </a>
        </>
      ) : null}
    </div>
  );
}

// --- steps 6 and 7 ------------------------------------------------------------------------------

function StepSimulate() {
  const { tr, profile } = useApp();
  const sid = demoSession();
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [summary, setSummary] = useState<{ sheets_read_by_ai: number; boxes: number; boxes_read_correctly: number; note: string } | null>(null);

  useEffect(() => {
    if (sid) void dcall<typeof summary>(`/${sid}/reading-summary`).then(setSummary).catch(() => undefined);
  }, [sid]);

  async function simulate() {
    if (!sid || !profile) return;
    setBusy(true);
    try {
      await dcall(`/${sid}/simulate-classes`, { body: { counts: profile.counts, checked: profile.childrenChecked } });
      window.location.hash = "#/demo?step=7";
    } catch {
      setMsg(tr("demo.error"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack" data-testid="demo-step-6">
      <h2>{tr("demo.s6.title")}</h2>
      {profile ? (
        <>
          <SimulatedBanner />
          <p data-testid="demo-my-counts">
            {tr("demo.s6.mine", { n: profile.childrenChecked })}{" "}
            {Object.entries(profile.counts)
              .filter(([, v]) => v > 0)
              .map(([k, v]) => tr("demo.s6.count", { code: k, n: v, total: profile.childrenChecked }))
              .join(" · ")}
          </p>
          <a className="btn btn-secondary" href="#/cards">
            {tr("demo.s6.cards")}
          </a>
        </>
      ) : (
        <p role="status">{tr("demo.s6.no_check")}</p>
      )}
      {summary && summary.sheets_read_by_ai > 0 ? (
        <div className="card" data-testid="demo-reading-summary">
          <h3>{tr("demo.s6.summary_title")}</h3>
          <p className="chip">{tr("demo.label.synthetic")}</p>
          <p>{tr("demo.s6.summary", { right: summary.boxes_read_correctly, boxes: summary.boxes, sheets: summary.sheets_read_by_ai })}</p>
          <p className="muted">{summary.note}</p>
        </div>
      ) : null}
      <a className="btn btn-secondary" href="#/demo?step=4" onClick={() => setDemoStep(4)} data-testid="demo-reopen">
        {tr("demo.s6.reopen")}
      </a>
      <button type="button" className="btn btn-primary" disabled={busy || !profile} onClick={() => void simulate()} data-testid="demo-simulate">
        {tr("demo.s6.simulate")}
      </button>
      {busy ? <Busy text={tr("demo.busy.simulate")} testId="demo-busy" /> : null}
      {msg ? <p role="alert">{msg}</p> : null}
    </div>
  );
}

function CohortCards({ plan }: { plan: Plan }) {
  const { tr } = useApp();
  return (
    <ul className="plain stack" data-testid="demo-cohorts">
      {plan.cohorts.map((c) => (
        <li key={c.id} className={c.includes_you ? "card card-focus" : "card"} data-testid={`demo-cohort-${c.error}`}>
          <h3>{tr("demo.cohort.title", { code: c.error })}</h3>
          <p>
            <span className="chip">{tr("demo.label.simulated")}</span> {tr("demo.cohort.members", { n: c.classes })}
            {c.undersized ? ` · ${tr("demo.cohort.small")}` : ""}
          </p>
          <p data-testid={`demo-cohort-you-${c.error}`}>
            {c.includes_you ? tr("demo.cohort.you_in", { code: c.error }) : c.you_next_term ? tr("demo.cohort.you_next", { code: c.error }) : tr("demo.cohort.you_not")}
          </p>
          <p className="muted">{tr("demo.cohort.rule", { code: c.error })}</p>
          <p>{c.mentor ? tr("demo.cohort.mentor", { cls: c.mentor.class, n: c.mentor.showing, total: c.mentor.checked }) : tr("demo.cohort.no_mentor")}</p>
        </li>
      ))}
    </ul>
  );
}

function StepCohorts() {
  const { tr } = useApp();
  const sid = demoSession();
  const [plan, setPlan] = useState<Plan | null>(null);
  const [msg, setMsg] = useState("");
  useEffect(() => {
    if (sid)
      void dcall<Plan>(`/${sid}/cohorts`)
        .then(setPlan)
        .catch((e) => setMsg(e instanceof DemoError && e.message ? e.message : tr("demo.error")));
  }, [sid, tr]);
  return (
    <div className="stack" data-testid="demo-step-7">
      <h2>{tr("demo.s7.title")}</h2>
      {msg ? <p role="alert">{msg}</p> : null}
      {!plan && !msg ? <Busy text={tr("demo.busy.cohorts")} testId="demo-busy" /> : null}
      {plan ? (
        <>
          <p>{tr("demo.s7.body", { classes: plan.other_classes, schools: plan.schools, n: plan.cohorts.length })}</p>
          <p data-testid="demo-your-track">{plan.you.track ? tr("demo.s7.track", { code: plan.you.track, eligible: plan.you.eligible.length }) : tr("demo.s7.no_track")}</p>
          {(() => {
            // her class's cohorts: one this term (one track a term) and any it joins next term
            const now = plan.cohorts.filter((c) => c.includes_you);
            const later = plan.cohorts.filter((c) => !c.includes_you && c.you_next_term);
            const n = now.length + later.length;
            return n > 1 && now[0] ? (
              <p className="card" data-testid="demo-in-two">
                {tr("demo.s7.in_cohorts", { n, total: plan.cohorts.length, now: now[0].error, later: later.map((c) => c.error).join(", ") })}
              </p>
            ) : null;
          })()}
          <CohortCards plan={plan} />
          <a className="btn btn-primary" href="#/demo?step=8" onClick={() => setDemoStep(8)} data-testid="demo-to-8">
            {tr("demo.next_step", { n: 8 })}
          </a>
        </>
      ) : null}
    </div>
  );
}

/** A queue status code (awaiting_coach, pending, approved...) as words; never the raw code. */
function statusWords(tr: (k: Key) => string, status: string | null): string {
  return status ? tr(`item.st.${status}` as Key) : "";
}

/** The server's badge for a pre-approved demo lesson, in the screen's language. */
const BADGES: Record<string, Key> = { "Demo: pre-approved": "demo.s8.badge_preapproved" as Key };

// --- step 8 -----------------------------------------------------------------------------------

interface AudioOut {
  script: string;
  source: "ai" | "template";
  badge: string;
  error: string;
  audio_url: string | null;
}

function StepAudio() {
  const { tr } = useApp();
  const sid = demoSession();
  const [out, setOut] = useState<AudioOut | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  async function make(regenerate = false) {
    if (!sid) return;
    setBusy(true);
    setMsg("");
    try {
      setOut(await dcall<AudioOut>(`/${sid}/audio`, { body: { regenerate } }));
    } catch (e) {
      setMsg(e instanceof DemoError && e.message ? e.message : tr("demo.error"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack" data-testid="demo-step-8">
      <h2>{tr("demo.s8.title")}</h2>
      <p>{tr("demo.s8.body")}</p>
      <AiOffNote text={tr("ai.off.lesson")} testId="demo-audio-ai-off" />
      <button type="button" className="btn btn-primary" disabled={busy} onClick={() => void make()} data-testid="demo-audio">
        {busy ? tr("demo.working") : tr("demo.s8.make")}
      </button>
      {busy ? <Busy text={tr("demo.busy.audio")} testId="demo-busy" /> : null}
      {msg ? <p role="alert">{msg}</p> : null}
      {out ? (
        <article className="card stack" data-testid="demo-audio-card">
          <p>
            <span className="chip" data-testid="demo-audio-badge">
              {BADGES[out.badge] ? tr(BADGES[out.badge]!) : out.badge}
            </span>{" "}
            <span className="chip">{out.source === "ai" ? tr("demo.s8.by_ai") : tr("demo.s8.by_template")}</span>{" "}
            {out.source === "ai" ? <RecordedChip testId="demo-audio-recorded" /> : null}
          </p>
          {out.audio_url ? (
            <>
              <audio controls src={`${API_BASE}${out.audio_url}`} data-testid="demo-audio-player" />
              <a className="btn btn-secondary" href={`${API_BASE}${out.audio_url}`} download="lesson-1-audio" data-testid="demo-audio-download">
                {tr("demo.s8.download")}
              </a>
            </>
          ) : (
            <p className="muted">{tr("demo.s8.text_only")}</p>
          )}
          <div className="demo-script" data-testid="demo-audio-script">
            {out.script.split(/\n+/).map((p, i) => (
              <p key={i}>{p}</p>
            ))}
          </div>
          <div className="row">
            <a className="btn btn-primary" href="#/practice?next=ask_explain" onClick={() => setDemoStep(9)} data-testid="demo-to-practice">
              {tr("demo.s8.practice")}
            </a>
            <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => void make(true)} data-testid="demo-audio-regenerate">
              {tr("demo.s8.regenerate")}
            </button>
          </div>
        </article>
      ) : null}
    </div>
  );
}

// --- step 10 ----------------------------------------------------------------------------------

interface ChatAnswer {
  id: string;
  body: string;
  author_role?: string;
  author_label?: string;
  label?: string | null; // a string key (chat.label.*)
  status?: string;
  sources?: { title?: string; label?: string }[];
}
interface ChatQ {
  id: string;
  body: string;
  status: string;
  waiting: { key: string; params: Record<string, string> };
  ai_due_at: string | null;
  answers: ChatAnswer[];
}

function StepChat() {
  const { tr } = useApp();
  const sid = demoSession();
  const [view, setView] = useState<{ questions: ChatQ[]; wait_seconds: number } | null>(null);
  const [busyText, setBusyText] = useState("");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [now, setNow] = useState(Date.now());
  const [msg, setMsg] = useState("");

  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  useEffect(() => {
    if (sid)
      void dcall<typeof view>(`/${sid}/chat`)
        .then(setView)
        .catch((e) => setMsg(e instanceof DemoError && e.message ? e.message : tr("demo.error")));
  }, [sid, tr]);

  async function act(path: string, body?: unknown) {
    setBusy(true);
    setBusyText(path.endsWith("/skip") ? "demo.busy.skip" : "demo.busy.ask");
    setMsg("");
    try {
      setView(await dcall(path, { method: "POST", body }));
    } catch (e) {
      setMsg(e instanceof DemoError && e.message ? e.message : tr("demo.error"));
    } finally {
      setBusy(false);
    }
  }

  const pending = view?.questions.find((q) => q.ai_due_at && q.answers.length === 0);
  const left = pending?.ai_due_at ? Math.max(0, Math.round((Date.parse(pending.ai_due_at) - now) / 1000)) : null;
  useEffect(() => {
    if (left === 0 && pending && !busy) void act(`/${sid}/chat/skip`);
  }, [left === 0]);

  return (
    <div className="stack" data-testid="demo-step-10">
      <h2>{tr("demo.s10.title")}</h2>
      <p>{tr("demo.s10.body")}</p>
      <AiOffNote text={tr("ai.off.chat")} testId="demo-chat-ai-off" />
      <label className="field">
        <span>{tr("demo.s10.ask_label")}</span>
        <textarea value={text} maxLength={500} rows={3} onChange={(e) => setText(e.target.value)} data-testid="demo-chat-text" />
      </label>
      <button type="button" className="btn btn-primary" disabled={busy || text.trim().length < 3} onClick={() => void act(`/${sid}/chat/ask`, { text }).then(() => setText(""))} data-testid="demo-chat-ask">
        {tr("demo.s10.ask")}
      </button>
      {left !== null ? (
        <div className="card row" data-testid="demo-chat-wait">
          <p role="status">{tr("demo.s10.wait", { s: left })}</p>
          <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => void act(`/${sid}/chat/skip`)} data-testid="demo-chat-skip">
            {tr("demo.s10.skip")}
          </button>
        </div>
      ) : null}
      {busy ? <Busy ai text={tr(busyText as "demo.busy.ask")} testId="demo-busy" /> : null}
      {msg ? <p role="alert">{msg}</p> : null}
      <ul className="plain stack" data-testid="demo-chat-thread">
        {(view?.questions ?? []).map((q) => (
          <li key={q.id} className="card stack">
            <p>
              <strong>{tr("demo.s10.you")}</strong> {q.body}
            </p>
            {q.answers.length === 0 ? (
              <p className="muted" data-testid="demo-chat-waiting">
                {tr(q.waiting.key as Key, q.waiting.params.time ? { time: new Date(q.waiting.params.time).toLocaleTimeString() } : {})}
              </p>
            ) : null}
            {q.answers.map((a) => (
              <div key={a.id} data-testid="demo-chat-answer">
                <p>
                  <span className="chip">{a.label ? tr(a.label as Key) : (a.author_label ?? "")}</span> {a.author_role === "ai" ? <RecordedChip /> : null}
                </p>
                <p>{a.body}</p>
              </div>
            ))}
          </li>
        ))}
      </ul>
    </div>
  );
}

// --- step 11 ----------------------------------------------------------------------------------

interface CoachView {
  cohorts: Cohort[];
  chat: { questions: { id: string; body: string; draft: { text?: string } | null }[]; ai_answers: { id: string; question: string | null; answer: string }[] };
  mentor_card: { mentor_label: string; card: { title: string; steps: string[]; phrase: string }; item_id: string | null; status: string | null };
  lesson2: { item_id: string | null; status: string | null; note: string | null };
}

interface Dashboard {
  classes: number;
  cohorts: { error: string; classes: number | null }[];
  by_error: { error: string; classes: number | null; share: number | null }[];
  tracks_started: number | null;
  waiting_next_term: number | null;
  approvals_pending: number;
  before_after: { error: string; classes: number | null; before: number | null; after: number | null; checked_before: number | null; checked_after: number | null }[] | null;
}

function StepCoach() {
  const { tr, setRole } = useApp();
  const sid = demoSession();
  const [tab, setTab] = useState<"coach" | "officer">("coach");
  const [view, setView] = useState<CoachView | null>(null);
  const [dash, setDash] = useState<Dashboard | null>(null);
  const [reason, setReason] = useState("");
  const [own, setOwn] = useState("");
  const [msg, setMsg] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!sid) return;
    void dcall<CoachView>(`/${sid}/coach/seed`, { method: "POST" })
      .then(setView)
      .catch((e) => setMsg(e instanceof DemoError && e.message ? e.message : tr("demo.error")));
  }, [sid, tr]);
  useEffect(() => {
    if (sid && tab === "officer") void dcall<Dashboard>(`/${sid}/dashboard`).then(setDash).catch(() => setMsg(tr("demo.error")));
  }, [sid, tab, tr]);

  async function act(path: string, body: unknown) {
    setMsg("");
    setSaving(true);
    try {
      setView(await dcall<CoachView>(path, { method: "POST", body }));
      setMsg(tr("demo.s11.done"));
    } catch (e) {
      setMsg(e instanceof DemoError && e.message ? e.message : tr("demo.error"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="stack" data-testid="demo-step-11">
      <h2>{tr("demo.s11.title")}</h2>
      <div className="chips" role="tablist">
        <button type="button" role="tab" aria-selected={tab === "coach"} className={tab === "coach" ? "chip-btn chip-on" : "chip-btn"} onClick={() => (setTab("coach"), setRole("coach"))} data-testid="demo-tab-coach">
          {tr("role.coach")}
        </button>
        <button type="button" role="tab" aria-selected={tab === "officer"} className={tab === "officer" ? "chip-btn chip-on" : "chip-btn"} onClick={() => (setTab("officer"), setRole("officer"))} data-testid="demo-tab-officer">
          {tr("demo.s11.officer")}
        </button>
      </div>
      {saving ? <Busy text={tr("demo.busy.saving")} testId="demo-busy" /> : null}
      {msg ? <p role="status">{msg}</p> : null}
      {tab === "coach" && !view && !msg ? <Busy text={tr("demo.busy.coach")} testId="demo-busy" /> : null}
      {tab === "officer" && !dash && !msg ? <Busy text={tr("demo.busy.dashboard")} testId="demo-busy" /> : null}
      {tab === "coach" && view ? (
        <div className="stack" data-testid="demo-coach">
          <h3>{tr("demo.s11.cohorts")}</h3>
          <CohortCards plan={{ cohorts: view.cohorts } as Plan} />
          <h3>{tr("demo.s11.queue")}</h3>
          <article className="card stack" data-testid="demo-q-chat">
            <h4>{tr("demo.s11.chat")}</h4>
            {view.chat.questions.length === 0 && view.chat.ai_answers.length === 0 ? <p className="muted">{tr("demo.s11.chat_none")}</p> : null}
            {view.chat.questions.map((q) => (
              <div key={q.id} className="stack">
                <p>{q.body}</p>
                {q.draft?.text ? (
                  <p className="muted">
                    {tr("demo.s11.draft", { text: q.draft.text })} <RecordedChip />
                  </p>
                ) : null}
                {q.draft?.text ? (
                  <button type="button" className="btn btn-secondary" onClick={() => void act(`/${sid}/coach/questions/${q.id}/reply`, { mode: "as_is" })} data-testid="demo-q-send">
                    {tr("demo.s11.send_draft")}
                  </button>
                ) : (
                  <p className="muted" data-testid="demo-q-no-draft">
                    {tr("demo.s11.no_draft")}
                  </p>
                )}
                <label className="field">
                  <span>{tr("demo.s11.own_label")}</span>
                  <textarea rows={3} maxLength={1000} value={own} onChange={(e) => setOwn(e.target.value)} data-testid="demo-q-own" />
                </label>
                <button type="button" className="btn btn-primary" disabled={own.trim().length < 3} onClick={() => void act(`/${sid}/coach/questions/${q.id}/reply`, { mode: "own", text: own }).then(() => setOwn(""))} data-testid="demo-q-own-send">
                  {tr("demo.s11.own_send")}
                </button>
              </div>
            ))}
            {view.chat.ai_answers.map((a) => (
              <div key={a.id} className="stack">
                <p>
                  <span className="chip">{tr("demo.s10.ai_label")}</span> <RecordedChip /> {a.answer}
                </p>
                <button type="button" className="btn btn-secondary" onClick={() => void act(`/${sid}/coach/answers/${a.id}/correct`, { text: tr("demo.s11.correction"), tags: ["not_practical"] })} data-testid="demo-q-correct">
                  {tr("demo.s11.correct")}
                </button>
              </div>
            ))}
          </article>
          <article className="card stack" data-testid="demo-q-mentor">
            <h4>{tr("demo.s11.mentor_card")}</h4>
            <p>
              <span className="chip">{view.mentor_card.mentor_label}</span> <span className="chip" data-testid="demo-mentor-status">{statusWords(tr, view.mentor_card.status)}</span>
            </p>
            <p className="muted" data-testid="demo-mentor-planned">
              {tr("demo.s11.mentor_planned")}
            </p>
            <p>
              <strong>{view.mentor_card.card.title}</strong>
            </p>
            <ol>
              {view.mentor_card.card.steps.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ol>
            <div className="row">
              <button type="button" className="btn btn-primary" disabled={view.mentor_card.status !== "awaiting_coach"} onClick={() => void act(`/${sid}/coach/mentor-card`, { decision: "approve" })} data-testid="demo-mentor-approve">
                {tr("papers.approve")}
              </button>
              <button type="button" className="btn btn-secondary" disabled={view.mentor_card.status !== "awaiting_coach"} onClick={() => void act(`/${sid}/coach/mentor-card`, { decision: "reject", reason: "missing_step", note: reason })}>
                {tr("papers.reject")}
              </button>
            </div>
          </article>
          <article className="card stack" data-testid="demo-q-lesson2">
            <h4>{tr("demo.s11.lesson2")}</h4>
            {view.lesson2.item_id ? (
              <>
                <p>
                  <span className="chip">{tr("demo.s11.ai_draft")}</span> <RecordedChip /> <span className="chip" data-testid="demo-lesson2-status">{statusWords(tr, view.lesson2.status)}</span>
                </p>
                <a className="btn btn-secondary" href="#/review">
                  {tr("demo.s11.open_review")}
                </a>
                <div className="row">
                  <button type="button" className="btn btn-primary" disabled={view.lesson2.status !== "pending"} onClick={() => void act(`/${sid}/coach/lesson2`, { decision: "approve" })} data-testid="demo-lesson2-approve">
                    {tr("papers.approve")}
                  </button>
                  <button type="button" className="btn btn-secondary" disabled={view.lesson2.status !== "pending"} onClick={() => void act(`/${sid}/coach/lesson2`, { decision: "reject", reason: "tone_issue", note: reason })}>
                    {tr("papers.reject")}
                  </button>
                </div>
              </>
            ) : (
              <p className="muted">{view.lesson2.note ?? tr("demo.s11.lesson2_none")}</p>
            )}
          </article>
          <label className="field">
            <span>{tr("papers.reject_reason")}</span>
            <input value={reason} maxLength={300} onChange={(e) => setReason(e.target.value)} />
          </label>
        </div>
      ) : null}
      {tab === "officer" && dash ? <OfficerDash dash={dash} /> : null}
    </div>
  );
}

function cell(n: number | null, tr: (k: Key, p?: Record<string, string | number>) => string): string {
  return n === null ? tr("demo.dash.hidden") : String(n);
}

function OfficerDash({ dash }: { dash: Dashboard }) {
  const { tr } = useApp();
  return (
    <div className="stack" data-testid="demo-dashboard">
      <SimulatedBanner />
      <p>{tr("demo.dash.intro", { n: dash.classes })}</p>
      <p className="muted">{tr("demo.dash.min5")}</p>
      <div className="table-scroll" role="region" tabIndex={0} aria-label={tr("demo.dash.cohorts")}>
        <table data-testid="demo-dash-cohorts">
          <caption>{tr("demo.dash.cohorts")}</caption>
          <thead>
            <tr>
              <th scope="col">{tr("demo.dash.error")}</th>
              <th scope="col">{tr("demo.dash.classes")}</th>
            </tr>
          </thead>
          <tbody>
            {dash.cohorts.map((r) => (
              <tr key={r.error}>
                <th scope="row">{r.error}</th>
                <td>{cell(r.classes, tr)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="table-scroll" role="region" tabIndex={0} aria-label={tr("demo.dash.by_error")}>
        <table data-testid="demo-dash-errors">
          <caption>{tr("demo.dash.by_error")}</caption>
          <thead>
            <tr>
              <th scope="col">{tr("demo.dash.error")}</th>
              <th scope="col">{tr("demo.dash.classes")}</th>
              <th scope="col">{tr("demo.dash.share")}</th>
            </tr>
          </thead>
          <tbody>
            {dash.by_error.map((r) => (
              <tr key={r.error}>
                <th scope="row">{r.error}</th>
                <td>{cell(r.classes, tr)}</td>
                <td>{r.share === null ? tr("demo.dash.hidden") : `${r.share}%`}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p data-testid="demo-dash-tracks">{tr("demo.dash.tracks", { started: cell(dash.tracks_started, tr), next: cell(dash.waiting_next_term, tr) })}</p>
      <p data-testid="demo-dash-pending">{tr("demo.dash.pending", { n: dash.approvals_pending })}</p>
      {dash.before_after ? (
        <div className="table-scroll" role="region" tabIndex={0} aria-label={tr("demo.dash.before_after")}>
          <table data-testid="demo-dash-before-after">
            <caption>{tr("demo.dash.before_after")}</caption>
            <thead>
              <tr>
                <th scope="col">{tr("demo.dash.error")}</th>
                <th scope="col">{tr("demo.dash.classes")}</th>
                <th scope="col">{tr("demo.dash.before")}</th>
                <th scope="col">{tr("demo.dash.after")}</th>
              </tr>
            </thead>
            <tbody>
              {dash.before_after.map((r) => (
                <tr key={r.error}>
                  <th scope="row">{r.error}</th>
                  <td>{cell(r.classes, tr)}</td>
                  <td>{r.before === null ? tr("demo.dash.hidden") : tr("demo.dash.of", { n: r.before, total: r.checked_before ?? 0 })}</td>
                  <td>{r.after === null ? tr("demo.dash.hidden") : tr("demo.dash.of", { n: r.after, total: r.checked_after ?? 0 })}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}

// --- step 12 ----------------------------------------------------------------------------------

function StepPost() {
  const { tr, klass, term, reload } = useApp();
  const sid = demoSession();
  const [done, setDone] = useState(false);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  async function simulate() {
    if (!sid || !klass) return;
    setBusy(true);
    try {
      const out = await dcall<{ rows: string[][]; form: string; paper_code: string | null }>(`/${sid}/post-test`, { method: "POST" });
      // the post-test is the pre-test's twin paper: its own key comes from the server like any paper's
      if (out.form.startsWith("P-")) await fetchPaperKey(out.form, { role: "teacher", classId: klass.id });
      await db.checks.put({
        id: `${klass.id}:${term + 1}`, classId: klass.id, term: term + 1, formKey: out.form, children: out.rows, updatedAt: Date.now(), paperId: out.form.startsWith("P-") ? out.form : null, paperCode: out.paper_code,
        kind: "post", round: 1, checkDate: new Date(Date.now() + 21 * 86400000).toISOString().slice(0, 10), expectedChildren: out.rows.length, status: "closed", confirm: false, notes: "Simulated post-test (demo)",
      });
      await reload();
      setDone(true);
    } catch {
      setMsg(tr("demo.error"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack" data-testid="demo-step-12">
      <h2>{tr("demo.s12.title")}</h2>
      <p>{tr("demo.s12.body")}</p>
      <button type="button" className="btn btn-primary" disabled={done} onClick={() => void simulate()} data-testid="demo-post">
        {tr("demo.s12.simulate")}
      </button>
      {busy ? <Busy text={tr("demo.busy.post")} testId="demo-busy" /> : null}
      {msg ? <p role="alert">{msg}</p> : null}
      {done ? (
        <>
          <SimulatedBanner />
          <BeforeAfter />
        </>
      ) : null}
    </div>
  );
}
