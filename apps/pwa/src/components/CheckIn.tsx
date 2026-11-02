// The private check-in after she answers a module: her answer and note (already sent), the optional
// follow-up questions, what changes next, then the sharing step. PRIVATE: a lock banner sits on every step,
// every step has a Skip, and nothing reaches the cohort chat unless she reads the exact text and presses
// Share. The text is built by the server from her answer, the validated tags and her masked note; no AI
// writes it. Share is blocked, with what to remove, if anything identifying remains.
import { useCallback, useEffect, useState } from "react";
import type { Key } from "../i18n";
import { answerReview, BlockedError, callMe, draftCheckin, getCheckin, retractCheckin, runReview, SHARE_FIELDS, shareCheckin, type CheckinState, type ShareField, type TrackView } from "../lib/modules";
import { useApp } from "../state";
import { Icon } from "./icons";
import { OpenChat } from "./OpenChat";

const BLOCK_KEYS = new Set(["child_name", "relative", "roll_number", "phone_or_id", "email", "percent", "class_code", "empty", "length"]);

function Lock() {
  const { tr } = useApp();
  return (
    <p className="checkin-lock" data-testid="checkin-private">
      <Icon name="lock" size={18} /> {tr("module.checkin.private")}
    </p>
  );
}

export function CheckIn({ track, number, answerWord }: { track: TrackView; number: number; answerWord: string }) {
  const { tr, lang, online } = useApp();
  const [st, setSt] = useState<CheckinState | null>(null);
  const [err, setErr] = useState(false);

  const load = useCallback(async () => {
    try {
      setSt(await getCheckin(track.id, number, lang));
    } catch {
      setErr(true);
    }
  }, [track.id, number, lang]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!st) return err ? <p className="muted">{tr("module.err")}</p> : null;
  const rv = st.review;
  return (
    <section className="stack checkin" aria-label={tr("module.checkin.title")} data-testid={`module-${number}-checkin`}>
      <h4>{tr("module.checkin.title")}</h4>
      <p className="module-answered" role="status" data-testid={`module-${number}-answered`}>
        <Icon name="ok" size={18} /> {tr("module.feedback.saved", { answer: answerWord })}
      </p>
      {rv.state === "safety" ? <Safety track={track} number={number} /> : null}
      {rv.state === "asked" ? <FollowUps track={track} number={number} st={st} onDone={setSt} /> : null}
      {rv.state !== "asked" && rv.state !== "safety" && rv.changes ? (
        <div data-testid={`module-${number}-changes`}>
          <Lock />
          <h5>{tr("module.changed.title")}</h5>
          <p>{rv.changes}</p>
        </div>
      ) : null}
      {rv.state !== "asked" && rv.state !== "safety" ? <ShareStep track={track} number={number} st={st} online={online} onChange={setSt} /> : null}
    </section>
  );
}

function Safety({ track, number }: { track: TrackView; number: number }) {
  const { tr } = useApp();
  const [asked, setAsked] = useState(false);
  const [err, setErr] = useState(false);
  return (
    <div className="module-hold" data-testid={`module-${number}-safety`}>
      <Lock />
      <p>{tr("module.review.safety")}</p>
      {asked ? (
        <p role="status">{tr("module.safety.called")}</p>
      ) : (
        <button
          type="button"
          className="btn btn-secondary"
          onClick={() =>
            callMe(track.id, number).then(
              () => setAsked(true),
              () => setErr(true),
            )
          }
          data-testid={`module-${number}-callme`}
        >
          {tr("module.safety.call_me")}
        </button>
      )}
      {err ? <p role="alert">{tr("module.err")}</p> : null}
    </div>
  );
}

function FollowUps({ track, number, st, onDone }: { track: TrackView; number: number; st: CheckinState; onDone: (s: CheckinState) => void }) {
  const { tr, lang } = useApp();
  const [pick, setPick] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(false);
  const qs = st.review.follow_ups;
  const send = async (skip: boolean) => {
    setBusy(true);
    setErr(false);
    try {
      const answers = skip ? [] : qs.filter((q) => pick[q.id]).map((q) => (q.kind === "bank" ? { id: q.id, chip: pick[q.id] } : { id: q.id, text: pick[q.id] }));
      await answerReview(track.id, number, answers, skip, lang);
      onDone(await getCheckin(track.id, number, lang));
    } catch {
      setErr(true);
    } finally {
      setBusy(false);
    }
  };
  return (
    <fieldset className="module-feedback" data-testid={`module-${number}-followups`}>
      <legend>{tr("module.review.title")}</legend>
      <Lock />
      <p className="muted">{tr("module.review.intro")}</p>
      {qs.map((q) => (
        <div key={q.id} className="stack">
          <p>
            <strong>{q.text}</strong>
          </p>
          {q.kind === "bank" ? (
            <div className="module-chips" role="group" aria-label={q.text}>
              {q.chips.map((c) => (
                <button key={c.id} type="button" className={pick[q.id] === c.id ? "chip-btn chip-btn-on" : "chip-btn"} aria-pressed={pick[q.id] === c.id} onClick={() => setPick({ ...pick, [q.id]: c.id })} data-testid={`module-${number}-fu-${q.id}-${c.id}`}>
                  {c.label}
                </button>
              ))}
            </div>
          ) : (
            <label className="field">
              <span>{tr("module.review.free_label")}</span>
              <input type="text" maxLength={200} value={pick[q.id] ?? ""} onChange={(e) => setPick({ ...pick, [q.id]: e.target.value })} data-testid={`module-${number}-fu-${q.id}`} />
            </label>
          )}
        </div>
      ))}
      <div className="pack-actions">
        <button type="button" className="btn btn-secondary" disabled={busy || Object.keys(pick).length === 0} onClick={() => void send(false)} data-testid={`module-${number}-fu-send`}>
          {tr("module.review.send")}
        </button>
        <button type="button" className="btn" disabled={busy} onClick={() => void send(true)} data-testid={`module-${number}-fu-skip`}>
          {tr("module.review.skip")}
        </button>
      </div>
      {err ? <p role="alert">{tr("module.err")}</p> : null}
    </fieldset>
  );
}

function ShareStep({ track, number, st, online, onChange }: { track: TrackView; number: number; st: CheckinState; online: boolean; onChange: (s: CheckinState) => void }) {
  const { tr, lang } = useApp();
  const [fields, setFields] = useState<Record<ShareField, boolean>>(st.share.default_fields);
  const [text, setText] = useState(st.share.draft);
  const [editing, setEditing] = useState(false);
  const [aiHelp, setAiHelp] = useState(false);
  const [open, setOpen] = useState(false); // "Share later" keeps the step closed until she opens it
  const [problems, setProblems] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(false);
  const sh = st.share;

  const rebuild = async (next: Record<ShareField, boolean>) => {
    setFields(next);
    setProblems([]);
    try {
      const d = await draftCheckin(track.id, number, lang, { fields: next });
      setText(d.text);
      setProblems(d.problems);
    } catch {
      setErr(true);
    }
  };
  const recheck = async (t: string) => {
    try {
      setProblems((await draftCheckin(track.id, number, lang, { text: t })).problems);
    } catch {
      /* the server checks again on Share */
    }
  };
  const share = async () => {
    setBusy(true);
    setErr(false);
    try {
      onChange(await shareCheckin(track.id, number, lang, { text, fields, named: fields.name, ai_help: aiHelp && fields.help }));
    } catch (e) {
      if (e instanceof BlockedError) setProblems(e.problems);
      else setErr(true);
    } finally {
      setBusy(false);
    }
  };
  const retract = async () => {
    setBusy(true);
    try {
      onChange(await retractCheckin(track.id, number, lang));
    } catch {
      setErr(true);
    } finally {
      setBusy(false);
    }
  };

  if (sh.shared) {
    return (
      <div className="stack module-share" data-testid={`module-${number}-shared`}>
        <p role="status">
          <Icon name="ok" size={18} /> {tr("module.share.shared")}
        </p>
        <blockquote className="share-text">{sh.posted_text}</blockquote>
        <div className="pack-actions">
          <button type="button" className="btn btn-secondary" disabled={busy || !online} onClick={() => void retract()} data-testid={`module-${number}-retract`}>
            {tr("module.share.retract")}
          </button>
          <OpenChat trackId={track.id} testId={`open-chat-done-${number}`} />
        </div>
        {err ? <p role="alert">{tr("module.err")}</p> : null}
      </div>
    );
  }
  if (!st.chat.available) {
    return (
      <p className="muted" data-testid={`module-${number}-nopeers`}>
        <Icon name="lock" size={16} /> {tr("module.share.not_shared")} {tr("module.share.no_peers")}
      </p>
    );
  }
  if (!open) {
    return (
      <div className="stack module-share" data-testid={`module-${number}-share-closed`}>
        <Lock />
        <p className="muted">{sh.retracted ? tr("module.share.retracted") : tr("module.share.not_shared")}</p>
        {sh.share_later_open ? (
          <>
            <p className="muted">{tr("module.share.later_open")}</p>
            <button type="button" className="btn btn-secondary" onClick={() => setOpen(true)} data-testid={`module-${number}-share-open`}>
              {tr(sh.retracted ? "module.share.btn" : "module.share.later")}
            </button>
          </>
        ) : null}
      </div>
    );
  }
  return (
    <fieldset className="module-feedback module-share" data-testid={`module-${number}-share`}>
      <legend>{tr("module.share.title")}</legend>
      <Lock />
      <p className="muted">{tr("module.share.exact")}</p>
      <div className="module-answers">
        {SHARE_FIELDS.map((f) => (
          <label key={f} className="module-answer">
            <input type="checkbox" checked={fields[f]} disabled={busy || editing} onChange={(e) => void rebuild({ ...fields, [f]: e.target.checked })} data-testid={`module-${number}-field-${f}`} />
            <span>{tr(`module.share.field.${f}` as Key)}</span>
          </label>
        ))}
      </div>
      {fields.name ? <p className="muted">{tr("module.share.named_note")}</p> : null}
      {fields.help ? (
        <label className="module-answer">
          <input type="checkbox" checked={aiHelp} onChange={(e) => setAiHelp(e.target.checked)} data-testid={`module-${number}-ai-help`} />
          <span>{tr("module.share.ai_help")}</span>
        </label>
      ) : null}
      <label className="field">
        <span className="sr-only">{tr("module.share.exact")}</span>
        <textarea
          rows={5}
          maxLength={600}
          value={text}
          readOnly={!editing}
          onChange={(e) => setText(e.target.value)}
          onBlur={() => editing && void recheck(text)}
          data-testid={`module-${number}-share-text`}
        />
      </label>
      {problems.length > 0 ? (
        <p role="alert" data-testid={`module-${number}-share-problems`}>
          {tr("module.share.blocked", { what: problems.map((p) => tr(`module.share.block.${BLOCK_KEYS.has(p) ? p : "other"}` as Key)).join(", ") })}
        </p>
      ) : null}
      {!online ? <p className="muted">{tr("module.share.offline")}</p> : null}
      {!st.chat.open ? <p className="muted">{tr("module.share.thread_closed")}</p> : null}
      <div className="pack-actions">
        <button type="button" className="btn btn-primary" disabled={busy || !online || !st.chat.open || problems.length > 0 || !text.trim()} onClick={() => void share()} data-testid={`module-${number}-share-go`}>
          {tr("module.share.btn")}
        </button>
        <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => setEditing((v) => !v)} aria-pressed={editing} data-testid={`module-${number}-share-edit`}>
          {tr("module.share.edit")}
        </button>
        <button type="button" className="btn" onClick={() => setOpen(false)} data-testid={`module-${number}-share-no`}>
          {tr("module.share.no")}
        </button>
      </div>
      {err ? <p role="alert">{tr("module.err")}</p> : null}
    </fieldset>
  );
}

export { runReview };
