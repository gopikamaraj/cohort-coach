// T5: the Practice Class. Five pretend children make her own class's mistakes; she teaches in
// text; a private feedback card follows. The transcript is kept on this phone only. Judges can
// turn on a panel that shows the five AI layers of each turn.
import { track } from "../lib/tester";
import { useCallback, useEffect, useRef, useState } from "react";
import { BlockBoard, ChildrenRow, FeedbackView, LayersPanel, Materials, SpriteSpec } from "../components/practice";
import { CuePanel, ImpactPicker, PracticeTabs, ReviewTab, type PracticeTab } from "../components/review";
import { Icon } from "../components/icons";
import { getConsent, setConsent, recordOnServer, type Choices } from "../lib/consent";
import { useConsent } from "../lib/useConsent";
import { sendFeedback } from "../lib/feedback";
import { setImpact, type Impact } from "../lib/review";
import { AiOffNote, RecordedChip, SimulatedBanner } from "../components/parts";
import { db, getSetting, setSetting } from "../lib/db";
import {
  appendTurn,
  createSession,
  endSession,
  finishTranscript,
  PracticeError,
  postTurn,
  scenarioFor,
  simpleReplyReason,
  startTranscript,
  type CreatedSession,
  type FeedbackCard,
  type Layers,
  type TurnResponse,
} from "../lib/practice";
import { useQuery } from "../lib/router";
import { useJudge } from "../lib/roles";
import { fetchHints } from "../lib/breakit";
import { Meters } from "../components/meters";
import { BreakIt } from "../components/breakit";
import type { ChildMeter } from "../lib/watch";
import {
  canRecord,
  MAX_RECORD_MS,
  MAX_VOICE_FAILURES,
  playReply,
  postVoiceTurn,
  recorderMime,
  slowLink,
  voiceDefault,
  VOICE_PREF_KEY,
  type VoiceState,
  type VoiceTurn,
} from "../lib/voice";
import { useApp } from "../state";

type Phase = "intro" | "starting" | "playing" | "ending" | "feedback" | "paused" | "offline" | "error";

interface TurnView {
  n: number;
  teacher: string;
  child: string;
  speaker: string | null;
  badge: string;
  /** Why a simple reply was used, if one was: the key of the message to show. */
  why: "practice.slow" | "practice.held" | "practice.model_off" | null;
  layers: Layers;
  textEn: string;
  written: number | null;
  move: { label: string; strategy: boolean; quality: string } | null;
  meters: ChildMeter[];
  /** Other children who spoke in the same turn. */
  others: { speaker: string; child: string; textEn: string; written: number | null }[];
  /** When the reply arrived (this phone's clock). */
  at: number;
}

interface Sample {
  turns: { turn: number; teacher: string; speaker: string | null; child: string }[];
  feedback: { strengths: { comment: string; quote: string }[]; try_next: { suggestion: string } };
}

export default function Practice() {
  const { tr, lang, role, klass, profile, online } = useApp();
  const judgeMode = useJudge();
  const query = useQuery();
  const [phase, setPhase] = useState<Phase>("intro");
  const [session, setSession] = useState<CreatedSession | null>(null);
  const [turns, setTurns] = useState<TurnView[]>([]);
  const [speakers, setSpeakers] = useState<string[]>([]);
  const [faces, setFaces] = useState<Record<string, string>>({});
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
  const consent = useConsent();
  const [tab, setTab] = useState<PracticeTab>("practise");
  const [cueOpen, setCueOpen] = useState(false);
  const says = useRef<HTMLDivElement>(null);
  const [side, setSide] = useState<"turn" | "coach" | "judge">("turn");
  const [impact, setImpactState] = useState<Impact | undefined>(undefined);
  const [voiceOn, setVoiceOn] = useState(false);
  const [hintsOn, setHintsOn] = useState(false);
  const [hintList, setHintList] = useState<{ move: string; line: string }[]>([]);
  const [voiceFails, setVoiceFails] = useState(0);
  const [vstate, setVstate] = useState<VoiceState>("idle");
  const rowId = useRef<number | null>(null);
  const holding = useRef(false);
  const rec = useRef<{ mr: MediaRecorder; at: number; timer: number } | null>(null);
  const log = useRef<HTMLDivElement>(null);

  useEffect(() => {
    void getSetting("shareSessions", false).then(setShare);
  }, []);
  useEffect(
    () => () => {
      // leaving the screen while the button is held must not leave the microphone on
      holding.current = false;
      const r = rec.current;
      if (r) {
        clearTimeout(r.timer);
        r.mr.stream.getTracks().forEach((x) => x.stop());
        if (r.mr.state === "recording") r.mr.stop();
      }
    },
    [],
  );
  useEffect(() => {
    // Keep the newest reply in view without moving the page when it already is: "nearest" scrolls
    // only if the card is off screen (a phone), never to the end of the page.
    if (turns.length > 0) says.current?.scrollIntoView({ block: "nearest" });
  }, [turns.length]);

  const fail = useCallback((e: unknown) => {
    const kind = e instanceof PracticeError ? e.kind : "other";
    track("error_shown", { value: { code: `practice_${kind}` } });
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
    setSpeakers([]);
    setCard(null);
    setOver(null);
    setRating({});
    setFlagged(false);
    setImpactState(undefined);
    setCueOpen(false);
    const urlSeed = query.get("seed");
    try {
      const created = await createSession({
        scenario: scenarioFor(profile?.track ?? null),
        language: lang,
        judge: judgeMode,
        ...(profile ? { counts: profile.counts, checked: profile.childrenChecked } : {}),
        ...(seed !== undefined ? { seed } : urlSeed ? { seed: Number(urlSeed) } : {}),
      });
      setSession(created);
      setFaces({});
      setVoiceFails(0);
      setVoiceOn(voiceDefault(created.voice.available, canRecord(), slowLink(), localStorage.getItem(VOICE_PREF_KEY)));
      rowId.current = await startTranscript(created.session_id, klass?.id ?? "none", scenarioFor(profile?.track ?? null), undefined, {
        language: created.language,
        seed: created.seed,
      });
      setPhase("playing");
    } catch (e) {
      fail(e);
    }
  };

  const applyTurn = async (r: TurnResponse, shown: string) => {
    const why = simpleReplyReason(r.layers.guardrails.fallback_used, r.layers.output.source);
    setTurns((prev) => [...prev, { n: r.turn, teacher: shown, child: r.child_text, speaker: r.speaker, badge: r.badge, why, layers: r.layers, textEn: r.child_text_en ?? "", written: r.written ?? null, move: r.move ?? null, meters: r.children ?? [], others: (r.others ?? []).map((o) => ({ speaker: o.speaker, child: o.child_text, textEn: o.child_text_en, written: o.written })), at: Date.now() }]);
    setSpeakers([...(r.speaker ? [r.speaker] : []), ...(r.others ?? []).map((o) => o.speaker)]);
    setFaces(Object.fromEntries((r.children ?? []).map((c) => [c.name, c.expression])));
    const moveId = r.layers.processing.label.move_id;
    const move = session?.moves.find((m) => m.id === moveId)?.label;
    if (rowId.current !== null) await appendTurn(rowId.current, { turn: r.turn, teacher: shown, child: r.child_text, speaker: r.speaker, ...(move ? { move } : {}) });
    if (r.finished) setOver(r.finished_reason === "all_correct" ? "practice.over_all" : "practice.over_cap");
  };

  const doVoice = async (clip: Blob) => {
    if (!session) return;
    setBusy(true);
    setVstate("thinking");
    setNotice("");
    try {
      const r: VoiceTurn = await postVoiceTurn(session.session_id, clip);
      setVoiceFails(0);
      await applyTurn(r, r.heard);
      if (r.audio && r.audio_mime) {
        setVstate("speaking");
        await playReply(r.audio, r.audio_mime);
      }
      for (const o of r.others ?? []) if (o.audio && o.audio_mime) await playReply(o.audio, o.audio_mime); // the others, one after another
    } catch (e) {
      if (e instanceof PracticeError && e.kind === "voice") {
        const n = voiceFails + 1;
        setVoiceFails(n);
        setNotice(n >= MAX_VOICE_FAILURES ? "practice.voice_fallback" : "practice.error");
        if (n >= MAX_VOICE_FAILURES) setVoiceOn(false); // typing takes over by itself
      } else if (e instanceof PracticeError && e.kind === "unheard") setNotice("practice.unheard");
      else if (e instanceof PracticeError && (e.kind === "finished" || e.kind === "invalid")) setNotice("practice.error");
      else fail(e);
    } finally {
      setBusy(false);
      setVstate("idle");
    }
  };

  function stopRec() {
    holding.current = false;
    const r = rec.current;
    if (!r) return;
    clearTimeout(r.timer);
    if (r.mr.state === "recording") {
      setVstate("thinking");
      r.mr.stop();
    }
  }

  const startRec = async () => {
    if (!session || busy || over !== null || holding.current) return;
    holding.current = true;
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      holding.current = false;
      setNotice("practice.mic_denied");
      setVoiceOn(false);
      return;
    }
    if (!holding.current) {
      stream.getTracks().forEach((x) => x.stop()); // she let go before the phone asked
      return;
    }
    const mime = recorderMime();
    let mr: MediaRecorder;
    try {
      mr = new MediaRecorder(stream, mime ? { mimeType: mime, audioBitsPerSecond: 24000 } : undefined);
    } catch {
      stream.getTracks().forEach((x) => x.stop());
      holding.current = false;
      setNotice("practice.voice_fallback");
      setVoiceOn(false);
      return;
    }
    mr.onerror = () => {
      stream.getTracks().forEach((x) => x.stop());
      holding.current = false;
      setVstate("idle");
    };
    const chunks: Blob[] = [];
    mr.ondataavailable = (e) => {
      if (e.data.size > 0) chunks.push(e.data);
    };
    mr.onstop = () => {
      stream.getTracks().forEach((x) => x.stop());
      const held = Date.now() - (rec.current?.at ?? 0);
      rec.current = null;
      if (held < 400 || chunks.length === 0) {
        setVstate("idle");
        setNotice("practice.unheard");
        return;
      }
      void doVoice(new Blob(chunks, { type: mr.mimeType }));
    };
    rec.current = { mr, at: Date.now(), timer: window.setTimeout(stopRec, MAX_RECORD_MS) };
    mr.start();
    setVstate("listening");
  };

  const useText = () => {
    localStorage.setItem(VOICE_PREF_KEY, "0");
    track("feature_used", { feature_id: "voice_toggle", value: { on: false } });
    setVoiceOn(false);
  };
  const useVoice = () => {
    localStorage.setItem(VOICE_PREF_KEY, "1");
    track("feature_used", { feature_id: "voice_toggle", value: { on: true } });
    setVoiceFails(0);
    setNotice("");
    setVoiceOn(true);
  };

  const doTurn = async (body: { text?: string; material?: string }, shown: string) => {
    if (!session || busy) return;
    setBusy(true);
    setNotice("");
    try {
      await applyTurn(await postTurn(session.session_id, body), shown);
      track("feature_used", { feature_id: "practice_turn" });
      setText("");
    } catch (e) {
      if (e instanceof PracticeError && (e.kind === "finished" || e.kind === "invalid")) setNotice("practice.error");
      else fail(e);
    } finally {
      setBusy(false);
    }
  };

  // Try with hints (judge mode): three replies for the next turn, built by the server from the move list.
  useEffect(() => {
    if (!judgeMode || !hintsOn || !session || over !== null || phase !== "playing") {
      setHintList([]);
      return;
    }
    let live = true;
    void fetchHints(session.session_id).then((h) => live && setHintList(h));
    return () => {
      live = false;
    };
  }, [judgeMode, hintsOn, session, turns.length, over, phase]);

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
    if (!consent?.feedback) {
      setNotice("feedback.need_consent");
      return;
    }
    setFlagged(true);
    void sendFeedback({ kind: "card_flag", language: lang, role, context: "practice" }, online);
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
  const tabs = <PracticeTabs tab={tab} onTab={setTab} />;

  if (tab === "review") {
    return (
      <section aria-labelledby="pr-title">
        <h1 id="pr-title">{tr("practice.title")}</h1>
        {tabs}
        <ReviewTab
          onAgain={(seed) => {
            setTab("practise");
            void start(seed);
          }}
        />
      </section>
    );
  }

  if (phase === "intro" || phase === "starting") {
    return (
      <section aria-labelledby="pr-title">
        <h1 id="pr-title">{tr("practice.title")}</h1>
        {tabs}
        {banner}
        {query.get("next") ? (
          <p className="card" role="status" data-testid="practice-next">
            {tr("practice.next_from_lesson")}
          </p>
        ) : null}
        <p>{tr("practice.intro")}</p>
        <p data-testid="goal-intro">{tr("practice.goal_line", { error: tr(`err.desc.${scenarioFor(profile?.track ?? null)}` as "err.desc.SUB-SFL") })}</p>
        {consent?.practice_ai ? null : (
          <div className="panel notice-card" data-testid="practice-consent">
            <h2>
              <Icon name="shield" /> <span>{tr("practice.consent_title")}</span>
            </h2>
            <p>{tr("practice.consent_body")}</p>
          </div>
        )}
        <button
          type="button"
          className="btn btn-primary btn-with-icon"
          onClick={() => {
            if (!consent?.practice_ai) {
              const before = getConsent();
              const base: Choices = { core: true, counts: false, practice_ai: false, share_rehearsal: false, feedback: false, ...(before ?? {}) };
              void recordOnServer(before, setConsent({ ...base, core: true, practice_ai: true }));
            }
            void start();
          }}
          disabled={phase === "starting"}
          data-testid="start-practice"
        >
          <Icon name="practice" /> <span>{phase === "starting" ? tr("practice.starting") : consent?.practice_ai ? tr("practice.start") : tr("practice.consent_allow")}</span>
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
        {tabs}
        {banner}
        <FeedbackView card={card} rating={rating} onRate={rate} onFlag={flag} flagged={flagged} />
        <ImpactPicker
          value={impact}
          onChange={(v) => {
            setImpactState(v);
            if (rowId.current !== null) void setImpact(rowId.current, v);
          }}
        />
        <p className="muted">{tr("practice.saved")}</p>
        <button type="button" className="btn btn-primary" onClick={() => void start(session?.seed)} data-testid="retry">
          {tr("practice.retry")}
        </button>
      </section>
    );
  }

  const last = turns[turns.length - 1];
  const lastSaid = [...turns].reverse().find((t) => t.child);
  const posed = [...turns].reverse().map((t) => t.layers.processing.posed_problem).find((p) => p !== null && p !== undefined);
  const meters = last?.meters ?? [];
  const following = meters.filter((c) => !c.has_error || c.band === "low").length;

  return (
    <section aria-labelledby="pr-title" className="pcx">
      <h1 id="pr-title">{tr("practice.title")}</h1>
      {tabs}
      {banner}
      {session ? (
        <div className="pcx-cols">
          <div className="pcx-col">
            <section className="pcx-card pcx-scenario" aria-labelledby="pcx-goal" data-testid="goal">
              <Icon name="bulb" />
              <div>
                <h2 id="pcx-goal" className="pcx-meta">{tr("practice.goal_title")}</h2>
                <p>{tr("practice.goal_line", { error: tr(`err.desc.${session.goal.error}` as "err.desc.SUB-SFL") })}</p>
                <ul className="plain pcx-tips">
                  {session.goal.tips.map((tip) => (
                    <li key={tip}>{tip}</li>
                  ))}
                </ul>
              </div>
            </section>

            <section className="pcx-card" aria-labelledby="pcx-class">
              <h2 id="pcx-class">{tr("practice.class_title")}</h2>
              <p className="pcx-hint">{tr("practice.class_hint")}</p>
              <AiOffNote text={tr("ai.off.practice")} testId="practice-ai-off" />
              <div data-testid="pc-top">
                <ChildrenRow children={session.children} speakers={speakers} faces={faces} />
                <p className="muted pc-count" data-testid="turn-counter">
                  {tr("practice.turn", { n: turns.length, cap })}
                </p>
              </div>
              {lastSaid ? (
                <div className="pcx-says" role="status" data-testid="says" ref={says}>
                  <Icon name="chat" />
                  <div>
                    <b>{tr("practice.says", { name: lastSaid.speaker ?? "" })}</b>
                    <span>{lastSaid.child}</span>
                  </div>
                </div>
              ) : null}
        <div className="log" ref={log} aria-live="polite" data-testid="log">
          {busy ? <p className="muted" role="status">{tr("practice.sending")}</p> : null}
          {/* newest first, so the latest reply is at the top without scrolling */}
          {[...turns].reverse().map((t) => (
            <div key={t.n} className="exchange" data-testid={`turn-${t.n}`}>
              <time className="turn-time" dateTime={new Date(t.at).toISOString()} data-testid={`turn-time-${t.n}`}>
                {new Date(t.at).toLocaleTimeString(lang, { hour: "numeric", minute: "2-digit", second: "2-digit" })}
              </time>
              <p className="said">{t.teacher}</p>
              <p className="reply" data-testid={`reply-${t.n}`}>
                {t.child ? (
                  <>
                    <strong>{t.speaker}</strong>: {t.child} {t.badge !== "none" ? <span className="tick" aria-label={tr("practice.checked")}>✓</span> : null}
                    {t.layers.output.source === "ai" ? <> <RecordedChip testId={`recorded-${t.n}`} /></> : null}
                  </>
                ) : (
                  <em>{tr("practice.silent")}</em>
                )}
              </p>
              {t.others.map((o, i) => (
                <p className="reply" key={`${t.n}-${i}`} data-testid={`other-${t.n}-${i}`}>
                  <strong>{o.speaker}</strong>: {o.child}
                  {judgeMode && o.textEn && lang !== "en" ? <span className="muted"> ({o.textEn})</span> : null}
                </p>
              ))}
              {t.why ? <p className="muted" role="status">{tr(t.why)}</p> : null}
              {t.child && t.written !== null ? (
                <p className="slate" data-testid={`slate-${t.n}`}>
                  {tr("practice.slate", { who: t.speaker ?? "", n: t.written })}
                </p>
              ) : null}
              {judgeMode && t.child && t.textEn && lang !== "en" ? (
                <p className="muted" data-testid={`subtitle-${t.n}`}>
                  {tr("watch.subtitle")}: {t.textEn}
                </p>
              ) : null}
              {judgeMode && t.move ? (
                <p className="muted" data-testid={`move-tag-${t.n}`}>
                  {tr("watch.move", { move: t.move.label })}
                  {t.move.strategy ? `, ${tr("watch.strategy")}` : ""}
                  {t.move.quality === "common_mistake" ? `, ${tr("watch.mistake")}` : ""}
                </p>
              ) : null}
            </div>
          ))}
        </div>
            </section>

            {posed && (posed.kind === "sub" || posed.kind === "add") ? <BlockBoard a={posed.a} b={posed.b} kind={posed.kind} /> : null}
          </div>

          <div className="pcx-col">
            <section className="pcx-card pcx-side">
              <div className="pcx-tabs" role="tablist" aria-label={tr("practice.side_tabs")}>
                {(judgeMode ? (["turn", "coach", "judge"] as const) : (["turn", "coach"] as const)).map((k) => (
                  <button key={k} type="button" role="tab" id={`side-${k}`} aria-selected={side === k} aria-controls={`side-panel-${k}`} className={side === k ? "pcx-tab pcx-tab-on" : "pcx-tab"} onClick={() => setSide(k)} data-testid={`side-${k}`}>
                    {tr(k === "turn" ? "practice.your_turn" : k === "coach" ? "practice.coaching" : "practice.judge_title")}
                  </button>
                ))}
              </div>
            <div role="tabpanel" id="side-panel-turn" aria-labelledby="side-turn" hidden={side !== "turn"}>
              <h2 id="pcx-turn">{tr("practice.your_turn")}</h2>
              <p className="pcx-hint">{tr("practice.your_turn_hint")}</p>
        {voiceOn ? (
          <>
            <div className="compose compose-dock pcx-mic" data-state={vstate}>
              <span className="pcx-bars" aria-hidden="true"><i /><i /><i /><i /></span>
              <button
                type="button"
                className="btn btn-primary btn-talk"
                data-testid="talk"
                data-state={vstate}
                aria-label={tr("practice.voice_label")}
                disabled={over !== null || vstate === "thinking" || vstate === "speaking"}
                onPointerDown={() => void startRec()}
                onPointerUp={stopRec}
                onPointerCancel={stopRec}
                onPointerLeave={stopRec}
                onKeyDown={(e) => {
                  if ((e.key === " " || e.key === "Enter") && !e.repeat) {
                    e.preventDefault();
                    void startRec();
                  }
                }}
                onKeyUp={(e) => {
                  if (e.key === " " || e.key === "Enter") stopRec();
                }}
                onContextMenu={(e) => e.preventDefault()}
              >
                {vstate === "listening" ? tr("practice.talk_release") : vstate === "thinking" ? tr("practice.sending") : vstate === "speaking" ? tr("practice.speaking") : tr("practice.talk")}
              </button>
              <span className="pcx-bars" aria-hidden="true"><i /><i /><i /><i /></span>
              {session?.voice.mode === "stub" ? (
                <p className="muted" data-testid="voice-stub">
                  {tr("practice.voice_stub")}
                </p>
              ) : null}
              <p className="muted" role="status" data-testid="voice-state">
                {vstate === "listening" ? tr("practice.listening") : ""}
              </p>
            </div>
            <button type="button" className="btn btn-secondary" onClick={useText} data-testid="use-text">
              {tr("practice.use_text")}
            </button>
          </>
        ) : (
          <>
            {hintsOn && hintList.length > 0 ? (
              <div className="stack" data-testid="hints">
                <p className="muted">{tr("hints.intro")}</p>
                {hintList.map((h) => (
                  <button key={h.move} type="button" className="btn btn-secondary" disabled={busy || over !== null} onClick={() => void doTurn({ text: h.line }, h.line)} data-testid={`hint-${h.move}`}>
                    {h.line}
                  </button>
                ))}
              </div>
            ) : null}
            <form
              className="compose compose-dock"
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
            {canRecord() ? (
              <button type="button" className="btn btn-secondary" onClick={useVoice} data-testid="use-voice">
                {tr("practice.use_voice")}
              </button>
            ) : null}
          </>
        )}
              {notice ? <p role="alert">{tr(notice as "practice.error")}</p> : null}
              {over ? <p role="status" data-testid="over">{tr(over as "practice.over_all")}</p> : null}
              <div className="pcx-cue">
        <>
            <button type="button" className="btn btn-secondary btn-with-icon" onClick={() => setCueOpen(!cueOpen)} aria-expanded={cueOpen} data-testid="cue-toggle">
              <Icon name="bulb" /> <span>{cueOpen ? tr("cue.hide") : tr("cue.button")}</span>
            </button>
            {cueOpen ? (
              <CuePanel
                moves={session.moves}
                onUse={(line) => {
                  setVoiceOn(false); // she will type or edit the line
                  setText(line);
                  setCueOpen(false);
                }}
              />
            ) : null}
        </>
              </div>
              <div className="pcx-moves">
                <p className="pcx-label">{tr("practice.quick_moves")}</p>
                <Materials items={session.materials} itemFor={session.material_items} disabled={busy || over !== null} onTap={tap} />
              </div>
        <button type="button" className="btn btn-secondary pc-end" onClick={() => void end()} disabled={busy || turns.length === 0 || phase === "ending"} data-testid="end">
          {tr("practice.end")}
        </button>
            </div>

            <div role="tabpanel" id="side-panel-coach" aria-labelledby="side-coach" hidden={side !== "coach"} data-testid="coaching">
              <h2 id="pcx-coach">{tr("practice.coaching")}</h2>
              <p className="pcx-hint">{tr("practice.coaching_hint")}</p>
              {last?.why ? (
                <div className="pcx-fb pcx-fb-watch">
                  <Icon name="info" />
                  <div>{tr(last.why)}</div>
                </div>
              ) : null}
              {judgeMode && last?.move ? (
                <div className="pcx-fb pcx-fb-good">
                  <Icon name="ok" />
                  <div>{tr("watch.move", { move: last.move.label })}</div>
                </div>
              ) : null}
              {!last?.why && !(judgeMode && last?.move) ? <p className="muted">{tr("practice.coach_none")}</p> : null}
              {meters.length > 0 ? (
                <>
                  <div className="pcx-meterhead">
                    <span>{tr("practice.following")}</span>
                    <span>{tr("practice.following_n", { n: following, total: meters.length })}</span>
                  </div>
                  <div className="pcx-meter" role="progressbar" aria-valuemin={0} aria-valuemax={meters.length} aria-valuenow={following} aria-label={tr("practice.following")}>
                    <i style={{ width: `${(following / meters.length) * 100}%` }} />
                  </div>
                </>
              ) : null}
              <p className="pcx-privacy">
                <Icon name="shield" size={20} /> <span>{tr("practice.private_line")}</span>
              </p>
            </div>

            {judgeMode ? (
              <div role="tabpanel" id="side-panel-judge" aria-labelledby="side-judge" hidden={side !== "judge"} data-testid="judge-panel">
                <div className="pcx-judgehead">
                  <h2 id="pcx-judge">{tr("practice.judge_title")}</h2>
                  <label className="check">
                    <input type="checkbox" checked={showLayers} onChange={toggleLayers} data-testid="layers-toggle" />
                    <span>{tr("layers.show")}</span>
                  </label>
                </div>
          <label className="check">
            <input type="checkbox" checked={hintsOn} onChange={(e) => setHintsOn(e.target.checked)} data-testid="hints-toggle" />
            <span>{tr("hints.toggle")}</span>
          </label>
          <p className="muted">{tr("layers.judge_only")}</p>
          {turns.length > 0 ? (
            <details className="pcx-trace" open data-testid="judge-trace">
              <summary>{tr("practice.trace", { n: turns.length })}</summary>
              <div className="pcx-trace-body">
                {turns.map((t) => (
                  <div key={t.n} data-testid={`trace-${t.n}`}>
                    <h3>{tr("practice.turn_n", { n: t.n })}</h3>
                    {t.meters.length > 0 ? <Meters children={t.meters} /> : null}
                    {showLayers ? (
                      <>
                        <LayersPanel layers={t.layers} />
                        <SpriteSpec child={t.meters.find((c) => c.speaking)} />
                      </>
                    ) : null}
                  </div>
                ))}
              </div>
            </details>
          ) : null}
          <BreakIt />
              </div>
            ) : null}
            </section>
          </div>
        </div>
      ) : null}
    </section>
  );
}
