// The gated cohort chat: one thread for a cohort's teachers, its mentor and its coach. Everyone is a label, never
// a name. A question starts a timer on the server; if no mentor or coach replies in time, the AI answers from
// approved sources, clearly labelled, and the coach can correct it. This screen only shows what the server
// allows and sends what she writes; masking, roles and the timer are the server's.
import { useCallback, useEffect, useRef, useState } from "react";
import type { Key } from "../i18n";
import { ChatError, ChatQueued, correctAi, loadInbox, loadThread, moderate, postMessage, reportMessage, resolveQuestion, secondsLeft, setTimeoutSeconds, threaded, type ChatMessage, type ChatRole, type ChatThread, type InboxItem } from "../lib/gatedChat";
import { useApp } from "../state";
import { Icon } from "./icons";

const LIMIT = 500;
const POLL_OPEN_MS = 2000;
const POLL_HIDDEN_MS = 30000;

type Tr = (key: Key, params?: Record<string, string | number>) => string;

function when(iso: string, lang: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleTimeString(lang === "hi" ? "hi-IN" : lang === "ta" ? "ta-IN" : "en-IN", { hour: "2-digit", minute: "2-digit" });
}
function day(iso: string, lang: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleDateString(lang === "hi" ? "hi-IN" : lang === "ta" ? "ta-IN" : "en-IN", { day: "numeric", month: "short" });
}

export function GatedChat({ cohortId, role }: { cohortId: string; role: ChatRole }) {
  const { tr, lang, online } = useApp();
  const [thread, setThread] = useState<ChatThread | null>(null);
  const [fetchedAt, setFetchedAt] = useState(0);
  const [state, setState] = useState<"loading" | "ok" | "error">("loading");
  const [tick, setTick] = useState(0);
  const [inbox, setInbox] = useState<InboxItem[]>([]);
  const [tab, setTab] = useState<"thread" | "inbox">("thread");
  const [announce, setAnnounce] = useState("");
  const endRef = useRef<HTMLDivElement | null>(null);
  const lastCount = useRef(0);

  const load = useCallback(async () => {
    try {
      const t = await loadThread(cohortId, role);
      setThread(t);
      setFetchedAt(Date.now());
      setState("ok");
      if (role !== "teacher") setInbox((await loadInbox(role)).items);
      if (t.messages.length > lastCount.current && lastCount.current > 0) setAnnounce(tr("gchat.new_messages", { n: t.messages.length - lastCount.current }));
      lastCount.current = t.messages.length;
    } catch {
      setState((s) => (s === "ok" ? s : "error"));
    }
  }, [cohortId, role, tr]);

  useEffect(() => {
    if (!online) return;
    void load();
    let id: ReturnType<typeof setInterval>;
    const start = () => {
      clearInterval(id);
      id = setInterval(() => void load(), document.hidden ? POLL_HIDDEN_MS : POLL_OPEN_MS);
    };
    start();
    document.addEventListener("visibilitychange", start);
    return () => {
      clearInterval(id);
      document.removeEventListener("visibilitychange", start);
    };
  }, [load, online]);

  useEffect(() => {
    const id = setInterval(() => setTick((n) => n + 1), 1000); // the countdown redraws each second
    return () => clearInterval(id);
  }, []);
  useEffect(() => {
    endRef.current?.scrollIntoView?.({ block: "end" });
  }, [thread?.messages.length]);
  void tick;

  if (state === "loading") return <p role="status" className="muted" data-testid="gchat-loading">{tr("gchat.loading")}</p>;
  if (!thread || state === "error") {
    return (
      <div role="alert" data-testid="gchat-error">
        <p>{tr("gchat.error")}</p>
        <button type="button" className="btn btn-secondary" onClick={() => { setState("loading"); void load(); }}>
          {tr("gchat.retry")}
        </button>
      </div>
    );
  }
  const c = thread.cohort;
  const waitingCount = inbox.filter((i) => i.qstatus === "waiting").length;
  const rows = threaded(thread.messages);
  let lastDay = "";
  return (
    <section className="gchat stack" aria-label={tr("cohort.title")} data-testid="gchat">
      <header className="gchat-head">
        <h2>{tr(`err.${c.error}` as Key)}</h2>
        <p className="muted" data-testid="gchat-counts">{tr("gchat.counts", { t: c.teachers, m: c.mentors, c: c.coaches })}</p>
        <p className="muted" data-testid="gchat-timeout">
          {tr("gchat.timeout_line", { n: thread.timeout.seconds })}
          {thread.timeout.source === "demo" ? ` ${tr("gchat.demo_value")}` : ""}
        </p>
        {thread.ai_mode === "off" ? <p className="note">{tr("gchat.ai_off")}</p> : null}
        {!online ? <p className="note" data-testid="gchat-offline">{tr("gchat.offline")}</p> : null}
      </header>
      <p className="note" data-testid="gchat-pinned">
        <Icon name="lock" size={18} /> {thread.pinned?.text ?? tr("gchat.pinned_default")}
      </p>
      {role !== "teacher" ? (
        <div className="subtabs" role="group" aria-label={tr("gchat.inbox")}>
          <button type="button" className={tab === "thread" ? "subtab subtab-on" : "subtab"} aria-pressed={tab === "thread"} onClick={() => setTab("thread")}>{tr("cohort.chat")}</button>
          <button type="button" className={tab === "inbox" ? "subtab subtab-on" : "subtab"} aria-pressed={tab === "inbox"} onClick={() => setTab("inbox")} data-testid="gchat-inbox-tab">
            {tr("gchat.inbox")} {waitingCount > 0 ? <span className="chip" data-testid="gchat-inbox-badge">{waitingCount}</span> : null}
          </button>
        </div>
      ) : null}
      {tab === "inbox" && role !== "teacher" ? (
        <Inbox items={inbox} aiMode={thread.ai_mode} tr={tr} onOpen={() => setTab("thread")} />
      ) : (
        <>
          <div role="log" aria-live="polite" aria-relevant="additions" className="gchat-log" data-testid="gchat-log">
            {rows.length === 0 ? <p className="muted" data-testid="gchat-empty">{tr("gchat.empty")}</p> : null}
            {rows.map(({ message: m, replies }) => {
              const d = day(m.created_at, lang);
              const heading = d !== lastDay ? d : "";
              lastDay = d;
              return (
                <div key={m.id}>
                  {heading ? <p className="muted gchat-day">{heading}</p> : null}
                  <Card m={m} thread={thread} fetchedAt={fetchedAt} cohortId={cohortId} role={role} tr={tr} lang={lang} onChanged={load} online={online}>
                    {replies.map((r) => (
                      <div key={r.id} className="gchat-reply">
                        <Card m={r} thread={thread} fetchedAt={fetchedAt} cohortId={cohortId} role={role} tr={tr} lang={lang} onChanged={load} online={online} />
                      </div>
                    ))}
                  </Card>
                </div>
              );
            })}
            <div ref={endRef} />
          </div>
          <p className="sr-only" role="status" aria-live="polite">{announce}</p>
          {thread.state === "open" ? <Composer cohortId={cohortId} role={role} tr={tr} lang={lang} online={online} onSent={load} /> : <p className="note" data-testid="gchat-readonly">{tr("gchat.read_only")}</p>}
          {role === "coach" ? <TimeoutSetting cohortId={cohortId} current={thread.timeout.seconds} tr={tr} onSaved={load} /> : null}
        </>
      )}
    </section>
  );
}

function statusKey(m: ChatMessage): Key | null {
  switch (m.qstatus) {
    case "waiting":
    case "answering":
      return "gchat.q.waiting";
    case "answered_human":
      return "gchat.q.answered_human";
    case "answered_ai":
      return "gchat.q.answered_ai";
    case "corrected":
      return "gchat.q.corrected";
    case "resolved":
      return "gchat.q.resolved";
    default:
      return null;
  }
}

function Card({ m, thread, fetchedAt, cohortId, role, tr, lang, onChanged, online, children }: { m: ChatMessage; thread: ChatThread; fetchedAt: number; cohortId: string; role: ChatRole; tr: Tr; lang: string; onChanged: () => Promise<void>; online: boolean; children?: React.ReactNode }) {
  const [reply, setReply] = useState<string | null>(null);
  const [err, setErr] = useState("");
  const mine = m.author === thread.me;
  const isAi = m.kind === "ai_reply";
  const left = m.kind === "question" && (m.qstatus === "waiting" || m.qstatus === "answering") && !m.abstained ? secondsLeft(m.ai_due_at, thread.server_time, fetchedAt) : null;
  const key = statusKey(m);
  const act = async (fn: () => Promise<unknown>) => {
    setErr("");
    try {
      await fn();
      await onChanged();
    } catch (e) {
      setErr(e instanceof ChatError && e.codes.length ? tr("gchat.blocked", { what: e.codes.join(", ") }) : tr("gchat.error"));
    }
  };
  const staff = role === "mentor" || role === "coach";
  const label = `${m.author}, ${tr(`gchat.kind.${m.kind}` as Key)}, ${when(m.created_at, lang)}`;
  return (
    <article className={`gchat-card gchat-${m.kind}`} aria-label={label} data-testid={`gchat-msg-${m.id}`} data-kind={m.kind} data-qstatus={m.qstatus ?? ""}>
      <p className="gchat-who">
        {isAi ? <Icon name="info" size={18} /> : null}
        <strong>{mine ? `${m.author} (${tr("gchat.you")})` : m.author}</strong>{" "}
        <span className="chip">{tr(`gchat.role.${isAi ? "ai" : m.role === "system" ? "system" : m.role}` as Key)}</span>{" "}
        <span className="muted">{when(m.created_at, lang)}</span>
        {m.demo ? <span className="chip"> {tr("gchat.demo")}</span> : null}
        {m.pinned ? <span className="chip"> {tr("cohort.post.pinned")}</span> : null}
        {key ? <span className="chip" data-testid={`gchat-status-${m.id}`}> {tr(key)}</span> : null}
      </p>
      {m.hidden && m.text === null ? <p className="muted">{tr("gchat.hidden")}</p> : <p style={{ whiteSpace: "pre-line" }}>{m.text}</p>}
      {m.masked.length > 0 && mine ? <p className="muted">{tr("gchat.masked", { what: m.masked.join(", ") })}</p> : null}
      {isAi ? (
        <p className="muted" data-testid={`gchat-ailabel-${m.id}`}>
          {m.ai_label === "recorded" ? `${tr("gchat.ai.recorded")}. ` : ""}
          {tr("gchat.ai.label", { n: m.after_seconds ?? 0 })}
          {m.corrected ? <span className="chip"> {tr("gchat.corrected_badge")}</span> : null}
        </p>
      ) : null}
      {m.kind === "correction" ? <p className="muted">{tr("gchat.correction")}</p> : null}
      {left !== null ? (
        <p className="muted" role="timer" data-testid={`gchat-countdown-${m.id}`}>
          {tr("gchat.countdown", { n: left })}
        </p>
      ) : null}
      <div className="row">
        {m.kind === "question" ? (
          <button type="button" className="btn btn-secondary" onClick={() => setReply(reply === null ? "" : null)} data-testid={`gchat-reply-${m.id}`}>
            {tr("gchat.reply")}
          </button>
        ) : null}
        {!mine && !isAi ? (
          <button type="button" className="btn btn-secondary" disabled={!online} onClick={() => void act(() => reportMessage(cohortId, role, m.id))}>
            {tr("gchat.report")}
          </button>
        ) : null}
        {staff && m.kind === "question" && m.qstatus !== "resolved" ? (
          <button type="button" className="btn btn-secondary" disabled={!online} onClick={() => void act(() => resolveQuestion(cohortId, role, m.id))} data-testid={`gchat-resolve-${m.id}`}>
            {tr("gchat.resolve")}
          </button>
        ) : null}
        {role === "coach" && isAi && !m.corrected ? (
          <button type="button" className="btn btn-secondary" onClick={() => setReply(reply === null ? "" : null)} data-testid={`gchat-correct-${m.id}`}>
            {tr("gchat.correct")}
          </button>
        ) : null}
        {role === "coach" ? (
          <>
            <button type="button" className="btn btn-secondary" disabled={!online} onClick={() => void act(() => moderate(cohortId, role, m.id, m.hidden ? "restore" : "hide"))}>
              {tr(m.hidden ? "gchat.restore" : "gchat.hide")}
            </button>
            <button type="button" className="btn btn-secondary" disabled={!online} onClick={() => void act(() => moderate(cohortId, role, m.id, m.pinned ? "unpin" : "pin"))}>
              {tr(m.pinned ? "gchat.unpin" : "gchat.pin")}
            </button>
          </>
        ) : null}
      </div>
      {reply !== null ? (
        <div className="stack">
          <textarea rows={3} maxLength={LIMIT} value={reply} onChange={(e) => setReply(e.target.value)} aria-label={tr("gchat.compose.label")} data-testid={`gchat-reply-text-${m.id}`} />
          <button
            type="button"
            className="btn btn-primary"
            disabled={!reply.trim() || !online}
            onClick={() => void act(async () => { await (isAi ? correctAi(cohortId, role, m.id, reply, lang) : postMessage(cohortId, role, "reply", reply, lang, m.id)); setReply(null); })}
            data-testid={`gchat-reply-send-${m.id}`}
          >
            {tr(isAi ? "gchat.correct_send" : "gchat.reply_send")}
          </button>
        </div>
      ) : null}
      {err ? <p role="alert">{err}</p> : null}
      {children}
    </article>
  );
}

function Composer({ cohortId, role, tr, lang, online, onSent }: { cohortId: string; role: ChatRole; tr: Tr; lang: string; online: boolean; onSent: () => Promise<void> }) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ text: string; bad?: boolean } | null>(null);
  const send = async (kind: "question" | "tip") => {
    if (!text.trim() || text.length > LIMIT || busy) return;
    setBusy(true);
    try {
      const r = await postMessage(cohortId, role, kind, text, lang);
      setText("");
      setMsg(r.hidden.length > 0 ? { text: tr("gchat.masked", { what: r.hidden.join(", ") }) } : null);
      await onSent();
    } catch (e) {
      if (e instanceof ChatQueued) {
        setText("");
        setMsg({ text: tr("sync.queued_note") });
        return;
      }
      setMsg({ text: e instanceof ChatError && e.codes.length ? tr("gchat.blocked", { what: e.codes.join(", ") }) : tr("gchat.error"), bad: true });
    } finally {
      setBusy(false);
    }
  };
  const canAsk = role === "teacher";
  return (
    <div className="panel stack" data-testid="gchat-composer">
      <p className="note"><Icon name="lock" size={18} /> {tr("gchat.names_hidden")}</p>
      {role === "teacher" ? <p className="muted" data-testid="gchat-ai-notice">{tr("gchat.ai_notice")}</p> : null}
      <label className="field">
        <span>{tr("gchat.compose.label")}</span>
        <textarea rows={4} value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) void send(canAsk ? "question" : "tip"); }} data-testid="gchat-text" />
      </label>
      <p className={text.length > LIMIT ? "banner" : "muted"} data-testid="gchat-counter">{tr("gchat.compose.count", { n: text.length })}</p>
      {msg ? <p role={msg.bad ? "alert" : "status"} className={msg.bad ? "banner" : "note"} data-testid="gchat-msg">{msg.text}</p> : null}
      <div className="row">
        {canAsk ? (
          <button type="button" className="btn btn-primary" disabled={!text.trim() || text.length > LIMIT || busy || !online} onClick={() => void send("question")} data-testid="gchat-ask">
            {tr("gchat.ask")}
          </button>
        ) : null}
        <button type="button" className={canAsk ? "btn btn-secondary" : "btn btn-primary"} disabled={!text.trim() || text.length > LIMIT || busy || !online} onClick={() => void send("tip")} data-testid="gchat-tip">
          {tr("gchat.tip")}
        </button>
      </div>
    </div>
  );
}

function Inbox({ items, aiMode, tr, onOpen }: { items: InboxItem[]; aiMode: string; tr: Tr; onOpen: () => void }) {
  return (
    <div className="stack" data-testid="gchat-inbox">
      {aiMode === "off" ? <p className="note">{tr("gchat.inbox_ai_off")}</p> : null}
      {items.length === 0 ? <p className="muted">{tr("gchat.inbox_none")}</p> : null}
      <ul className="plain">
        {items.map((i) => (
          <li key={i.id} className="panel" data-testid={`gchat-inbox-${i.id}`}>
            <p><strong>{i.author}</strong> {i.abstained ? <span className="chip">{tr("gchat.inbox_abstained")}</span> : null} {i.seconds_left !== null ? <span className="muted">{tr("gchat.inbox_left", { n: i.seconds_left })}</span> : null}</p>
            <p>{i.text}</p>
            <button type="button" className="btn btn-secondary" onClick={onOpen}>{tr("gchat.inbox_open")}</button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function TimeoutSetting({ cohortId, current, tr, onSaved }: { cohortId: string; current: number; tr: Tr; onSaved: () => Promise<void> }) {
  const [value, setValue] = useState(String(current));
  const [bad, setBad] = useState(false);
  const save = async () => {
    setBad(false);
    try {
      await setTimeoutSeconds(cohortId, "coach", Number(value));
      await onSaved();
    } catch {
      setBad(true);
    }
  };
  return (
    <div className="panel stack" data-testid="gchat-timeout-setting">
      <label className="field">
        <span>{tr("gchat.timeout_label")}</span>
        <input type="number" min={5} max={86400} value={value} onChange={(e) => setValue(e.target.value)} data-testid="gchat-timeout-input" />
      </label>
      <button type="button" className="btn btn-secondary" onClick={() => void save()} data-testid="gchat-timeout-save">{tr("gchat.timeout_save")}</button>
      {bad ? <p role="alert">{tr("gchat.timeout_bad")}</p> : null}
    </div>
  );
}
