// Practice Class extras: the two tabs, the Review tab (rehearsals recorded on this phone, replayed
// turn by turn), her own impact tag, and the cue card of things to say. Everything here is shown
// in the selected language; nothing leaves the phone.
import { useCallback, useEffect, useState } from "react";
import type { TranscriptRow } from "../lib/db";
import type { FeedbackCard, PracticeMove } from "../lib/practice";
import { deleteAllSessions, deleteSession, IMPACTS, impactCounts, listSessions, moveCounts, setImpact, turnsOf, type Impact } from "../lib/review";
import { useApp } from "../state";

export type PracticeTab = "practise" | "review";

export function PracticeTabs({ tab, onTab }: { tab: PracticeTab; onTab: (t: PracticeTab) => void }) {
  const { tr } = useApp();
  return (
    <div className="tabs" role="tablist">
      {(["practise", "review"] as const).map((t) => (
        <button key={t} type="button" role="tab" aria-selected={tab === t} className={tab === t ? "tab tab-on" : "tab"} onClick={() => onTab(t)} data-testid={`tab-${t}`}>
          {tr(t === "practise" ? "practice.tab_practise" : "practice.tab_review")}
        </button>
      ))}
    </div>
  );
}

export function ImpactPicker({ value, onChange }: { value?: Impact; onChange: (v: Impact | undefined) => void }) {
  const { tr } = useApp();
  return (
    <fieldset className="stack impact" data-testid="impact">
      <legend>{tr("impact.title")}</legend>
      <div className="row">
        {IMPACTS.map((i) => (
          <button
            key={i}
            type="button"
            className={value === i ? "btn btn-primary" : "btn btn-secondary"}
            aria-pressed={value === i}
            onClick={() => onChange(value === i ? undefined : i)}
            data-testid={`impact-${i}`}
          >
            {tr(`impact.${i}` as "impact.positive")}
          </button>
        ))}
      </div>
      <p className="muted">{tr("impact.note")}</p>
    </fieldset>
  );
}

/** Things she could say, one card per move; a tap puts the line in the box so she can change it. */
export function CuePanel({ moves, onUse }: { moves: PracticeMove[]; onUse: (line: string) => void }) {
  const { tr } = useApp();
  const cued = moves.filter((m) => m.examples.length > 0);
  return (
    <div className="card" data-testid="cue-panel">
      <h2>{tr("cue.title")}</h2>
      <p className="muted">{tr("cue.tap")}</p>
      {cued.map((m) => (
        <div key={m.id} className="cue-move">
          <p>
            <strong>{m.label}</strong>
          </p>
          <ul className="plain">
            {m.examples.map((line) => (
              <li key={line}>
                <button type="button" className="btn btn-secondary cue-line" onClick={() => onUse(line)} data-testid="cue-line">
                  {line}
                </button>
              </li>
            ))}
          </ul>
        </div>
      ))}
      <h3>{tr("cue.tips_title")}</h3>
      <ul className="plain">
        {(["cue.tip1", "cue.tip2", "cue.tip3", "cue.tip4"] as const).map((k) => (
          <li key={k}>{tr(k)}</li>
        ))}
      </ul>
    </div>
  );
}

interface ReviewProps {
  onAgain: (seed: number) => void;
}

export function ReviewTab({ onAgain }: ReviewProps) {
  const { tr, lang } = useApp();
  const [rows, setRows] = useState<TranscriptRow[] | null>(null);
  const [openId, setOpenId] = useState<number | null>(null);
  const [upto, setUpto] = useState(1);

  const refresh = useCallback(async () => setRows(await listSessions()), []);
  useEffect(() => {
    void refresh();
  }, [refresh]);

  if (rows === null) return <p role="status">{tr("common.loading")}</p>;
  const when = (ms: number) => new Date(ms).toLocaleString(lang, { dateStyle: "medium", timeStyle: "short" });

  const open = rows.find((r) => r.id === openId);
  if (open?.id !== undefined) {
    const id = open.id;
    const turns = turnsOf(open);
    const shown = turns.slice(0, upto);
    const card = open.card as FeedbackCard | undefined;
    const used = moveCounts(turns);
    return (
      <section aria-labelledby="rv-detail" data-testid="review-detail">
        <button type="button" className="btn btn-secondary" onClick={() => setOpenId(null)} data-testid="review-back">
          {tr("review.back")}
        </button>
        <h2 id="rv-detail">{when(open.createdAt)}</h2>
        <p className="muted">{tr(`err.${open.scenario ?? "SUB-SFL"}` as "err.SUB-SFL")}</p>
        <h3>{tr("review.replay")}</h3>
        <div className="log" aria-live="polite" data-testid="replay">
          {shown.map((t) => (
            <div key={t.turn} className="exchange" data-testid={`replay-turn-${t.turn}`}>
              <p className="said">
                <strong>{tr("review.you")}:</strong> {t.teacher}
              </p>
              {t.move ? <p className="muted">{t.move}</p> : null}
              <p className="reply">{t.child ? <><strong>{t.speaker}</strong>: {t.child}</> : <em>{tr("practice.silent")}</em>}</p>
            </div>
          ))}
        </div>
        <p className="muted" data-testid="replay-count">
          {tr("review.turn_of", { n: shown.length, total: turns.length })}
        </p>
        <div className="row">
          <button type="button" className="btn btn-secondary" onClick={() => setUpto(Math.max(1, upto - 1))} disabled={upto <= 1} data-testid="replay-prev">
            {tr("review.prev")}
          </button>
          <button type="button" className="btn btn-primary" onClick={() => setUpto(Math.min(turns.length, upto + 1))} disabled={upto >= turns.length} data-testid="replay-next">
            {tr("review.next")}
          </button>
        </div>
        {used.length > 0 ? (
          <>
            <h3>{tr("review.moves_used")}</h3>
            <ul className="plain" data-testid="moves-used">
              {used.map(([move, n]) => (
                <li key={move}>
                  {move} · {n}
                </li>
              ))}
            </ul>
          </>
        ) : null}
        {card ? (
          <>
            <h3>{tr("review.feedback")}</h3>
            <ul className="plain" data-testid="review-feedback">
              {card.strengths.map((s) => (
                <li key={s.turn_id + s.quote}>{s.comment}</li>
              ))}
              <li>{card.try_next.suggestion}</li>
            </ul>
          </>
        ) : null}
        <ImpactPicker
          value={open.impact}
          onChange={(v) => {
            void setImpact(id, v).then(refresh);
          }}
        />
        <button type="button" className="btn btn-primary" onClick={() => open.seed !== undefined && onAgain(open.seed)} disabled={open.seed === undefined} data-testid="review-again">
          {tr("review.again")}
        </button>
        <button
          type="button"
          className="btn btn-secondary"
          data-testid="review-delete"
          onClick={() => {
            if (!window.confirm(tr("review.delete_confirm"))) return;
            void deleteSession(id).then(() => {
              setOpenId(null);
              return refresh();
            });
          }}
        >
          {tr("review.delete")}
        </button>
      </section>
    );
  }

  const c = impactCounts(rows);
  return (
    <section aria-labelledby="rv-title" data-testid="review-list">
      <h2 id="rv-title">{tr("review.title")}</h2>
      <p className="muted">{tr("review.private")}</p>
      {rows.length === 0 ? (
        <p data-testid="review-empty">{tr("review.empty")}</p>
      ) : (
        <>
          <p data-testid="review-summary">{tr("review.summary", { n: rows.length, a: c.positive, b: c.none, c: c.negative, d: c.untagged })}</p>
          <ul className="plain">
            {rows.map((r) => (
              <li key={r.id}>
                <button
                  type="button"
                  className="btn btn-secondary review-item"
                  onClick={() => {
                    setUpto(1);
                    setOpenId(r.id ?? null);
                  }}
                  data-testid="review-item"
                >
                  <span>{when(r.createdAt)}</span>
                  <span className="muted">
                    {tr(`err.${r.scenario ?? "SUB-SFL"}` as "err.SUB-SFL")} · {tr("review.turns", { n: turnsOf(r).length })}
                  </span>
                  <span className={r.impact ? `chip chip-${r.impact}` : "chip"} data-testid="review-impact">
                    {r.impact ? tr(`impact.${r.impact}` as "impact.positive") : tr("impact.untagged")}
                  </span>
                </button>
              </li>
            ))}
          </ul>
          <button
            type="button"
            className="btn btn-secondary"
            data-testid="review-delete-all"
            onClick={() => {
              if (window.confirm(tr("review.delete_all_confirm"))) void deleteAllSessions().then(refresh);
            }}
          >
            {tr("review.delete_all")}
          </button>
        </>
      )}
    </section>
  );
}
