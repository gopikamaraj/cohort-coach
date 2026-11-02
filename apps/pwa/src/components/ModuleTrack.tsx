// The improvement track as a timeline of modules. Only the next module is ever made: the current one shows its
// text (collapsible), Download audio, why it was chosen and the feedback card; later ones show a title and a due
// date only. "Get the next module" opens after feedback (or the next module arrives on its due date by itself).
// Code on the server decides which module comes next; this only shows it. Nothing here names a child.
import { useCallback, useEffect, useState } from "react";
import type { Key } from "../i18n";
import type { ClassCohort } from "../lib/classCohort";
import { endBanner, getNext, loadTrack, markDownloaded, ModuleError, nextBlocked, sendFeedback, startTrack, CHIPS, sendWhyNot, type Answer, type Chip, type ModuleStatus, type ModuleView, type TextPart, type TrackView } from "../lib/modules";
import { exportStem } from "../lib/packAudio";
import { href } from "../lib/router";
import { useApp } from "../state";
import { AudioDownload } from "./AudioDownload";
import { Icon, type IconName } from "./icons";

const STATUS_ICON: Record<ModuleStatus, IconName> = {
  planned: "history",
  ready: "play",
  downloaded: "download",
  feedback_given: "ok",
  completed: "check",
  skipped: "minus",
  expired: "warning",
};

const ANSWERS: Answer[] = ["worked", "partly", "not_yet", "not_tried"];
const ANSWER_ICON: Record<Answer, IconName> = { worked: "ok", partly: "refresh", not_yet: "warning", not_tried: "history" };

/** "17 Nov" in her language; the server's date is a plain calendar date. */
export function shortDate(iso: string, lang: string): string {
  const d = new Date(`${iso}T00:00:00`);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString(lang === "hi" ? "hi-IN" : lang === "ta" ? "ta-IN" : "en-IN", { day: "numeric", month: "short" });
}

export function ModuleTrack({ cohort, code }: { cohort: ClassCohort; code: string }) {
  const { tr, lang, online } = useApp();
  const [track, setTrack] = useState<TrackView | null>(null);
  const [offlineCopy, setOfflineCopy] = useState(false);
  const [busy, setBusy] = useState<"" | "start" | "next">("");
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const onServer = !cohort.id.startsWith("local-");

  useEffect(() => {
    let live = true;
    setLoaded(false);
    if (!onServer) {
      setTrack(null);
      setLoaded(true);
      return;
    }
    loadTrack(cohort.id, code, lang).then(
      (r) => {
        if (!live) return;
        setTrack(r.track);
        setOfflineCopy(r.offline);
        setLoaded(true);
      },
      () => live && setLoaded(true),
    );
    return () => {
      live = false;
    };
  }, [cohort.id, code, lang, online, onServer]);

  const run = useCallback(
    async (kind: "start" | "next", fn: () => Promise<TrackView>) => {
      setBusy(kind);
      setFailed(false);
      try {
        setTrack(await fn());
        setOfflineCopy(false);
      } catch (e) {
        // a closed button (409) is not an error: the screen already says why; the view is refreshed
        if (!(e instanceof ModuleError && e.status === 409)) setFailed(true);
      } finally {
        setBusy("");
      }
    },
    [],
  );

  if (!loaded && !track) return <p className="muted" role="status">{tr("module.getting")}</p>;

  if (!track) {
    return (
      <section className="stack module-track" data-testid="module-track" aria-label={tr("module.timeline")}>
        <h3>{tr("module.timeline")}</h3>
        {onServer && online ? (
          <button type="button" className="btn btn-primary" disabled={busy === "start"} onClick={() => void run("start", () => startTrack(cohort.id, code, lang))} data-testid="module-start">
            {busy === "start" ? tr("module.starting") : tr("module.start")}
          </button>
        ) : (
          <p className="muted" data-testid="module-offline">
            {tr("module.next_offline")}
          </p>
        )}
        {failed ? <p role="alert">{tr("module.start_err")}</p> : null}
      </section>
    );
  }

  const blocked = nextBlocked(track);
  const banner = endBanner(track);
  const hasMore = track.can_next.code !== "no_more" && track.status === "active";
  const lastMade = track.modules.filter((m) => m.status !== "planned").length === track.total && track.status === "active";
  return (
    <section className="stack module-track" data-testid="module-track" aria-label={tr("module.timeline")}>
      <h3>{tr("module.timeline")}</h3>
      {track.note ? <p className="muted" data-testid="module-one-only">{tr("module.one_only")}</p> : null}
      {banner ? (
        <p className="module-banner" role="status" data-testid="module-banner">
          <Icon name={banner === "module.end_banner" ? "ok" : "info"} size={20} /> {tr(banner)}
        </p>
      ) : null}
      <ol className="module-list" data-testid="module-list">
        {track.modules.map((m) => (
          <ModuleItem key={m.number} m={m} track={track} code={code} current={m.number === track.current} onTrack={setTrack} />
        ))}
      </ol>
      {hasMore ? (
        <div className="module-next">
          <button type="button" className="btn btn-primary" disabled={!track.can_next.enabled || !online || busy === "next"} aria-describedby="module-next-note" onClick={() => void run("next", () => getNext(track.id, lang))} data-testid="module-next">
            {busy === "next" ? tr("module.getting") : tr("module.get_next")}
          </button>
          <p id="module-next-note" className="muted" data-testid="module-next-note">
            {!online || offlineCopy ? tr("module.next_offline") : blocked ? tr(blocked.key, { n: blocked.slots.n, next: blocked.slots.next, date: shortDate(blocked.slots.date, lang) }) : ""}
          </p>
        </div>
      ) : null}
      {lastMade ? <p className="muted">{tr("module.last_one")}</p> : null}
      {failed ? <p role="alert">{tr("module.err")}</p> : null}
    </section>
  );
}

function ModuleItem({ m, track, code, current, onTrack }: { m: ModuleView; track: TrackView; code: string; current: boolean; onTrack: (t: TrackView) => void }) {
  const { tr, lang } = useApp();
  const made = m.status !== "planned";
  return (
    <li className={current ? "module-item module-current" : "module-item"} data-testid={`module-${m.number}`} aria-current={current ? "step" : undefined}>
      <div className="module-head">
        <span className="module-n">{tr("module.n_of", { n: m.number, total: track.total })}</span>
        <span className={`chip module-status module-status-${m.status}`} data-testid={`module-${m.number}-status`}>
          <Icon name={STATUS_ICON[m.status]} size={16} /> {tr(`module.status.${m.status}` as Key)}
        </span>
      </div>
      <p className="module-title">
        <strong>{m.title}</strong>
      </p>
      {!made ? (
        <p className="muted" data-testid={`module-${m.number}-due`}>
          {tr("module.due", { date: shortDate(m.due_date, lang) })}
        </p>
      ) : (
        <ModuleBody m={m} track={track} code={code} current={current} onTrack={onTrack} />
      )}
    </li>
  );
}

function ModuleBody({ m, track, code, current, onTrack }: { m: ModuleView; track: TrackView; code: string; current: boolean; onTrack: (t: TrackView) => void }) {
  const { tr, lang } = useApp();
  const parts: TextPart[] = m.text?.parts ?? [];
  const fallback = parts.some((p) => p.fallback);
  const draft = parts.some((p) => p.draft);
  const speakLang = m.language ?? track.language;
  return (
    <div className="stack module-body">
      {draft ? <span className="chip chip-draft">{tr("module.draft")}</span> : null}
      {m.reason_text ? (
        <details className="module-why" data-testid={`module-${m.number}-why`}>
          <summary>{tr("module.why")}</summary>
          <p>{m.reason_text}</p>
        </details>
      ) : null}
      <details open={current} className="module-text" data-testid={`module-${m.number}-text`}>
        <summary>{tr("module.show_text")}</summary>
        {fallback ? <p className="muted">{tr("module.fallback")}</p> : null}
        {parts.map((p) => (
          <div key={p.id} className="module-part">
            <h4>{tr(`module.part.${p.id}` as Key)}</h4>
            {p.text ? <p>{p.text}</p> : null}
            {p.list ? (
              p.id === "steps" ? (
                <ol>
                  {p.list.map((x) => (
                    <li key={x}>{x}</li>
                  ))}
                </ol>
              ) : (
                <ul>
                  {p.list.map((x) => (
                    <li key={x}>{x}</li>
                  ))}
                </ul>
              )
            ) : null}
          </div>
        ))}
      </details>
      {m.spoken ? (
        <AudioDownload
          request={{ text: m.spoken }}
          language={speakLang}
          code={code}
          label="audio.download"
          testId={`module-${m.number}-audio`}
          stem={exportStem(code, speakLang, `Improvement-Track-Module-${m.number}`)}
          onDone={async (made) => {
            onTrack(await markDownloaded(track.id, m.number, made.filename, lang));
          }}
        />
      ) : null}
      <FeedbackCard m={m} track={track} onTrack={onTrack} late={!current} />
    </div>
  );
}

function FeedbackCard({ m, track, onTrack, late }: { m: ModuleView; track: TrackView; onTrack: (t: TrackView) => void; late: boolean }) {
  const { tr, lang, online } = useApp();
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(false);
  const held = m.feedback?.answer === "not_tried";
  if (m.feedback && !held) {
    return (
      <p className="module-answered" role="status" data-testid={`module-${m.number}-answered`}>
        <Icon name="ok" size={18} /> {tr("module.feedback.saved", { answer: tr(`module.feedback.${m.feedback.answer}` as Key) })}
      </p>
    );
  }
  const send = async () => {
    if (!answer) return;
    setBusy(true);
    setErr(false);
    try {
      onTrack(await sendFeedback(track.id, m.number, answer, note, lang));
      setAnswer(null);
      setNote("");
    } catch {
      setErr(true);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="stack">
      {held ? <HoldPanel m={m} track={track} onTrack={onTrack} /> : null}
      <fieldset className="module-feedback" data-testid={`module-${m.number}-feedback`}>
        <legend>{tr("module.feedback.title", { n: m.number })}</legend>
        {held ? <p className="muted">{tr("module.hold.again")}</p> : null}
        <div className="module-answers" role="radiogroup">
          {ANSWERS.map((a) => (
            <label key={a} className={answer === a ? "module-answer module-answer-on" : "module-answer"}>
              <input type="radio" name={`fb-${m.number}`} value={a} checked={answer === a} onChange={() => setAnswer(a)} data-testid={`module-${m.number}-fb-${a}`} />
              <Icon name={ANSWER_ICON[a]} size={20} />
              <span>{tr(`module.feedback.${a}` as Key)}</span>
            </label>
          ))}
        </div>
        <label className="field">
          <span>{tr("module.feedback.note")}</span>
          <textarea rows={2} maxLength={300} value={note} onChange={(e) => setNote(e.target.value)} />
        </label>
        {late ? <p className="muted">{tr("module.feedback.late")}</p> : null}
        <button type="button" className="btn btn-secondary" disabled={!answer || busy || !online} onClick={() => void send()} data-testid={`module-${m.number}-fb-send`}>
          {tr("module.feedback.save")}
        </button>
        {err ? <p role="alert">{tr("module.err")}</p> : null}
      </fieldset>
    </div>
  );
}

/** She has not tried it yet: nothing advances, nothing is counted. One question (approved chips), a shorter
 *  version, and a way to ask a person. The next date has moved; "Get the next module" still works. */
function HoldPanel({ m, track, onTrack }: { m: ModuleView; track: TrackView; onTrack: (t: TrackView) => void }) {
  const { tr, lang, online } = useApp();
  const [chip, setChip] = useState<Chip | null>(null);
  const [err, setErr] = useState(false);
  const next = track.modules.find((x) => x.status === "planned");
  const pick = async (c: Chip) => {
    setErr(false);
    try {
      onTrack(await sendWhyNot(track.id, m.number, c, lang));
      setChip(c);
    } catch {
      setErr(true);
    }
  };
  const short = m.hold?.short?.parts ?? [];
  return (
    <section className="module-hold" aria-labelledby={`hold-${m.number}`} data-testid={`module-${m.number}-hold`}>
      <h4 id={`hold-${m.number}`}>{tr("module.hold.title")}</h4>
      {next ? <p>{tr("module.hold.intro", { date: shortDate(next.due_date, lang) })}</p> : null}
      <div className="module-chips" role="group" aria-label={tr("module.hold.title")}>
        {CHIPS.map((c) => (
          <button key={c} type="button" className={chip === c ? "chip-btn chip-btn-on" : "chip-btn"} aria-pressed={chip === c} disabled={!online} onClick={() => void pick(c)} data-testid={`module-${m.number}-chip-${c}`}>
            {tr(`module.hold.chip.${c}` as Key)}
          </button>
        ))}
      </div>
      {chip ? <p role="status">{tr("module.hold.chosen", { reason: tr(`module.hold.chip.${chip}` as Key) })}</p> : null}
      {err ? <p role="alert">{tr("module.err")}</p> : null}
      {short.length > 0 ? (
        <details data-testid={`module-${m.number}-short`}>
          <summary>{tr("module.hold.short")}</summary>
          {short.map((p) => (
            <div key={p.id} className="module-part">
              <h4>{tr(`module.part.${p.id}` as Key)}</h4>
              {p.text ? <p>{p.text}</p> : null}
              {p.list ? (
                <ol>
                  {p.list.map((x) => (
                    <li key={x}>{x}</li>
                  ))}
                </ol>
              ) : null}
            </div>
          ))}
        </details>
      ) : null}
      <a className="btn btn-secondary" href={href("/cohort_chat")} data-testid={`module-${m.number}-ask`}>
        {tr("module.hold.ask")}
      </a>
    </section>
  );
}
