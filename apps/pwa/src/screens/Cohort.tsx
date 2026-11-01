// The cohort chat: a small, moderated, pseudonymous thread. A teacher joins with her own tap and
// appears as a label ("Teacher 3"). Every post is checked by the server for names and details; a
// failed check asks her to rewrite. A coach sees held posts and can hide, restore, pin or erase the
// text, post a prompt, and start closing her cohort. The chat polls every 30 seconds while open.
import { useCallback, useEffect, useState } from "react";
import { Icon } from "../components/icons";
import type { Key } from "../i18n";
import { ccall, CohortError, ordered, showsText, type CohortSummary, type Post, type Who } from "../lib/cohort";
import { useApp } from "../state";
import { SimulatedBanner } from "../components/parts";
import { ClassOnlyForCoach, MyClassCohorts } from "../components/MyClassCohorts";

export default function Cohort() {
  const { tr, role, lang, klass } = useApp();
  const [view, setView] = useState<Who>(role === "coach" ? "coach" : "teacher");
  const who: Who = role === "coach" ? "coach" : role === "judge" ? view : "teacher";
  return (
    <section aria-labelledby="co-title" data-testid="cohort">
      <h1 id="co-title">
        <Icon name="chat" /> {tr("cohort.title")}
      </h1>
      {klass?.simulated || role !== "teacher" ? <SimulatedBanner /> : null}
      <p>{tr("cohort.intro")}</p>
      {role === "judge" ? (
        <div className="subtabs" role="group" aria-label={tr("cohort.view_as")}>
          {(["teacher", "coach"] as const).map((v) => (
            <button key={v} type="button" className={v === view ? "subtab subtab-on" : "subtab"} aria-pressed={v === view} onClick={() => setView(v)} data-testid={`as-${v}`}>
              {tr(v === "teacher" ? "cohort.as_teacher" : "cohort.as_coach")}
            </button>
          ))}
        </div>
      ) : null}
      {who === "coach" ? (
        <>
          <ClassOnlyForCoach />
          <CoachView tr={tr} lang={lang} />
        </>
      ) : (
        <>
          <MyClassCohorts />
          <TeacherView tr={tr} lang={lang} />
        </>
      )}
    </section>
  );
}

type Tr = (key: Key, params?: Record<string, string | number>) => string;

function Posts({ posts, tr, moderator, onAct }: { posts: Post[]; tr: Tr; moderator: boolean; onAct?: (p: Post, action: string, identifier?: boolean) => void }) {
  if (posts.length === 0) return <p className="muted">{tr("cohort.empty")}</p>;
  return (
    <ul className="plain" data-testid="posts">
      {ordered(posts).map((p) => (
        <li key={p.id} className="panel" data-testid={`post-${p.id}`} data-status={p.status}>
          <strong>{p.author_name}</strong>
          {p.pinned ? <span className="chip"> {tr("cohort.post.pinned")}</span> : null}
          {p.status !== "visible" ? <span className="chip"> {tr(`cohort.post.${p.status}` as Key)}</span> : null}
          {showsText(p, moderator) ? <p style={{ whiteSpace: "pre-line" }}>{p.body}</p> : null}
          {onAct ? (
            <div className="row">
              {p.status === "visible" || p.status === "reported" ? (
                <>
                  <button type="button" className="btn btn-secondary" onClick={() => onAct(p, "hide")}>
                    {tr("cohort.coach.hide")}
                  </button>
                  <button type="button" className="btn btn-secondary" onClick={() => onAct(p, "hide", true)} data-testid={`erase-${p.id}`}>
                    {tr("cohort.coach.erase")}
                  </button>
                </>
              ) : null}
              {p.status === "reported" || p.status === "hidden" ? (
                <button type="button" className="btn btn-secondary" onClick={() => onAct(p, "restore")}>
                  {tr("cohort.coach.restore")}
                </button>
              ) : null}
              <button type="button" className="btn btn-secondary" onClick={() => onAct(p, p.pinned ? "unpin" : "pin")}>
                {tr(p.pinned ? "cohort.coach.unpin" : "cohort.coach.pin")}
              </button>
            </div>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

function TeacherView({ tr, lang }: { tr: Tr; lang: string }) {
  const [cohorts, setCohorts] = useState<CohortSummary[]>([]);
  const [current, setCurrent] = useState<CohortSummary | null>(null);
  const [posts, setPosts] = useState<Post[]>([]);
  const [state, setState] = useState<"open" | "read_only">("read_only");
  const [text, setText] = useState("");
  const [agree, setAgree] = useState(false);
  const [msg, setMsg] = useState<{ text: string; bad?: boolean } | null>(null);

  const loadList = useCallback(async () => {
    try {
      setCohorts(await ccall<CohortSummary[]>("/open", "teacher"));
    } catch {
      setMsg({ text: tr("cohort.error"), bad: true });
    }
  }, [tr]);
  const loadThread = useCallback(async () => {
    if (!current) return;
    try {
      const t = await ccall<{ state: "open" | "read_only"; posts: Post[] }>(`/${current.id}/thread`, "teacher");
      setPosts(t.posts);
      setState(t.state);
    } catch {
      setMsg({ text: tr("cohort.error"), bad: true });
    }
  }, [current, tr]);

  useEffect(() => {
    void loadList();
  }, [loadList]);
  useEffect(() => {
    void loadThread();
    if (!current) return;
    const id = setInterval(() => void loadThread(), 30_000);
    return () => clearInterval(id);
  }, [current, loadThread]);

  async function join(c: CohortSummary) {
    try {
      await ccall(`/${c.id}/join`, "teacher", { method: "POST", body: { consent: agree } });
      setCurrent({ ...c, joined: true });
      await loadList();
    } catch {
      setMsg({ text: tr("cohort.error"), bad: true });
    }
  }

  async function send() {
    if (!current || !text.trim()) return;
    try {
      await ccall(`/${current.id}/posts`, "teacher", { method: "POST", body: { body: text.trim(), language: lang } });
      setText("");
      setMsg(null);
      await loadThread();
    } catch (e) {
      if (e instanceof CohortError && e.status === 422) setMsg({ text: tr("cohort.blocked", { codes: e.codes.join(", ") }), bad: true });
      else setMsg({ text: tr("cohort.error"), bad: true });
    }
  }

  async function report(p: Post) {
    try {
      await ccall(`/posts/${p.id}/report`, "teacher", { method: "POST" });
      setMsg({ text: tr("cohort.reported") });
      await loadThread();
    } catch {
      setMsg({ text: tr("cohort.error"), bad: true });
    }
  }

  return (
    <>
      {msg ? (
        <p role={msg.bad ? "alert" : "status"} className={msg.bad ? "banner" : "note"} data-testid="cohort-msg">
          {msg.text}
        </p>
      ) : null}
      {!current ? (
        <div className="panel">
          <h2>{tr("cohort.list")}</h2>
          {cohorts.length === 0 ? <p className="muted">{tr("cohort.none")}</p> : null}
          <label className="check">
            <input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} data-testid="join-consent" />
            <span>{tr("cohort.join_consent")}</span>
          </label>
          <ul className="plain">
            {cohorts.map((c) => (
              <li key={c.id} className="class-row" data-testid={`cohort-${c.id}`}>
                <span className="class-name">
                  {c.error} · {tr(`cohort.st.${c.status}` as Key)} · {c.members === null ? tr("cohort.members_hidden") : tr("cohort.members", { n: c.members })}
                </span>
                {c.joined ? (
                  <button type="button" className="btn btn-secondary" onClick={() => setCurrent(c)} data-testid="open-cohort">
                    {tr("cohort.joined")}
                  </button>
                ) : (
                  <button type="button" className="btn btn-primary" disabled={!agree} onClick={() => void join(c)} data-testid="join">
                    {tr("cohort.join")}
                  </button>
                )}
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <>
          <Posts posts={posts} tr={tr} moderator={false} />
          {posts.length > 0 ? (
            <div className="row">
              {ordered(posts).filter((p) => p.author_kind === "teacher").slice(-1).map((p) => (
                <button key={p.id} type="button" className="btn btn-secondary" onClick={() => void report(p)} data-testid="report">
                  {tr("cohort.report")}
                </button>
              ))}
            </div>
          ) : null}
          {state === "open" ? (
            <div className="panel">
              <p className="note" data-testid="cohort-notice">
                <Icon name="shield" size={18} /> {tr("cohort.notice")}
              </p>
              <label className="field">
                <span>{tr("cohort.compose")}</span>
                <textarea rows={4} maxLength={500} value={text} onChange={(e) => setText(e.target.value)} data-testid="compose" />
              </label>
              <button type="button" className="btn btn-primary" disabled={!text.trim()} onClick={() => void send()} data-testid="send-post">
                {tr("cohort.send")}
              </button>
            </div>
          ) : (
            <p className="note" data-testid="read-only">
              {tr("cohort.read_only")}
            </p>
          )}
        </>
      )}
    </>
  );
}

function CoachView({ tr, lang }: { tr: Tr; lang: string }) {
  const [cohorts, setCohorts] = useState<CohortSummary[]>([]);
  const [current, setCurrent] = useState<string | null>(null);
  const [posts, setPosts] = useState<Post[]>([]);
  const [text, setText] = useState("");
  const [msg, setMsg] = useState<{ text: string; bad?: boolean } | null>(null);

  const load = useCallback(async () => {
    try {
      setCohorts(await ccall<CohortSummary[]>("/coach/cohorts", "coach"));
      if (current) setPosts(await ccall<Post[]>(`/coach/cohorts/${current}/thread`, "coach"));
    } catch {
      setMsg({ text: tr("cohort.error"), bad: true });
    }
  }, [current, tr]);
  useEffect(() => {
    void load();
  }, [load]);

  async function act(p: Post, action: string, identifier = false) {
    try {
      await ccall(`/coach/posts/${p.id}/decide`, "coach", { method: "POST", body: { action, identifier } });
      await load();
    } catch {
      setMsg({ text: tr("cohort.error"), bad: true });
    }
  }
  async function prompt() {
    if (!current || !text.trim()) return;
    try {
      await ccall(`/coach/cohorts/${current}/prompt`, "coach", { method: "POST", body: { body: text.trim(), language: lang } });
      setText("");
      setMsg(null);
      await load();
    } catch (e) {
      if (e instanceof CohortError && e.status === 422) setMsg({ text: tr("cohort.blocked", { codes: e.codes.join(", ") }), bad: true });
      else setMsg({ text: tr("cohort.error"), bad: true });
    }
  }
  async function closing() {
    if (!current) return;
    try {
      await ccall(`/coach/cohorts/${current}/closing`, "coach", { method: "POST" });
      await load();
    } catch {
      setMsg({ text: tr("cohort.error"), bad: true });
    }
  }

  return (
    <>
      <h2>{tr("cohort.coach.title")}</h2>
      {msg ? (
        <p role={msg.bad ? "alert" : "status"} className={msg.bad ? "banner" : "note"}>
          {msg.text}
        </p>
      ) : null}
      <ul className="plain">
        {cohorts.map((c) => (
          <li key={c.id} className="class-row" data-testid={`coach-cohort-${c.id}`}>
            <span className="class-name">
              {c.error} · {tr(`cohort.st.${c.status}` as Key)} · {c.members === null ? tr("cohort.members_hidden") : tr("cohort.members", { n: c.members })}
            </span>
            <button type="button" className="btn btn-secondary" onClick={() => setCurrent(c.id)} data-testid="coach-open">
              {tr("cohort.title")}
            </button>
          </li>
        ))}
      </ul>
      {current ? (
        <>
          <Posts posts={posts} tr={tr} moderator onAct={(p, a, i) => void act(p, a, i)} />
          <div className="panel">
            <label className="field">
              <span>{tr("cohort.coach.prompt")}</span>
              <textarea rows={3} maxLength={500} value={text} onChange={(e) => setText(e.target.value)} data-testid="coach-prompt" />
            </label>
            <div className="row">
              <button type="button" className="btn btn-primary" disabled={!text.trim()} onClick={() => void prompt()} data-testid="coach-post">
                {tr("cohort.send")}
              </button>
              <button type="button" className="btn btn-secondary" onClick={() => void closing()} data-testid="coach-closing">
                {tr("cohort.coach.closing")}
              </button>
            </div>
          </div>
        </>
      ) : null}
    </>
  );
}
