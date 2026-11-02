// The cohort chat: a small, moderated, pseudonymous thread. A teacher joins with her own tap and
// appears as a label ("Teacher 3"). Every post is checked by the server for names and details; a
// failed check asks her to rewrite. A coach sees held posts and can hide, restore, pin or erase the
// text, post a prompt, and start closing her cohort. The chat polls every 30 seconds while open.
import { useCallback, useEffect, useState } from "react";
import { Icon } from "../components/icons";
import type { Key } from "../i18n";
import { ccall, CohortError, type CohortSummary, type Who } from "../lib/cohort";
import { useApp } from "../state";
import { SimulatedBanner } from "../components/parts";
import { ClassOnlyForCoach } from "../components/MyClassCohorts";
import { GatedChat } from "../components/GatedChat";
import { loadMine, type MyCohort } from "../lib/gatedChat";

export default function Cohort() {
  const { tr, role, lang, klass } = useApp();
  const [view, setView] = useState<Who>(role === "coach" ? "coach" : "teacher");
  const who: Who = role === "coach" ? "coach" : role === "mentor" ? "mentor" : role === "judge" ? view : "teacher";
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
      ) : who === "mentor" ? (
        <MentorView tr={tr} />
      ) : (
        <>
          <TeacherView tr={tr} />
        </>
      )}
    </section>
  );
}

type Tr = (key: Key, params?: Record<string, string | number>) => string;

function TeacherView({ tr }: { tr: Tr }) {
  const [cohorts, setCohorts] = useState<MyCohort[]>([]);
  const [current, setCurrent] = useState<MyCohort | null>(null);
  const [agree, setAgree] = useState(false);
  const [msg, setMsg] = useState<{ text: string; bad?: boolean } | null>(null);

  const loadList = useCallback(async () => {
    try {
      setCohorts(await loadMine());
    } catch {
      setMsg({ text: tr("cohort.error"), bad: true });
    }
  }, [tr]);
  useEffect(() => {
    void loadList();
  }, [loadList]);
  async function join(c: MyCohort) {
    try {
      await ccall(`/${c.id}/join`, "teacher", { method: "POST", body: { consent: agree } });
      setCurrent({ ...c, joined: true });
      await loadList();
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
      {!current && cohorts.length === 0 ? (
        <p className="muted" data-testid="gchat-no-cohorts">
          {tr("gchat.no_cohorts")}
        </p>
      ) : !current ? (
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
                  {c.name ? `${c.name} · ` : ""}
                  {tr(`err.${c.error}` as Key)} · {tr(`cohort.st.${c.status}` as Key)} · {c.members === null ? tr("cohort.members_hidden") : tr("cohort.members", { n: c.members })}
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
        <GatedChat cohortId={current.id} role="teacher" />
      )}
    </>
  );
}

function CoachView({ tr, lang }: { tr: Tr; lang: string }) {
  const [cohorts, setCohorts] = useState<CohortSummary[]>([]);
  const [current, setCurrent] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [msg, setMsg] = useState<{ text: string; bad?: boolean } | null>(null);

  const load = useCallback(async () => {
    try {
      setCohorts(await ccall<CohortSummary[]>("/coach/cohorts", "coach"));
    } catch {
      setMsg({ text: tr("cohort.error"), bad: true });
    }
  }, [current, tr]);
  useEffect(() => {
    void load();
  }, [load]);

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
              {tr("cohort.chat")}
            </button>
          </li>
        ))}
      </ul>
      {current ? (
        <>
          <GatedChat cohortId={current} role="coach" />
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

function MentorView({ tr }: { tr: Tr }) {
  const [cohorts, setCohorts] = useState<CohortSummary[]>([]);
  const [current, setCurrent] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    ccall<CohortSummary[]>("/mentor/cohorts", "mentor").then(setCohorts, () => setFailed(true));
  }, []);
  return (
    <>
      {failed ? <p role="alert">{tr("cohort.error")}</p> : null}
      {cohorts.length === 0 && !failed ? <p className="muted" data-testid="gchat-no-cohorts">{tr("gchat.no_cohorts")}</p> : null}
      <ul className="plain">
        {cohorts.map((c) => (
          <li key={c.id} className="class-row" data-testid={`mentor-cohort-${c.id}`}>
            <span className="class-name">
              {c.error} · {tr(`cohort.st.${c.status}` as Key)}
            </span>
            <button type="button" className="btn btn-secondary" onClick={() => setCurrent(c.id)}>
              {tr("cohort.chat")}
            </button>
          </li>
        ))}
      </ul>
      {current ? <GatedChat cohortId={current} role="mentor" /> : null}
    </>
  );
}
