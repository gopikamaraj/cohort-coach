// T5: the Practice Class. Five pretend children make her own class's mistakes; she teaches in
// text; a private feedback card follows. The transcript is kept on this phone only. Judges can
// turn on a panel that shows the five AI layers of each turn.
import { useCallback, useEffect, useRef, useState } from "react";
import { ChildrenRow, FeedbackView, LayersPanel, Materials } from "../components/practice";
import { SimulatedBanner } from "../components/parts";
import { db, getSetting, setSetting } from "../lib/db";
import {
  appendTurn,
  createSession,
  endSession,
  finishTranscript,
  PracticeError,
  postTurn,
  scenarioFor,
  startTranscript,
  type CreatedSession,
  type FeedbackCard,
  type Layers,
} from "../lib/practice";
import { useQuery } from "../lib/router";
import { useApp } from "../state";

type Phase = "intro" | "starting" | "playing" | "ending" | "feedback" | "paused" | "offline" | "error";

interface TurnView {
  n: number;
  teacher: string;
  child: string;
  speaker: string | null;
  badge: string;
  slow: boolean;
  layers: Layers;
}

interface Sample {
  turns: { turn: number; teacher: string; speaker: string | null; child: string }[];
  feedback: { strengths: { comment: string; quote: string }[]; try_next: { suggestion: string } };
}

export default function Practice() {
  const { tr, role, klass, profile, online } = useApp();
  const query = useQuery();
  const [phase, setPhase] = useState<Phase>("intro");
  const [session, setSession] = useState<CreatedSession | null>(null);
  const [turns, setTurns] = useState<TurnView[]>([]);
  const [speaker, setSpeaker] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [over, setOver] = useState<string | null>(null);
  const [card, setCard] = useState<FeedbackCard | null>(null);
  const [rating, setRating] = useState<Record<string, "up" | "down">>({});
  const [flagged, setFlagged] = useState(false);
  const [share, setShare] = useState(false);
  const [showLayers, setShowLayers] = useState(() => localStorage.getItem("cc.layers") === "1");
  const [sample, setSample] = useState<Sample | null>(null);
  const rowId = useRef<number | null>(null);
  const log = useRef<HTMLDivElement>(null);

  useEffect(() => {
    void getSetting("shareSessions", false).then(setShare);
  }, []);
  useEffect(() => {
    log.current?.scrollTo({ top: log.current.scrollHeight });
  }, [turns]);

  const fail = useCallback((e: unknown) => {
    const kind = e instanceof PracticeError ? e.kind : "other";
    setPhase(kind === "paused" ? "paused" : kind === "offline" ? "offline" : "error");
    setNotice(kind === "expired" ? "practice.expired" : "practice.error");
  }, []);

  const start = async (seed?: number) => {
    if (!online) {
      setPhase("offline");
      return;
    }
    setPhase("starting");
    setTurns([]);
    setSpeaker(null);
    setCard(null);
    setOver(null);
    setRating({});
    setFlagged(false);
    const urlSeed = query.get("seed");
    try {
      const created = await createSession({
        scenario: scenarioFor(profile?.track ?? null),
        language: localStorage.getItem("cc.lang") ?? "en",
        judge: role === "judge",
        ...(profile ? { counts: profile.counts, checked: profile.childrenChecked } : {}),
        ...(seed !== undefined ? { seed } : urlSeed ? { seed: Number(urlSeed) } : {}),
      });
      setSession(created);
      rowId.current = await startTranscript(created.session_id, klass?.id ?? "none", scenarioFor(profile?.track ?? null));
      setPhase("playing");
    } catch (e) {
      fail(e);
    }
  };

  const doTurn = async (body: { text?: string; material?: string }, shown: string) => {
    if (!session || busy) return;
    setBusy(true);
    setNotice("");
    try {
      const r = await postTurn(session.session_id, body);
      const slow = Boolean(r.layers.guardrails.fallback_used) || r.layers.output.source === "template";
      setTurns((prev) => [...prev, { n: r.turn, teacher: shown, child: r.child_text, speaker: r.speaker, badge: r.badge, slow, layers: r.layers }]);
      setSpeaker(r.speaker);
      if (rowId.current !== null) await appendTurn(rowId.current, { turn: r.turn, teacher: shown, child: r.child_text, speaker: r.speaker });
      if (r.finished) setOver(r.finished_reason === "all_correct" ? "practice.over_all" : "practice.over_cap");
      setText("");
    } catch (e) {
      if (e instanceof PracticeError && (e.kind === "finished" || e.kind === "invalid")) setNotice("practice.error");
      else fail(e);
    } finally {
      setBusy(false);
    }
  };

  const send = () => {
    const line = text.trim();
    if (line) void doTurn({ text: line }, line);
  };
  const tap = (m: string) => {
    const names: Record<string, string> = { bundles: tr("practice.bundles"), sticks: tr("practice.sticks"), chart: tr("practice.chart") };
    void doTurn({ material: m }, tr("practice.tapped", { material: names[m] ?? m }));
  };

  const end = async () => {
    if (!session) return;
    setPhase("ending");
    try {
      const r = await endSession(session.session_id);
      setCard(r.card);
      if (rowId.current !== null) await finishTranscript(rowId.current, r.card);
      setPhase("feedback");
    } catch (e) {
      fail(e);
    }
  };

  const rate = (id: string, value: "up" | "down") => {
    const next = { ...rating, [id]: value };
    setRating(next);
    if (rowId.current !== null) void db.transcripts.update(rowId.current, { ratings: next });
  };
  const flag = () => {
    setFlagged(true);
    void db.syncQueue.add({ kind: "flag", classId: klass?.id ?? "none", payload: { card: "practice", term: profile?.term ?? 1 }, createdAt: Date.now(), tries: 0 });
  };
  const toggleLayers = () => {
    const next = !showLayers;
    setShowLayers(next);
    localStorage.setItem("cc.layers", next ? "1" : "0");
  };
  const loadSample = async () => {
    try {
      setSample((await (await fetch("/sample-practice.json")).json()) as Sample);
    } catch {
      setNotice("practice.error");
    }
  };

  const banner = klass?.simulated ? <SimulatedBanner /> : null;
  const cap = session?.turn_cap ?? 40;

  if (phase === "intro" || phase === "starting") {
    return (
      <section aria-labelledby="pr-title">
        <h1 id="pr-title">{tr("practice.title")}</h1>
        {banner}
        <p>{tr("practice.intro")}</p>
        <button type="button" className="btn btn-primary" onClick={() => void start()} disabled={phase === "starting"} data-testid="start-practice">
          {phase === "starting" ? tr("practice.starting") : tr("practice.start")}
        </button>
        <label className="check">
          <input
            type="checkbox"
            checked={share}
            onChange={(e) => {
              setShare(e.target.checked);
              void setSetting("shareSessions", e.target.checked);
            }}
          />
          <span>{tr("practice.share")}</span>
        </label>
        <p className="muted">{tr("practice.share_note")}</p>
      </section>
    );
  }

  if (phase === "paused" || phase === "offline" || phase === "error") {
    return (
      <section aria-labelledby="pr-title">
        <h1 id="pr-title">{tr("practice.title")}</h1>
        {banner}
        <p role="alert" data-testid="practice-state">
          {phase === "paused" ? tr("practice.paused") : phase === "offline" ? tr("practice.offline") : tr((notice || "practice.error") as "practice.error")}
        </p>
        {phase === "paused" ? (
          <>
            <p>{tr("practice.paused_hint")}</p>
            <button type="button" className="btn btn-primary" onClick={() => void loadSample()} data-testid="watch-sample">
              {tr("practice.sample")}
            </button>
            {sample ? (
              <div className="card" data-testid="sample">
                <p className="muted">{tr("practice.sample_note")}</p>
                <ul className="plain">
                  {sample.turns.map((t) => (
                    <li key={t.turn}>
                      <p>{t.teacher}</p>
                      <p className="reply">
                        <strong>{t.speaker}</strong>: {t.child}
                      </p>
                    </li>
                  ))}
                </ul>
                {sample.feedback.strengths.map((s) => (
                  <p key={s.quote}>{s.comment}</p>
                ))}
                <p>{sample.feedback.try_next.suggestion}</p>
              </div>
            ) : null}
          </>
        ) : (
          <button type="button" className="btn btn-primary" onClick={() => setPhase(session ? "playing" : "intro")}>
            {tr("common.back")}
          </button>
        )}
      </section>
    );
  }

  if (phase === "feedback" && card) {
    return (
      <section aria-labelledby="pr-title">
        <h1 id="pr-title">{tr("practice.title")}</h1>
        {banner}
        <FeedbackView card={card} rating={rating} onRate={rate} onFlag={flag} flagged={flagged} />
        <p className="muted">{tr("practice.saved")}</p>
        <button type="button" className="btn btn-primary" onClick={() => void start(session?.seed)} data-testid="retry">
          {tr("practice.retry")}
        </button>
      </section>
    );
  }

  return (
    <section aria-labelledby="pr-title">
      <h1 id="pr-title">{tr("practice.title")}</h1>
      {banner}
      {session ? <ChildrenRow children={session.children} speaker={speaker} /> : null}
      <p className="muted" data-testid="turn-counter">
        {tr("practice.turn", { n: turns.length, cap })}
      </p>
      {role === "judge" ? (
        <button type="button" className="btn btn-secondary" onClick={toggleLayers} aria-pressed={showLayers} data-testid="layers-toggle">
          {showLayers ? tr("layers.hide") : tr("layers.show")}
        </button>
      ) : null}
      <div className="log" ref={log} aria-live="polite" data-testid="log">
        {turns.map((t) => (
          <div key={t.n} className="exchange" data-testid={`turn-${t.n}`}>
            <p className="said">{t.teacher}</p>
            <p className="reply" data-testid={`reply-${t.n}`}>
              {t.child ? (
                <>
                  <strong>{t.speaker}</strong>: {t.child} {t.badge !== "none" ? <span className="tick" aria-label={tr("practice.checked")}>✓</span> : null}
                </>
              ) : (
                <em>{tr("practice.silent")}</em>
              )}
            </p>
            {t.slow ? <p className="muted" role="status">{tr("practice.slow")}</p> : null}
            {role === "judge" && showLayers ? <LayersPanel layers={t.layers} /> : null}
          </div>
        ))}
        {busy ? <p className="muted" role="status">{tr("practice.sending")}</p> : null}
      </div>
      {notice ? <p role="alert">{tr(notice as "practice.error")}</p> : null}
      {over ? <p role="status" data-testid="over">{tr(over as "practice.over_all")}</p> : null}
      {session ? <Materials items={session.materials} disabled={busy || over !== null} onTap={tap} /> : null}
      <form
        className="compose"
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
      >
        <label className="sr" htmlFor="say">
          {tr("practice.placeholder")}
        </label>
        <textarea id="say" rows={2} value={text} placeholder={tr("practice.placeholder")} onChange={(e) => setText(e.target.value)} disabled={busy || over !== null} data-testid="say" />
        <button type="submit" className="btn btn-primary" disabled={busy || over !== null || text.trim() === ""} data-testid="send">
          {tr("practice.send")}
        </button>
      </form>
      <button type="button" className="btn btn-secondary" onClick={() => void end()} disabled={busy || turns.length === 0 || phase === "ending"} data-testid="end">
        {tr("practice.end")}
      </button>
    </section>
  );
}
