// The coach listens to a voiced lesson after it is published: the script is highlighted as it plays,
// each sentence shows whether it passed the round-trip check (the audio transcribed back and
// compared), and she can regenerate one sentence, regenerate the lesson, or approve it. The server
// decides who may do what; a lesson whose cohort has fewer than 5 classes is listed but hidden.
import { useCallback, useEffect, useRef, useState } from "react";
import { Icon } from "./icons";
import { qcall, QueueError, type QueueRole } from "../lib/queue";
import { sentenceAt, sizeLabel } from "../lib/lessonAudio";
import { useApp } from "../state";

interface Summary {
  sentences: number;
  checked: number;
  passed: number;
  flagged: number;
}
interface Row {
  id: string;
  track_id: string;
  language: string;
  day: number;
  revision: number;
  status: string;
  provider: string;
  summary: Summary;
  hidden: boolean;
  bytes: number;
  seconds: number;
}
interface Detail extends Row {
  voice: string;
  style?: string | null;
  sentences?: string[];
  timing?: { i: number; start: number; end: number }[];
  checks?: { i: number; cer: number | null; flagged: boolean }[];
  audio_url?: string | null;
  sentence_costs_inr?: number[];
}

const LANG_NAME: Record<string, string> = { en: "English", hi: "हिन्दी", ta: "தமிழ்" };

export function LessonAudioReview({ reader, asCoach }: { reader: QueueRole; asCoach: boolean }) {
  const { tr } = useApp();
  const [rows, setRows] = useState<Row[]>([]);
  const [open, setOpen] = useState<Detail | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ text: string; bad?: boolean } | null>(null);
  const [now, setNow] = useState<number | null>(null);
  const player = useRef<HTMLAudioElement | null>(null);

  const load = useCallback(async () => {
    try {
      setRows(await qcall<Row[]>("/lesson-audio", reader));
    } catch {
      setRows([]);
    }
  }, [reader]);
  useEffect(() => {
    void load();
  }, [load]);

  const show = async (id: string) => {
    try {
      setOpen(await qcall<Detail>(`/lesson-audio/${id}`, reader));
      setNow(null);
      setMsg(null);
    } catch {
      setMsg({ text: tr("queue.error"), bad: true });
    }
  };

  const act = async (path: string, body: unknown, done: string) => {
    if (!open) return;
    setBusy(true);
    setMsg(null);
    try {
      const next = await qcall<Detail>(`/lesson-audio/${open.id}${path}`, "coach", { method: "POST", body });
      setOpen(next);
      setMsg({ text: tr(done as "laudio.done_approve") });
      await load();
    } catch (e) {
      const status = e instanceof QueueError ? e.status : 0;
      setMsg({ text: tr(status === 503 ? "laudio.unavailable" : status === 403 ? "queue.forbidden" : "queue.error"), bad: true });
    } finally {
      setBusy(false);
    }
  };

  const verdict = (s: Summary) =>
    s.checked === 0 ? tr("laudio.unchecked") : tr("laudio.summary", { passed: s.passed, total: s.checked, flagged: s.flagged });

  return (
    <div className="panel" data-testid="lesson-audio-review">
      <h2>{tr("laudio.title")}</h2>
      <p className="muted">{tr("laudio.intro")}</p>
      {rows.length === 0 ? <p className="muted">{tr("laudio.none")}</p> : null}
      <ul className="plain">
        {rows.map((r) => (
          <li key={r.id} className="laudio-row">
            <button type="button" className="btn btn-secondary" onClick={() => void show(r.id)} data-testid={`laudio-open-${r.day}-${r.language}`}>
              {tr("laudio.row", { day: r.day, lang: LANG_NAME[r.language] ?? r.language, rev: r.revision })}
            </button>
            <span className="muted">
              {r.hidden ? tr("laudio.hidden_short") : `${tr(`laudio.status.${r.status}` as "laudio.status.approved")} · ${verdict(r.summary)}`}
            </span>
          </li>
        ))}
      </ul>

      {open ? (
        <div className="laudio-detail" data-testid="laudio-detail">
          <h3>{tr("laudio.row", { day: open.day, lang: LANG_NAME[open.language] ?? open.language, rev: open.revision })}</h3>
          {open.hidden ? (
            <p className="muted" data-testid="laudio-hidden">{tr("laudio.hidden")}</p>
          ) : (
            <>
              <p className="muted" data-testid="laudio-meta">
                {tr("laudio.meta", { provider: open.provider, voice: open.voice, size: sizeLabel(open.bytes), seconds: Math.round(open.seconds) })}
                {" · "}
                {tr("flow.ai_voice")}
              </p>
              <p data-testid="laudio-summary">{verdict(open.summary)}</p>
              {open.audio_url ? (
                <audio
                  ref={player}
                  controls
                  preload="metadata"
                  src={open.audio_url}
                  data-testid="laudio-audio"
                  style={{ width: "100%" }}
                  onTimeUpdate={() => setNow(sentenceAt(open.timing ?? [], player.current?.currentTime ?? 0))}
                  onEnded={() => setNow(null)}
                />
              ) : null}
              <ol className="laudio-sentences">
                {(open.sentences ?? []).map((s, i) => {
                  const check = open.checks?.[i];
                  return (
                    <li key={i} className={now === i ? "say say-on" : "say"} aria-current={now === i ? "true" : undefined} data-testid={`laudio-sentence-${i}`}>
                      {check?.flagged ? (
                        <span className="row-warn-icon" role="img" title={tr("laudio.flagged")} aria-label={tr("laudio.flagged")} data-testid={`laudio-flag-${i}`}>
                          <Icon name="warning" />
                        </span>
                      ) : null}
                      <span>{s}</span>
                      {asCoach ? (
                        <button type="button" className="chip-btn" disabled={busy} onClick={() => void act("/regenerate", { sentence: i }, "laudio.done_sentence")} data-testid={`laudio-regen-${i}`}>
                          {tr("laudio.regen_sentence", { cost: (open.sentence_costs_inr?.[i] ?? 0).toFixed(2) })}
                        </button>
                      ) : null}
                    </li>
                  );
                })}
              </ol>
              {asCoach ? (
                <div className="row">
                  <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => void act("/regenerate", {}, "laudio.done_lesson")} data-testid="laudio-regen-lesson">
                    {tr("laudio.regen_lesson")}
                  </button>
                  <button type="button" className="btn btn-primary" disabled={busy || open.status === "approved"} onClick={() => void act("/approve", undefined, "laudio.done_approve")} data-testid="laudio-approve">
                    {open.status === "approved" ? tr("laudio.approved") : tr("laudio.approve")}
                  </button>
                </div>
              ) : null}
              {busy ? <p className="muted" role="status">{tr("ai.working")}</p> : null}
            </>
          )}
        </div>
      ) : null}
      {msg ? (
        <p role={msg.bad ? "alert" : "status"} className={msg.bad ? "error" : "muted"} data-testid="laudio-msg">
          {msg.text}
        </p>
      ) : null}
    </div>
  );
}
