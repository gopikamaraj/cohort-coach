// T5: the Practice Class. Five pretend children make her own class's mistakes; she teaches in
// text; a private feedback card follows. The transcript is kept on this phone only. Judges can
// turn on a panel that shows the five AI layers of each turn.
import { useCallback, useEffect, useRef, useState } from "react";
import { ChildrenRow, FeedbackView, LayersPanel, Materials } from "../components/practice";
import { CuePanel, ImpactPicker, PracticeTabs, ReviewTab, type PracticeTab } from "../components/review";
import { LANG_NAMES, type Lang } from "../i18n";
import { Icon } from "../components/icons";
import { getConsent, setConsent, recordOnServer, type Choices } from "../lib/consent";
import { useConsent } from "../lib/useConsent";
import { sendFeedback } from "../lib/feedback";
import { setImpact, type Impact } from "../lib/review";
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
  slow: boolean;
  layers: Layers;
  textEn: string;
  move: { label: string; strategy: boolean; quality: string } | null;
  meters: ChildMeter[];
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
  const consent = useConsent();
  const [tab, setTab] = useState<PracticeTab>("practise");
  const [cueOpen, setCueOpen] = useState(false);
  const [goalOpen, setGoalOpen] = useState(true); // open until she says her first line, then out of the way
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
    setImpactState(undefined);
    setCueOpen(false);
    setGoalOpen(true);
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
    const slow = Boolean(r.layers.guardrails.fallback_used) || r.layers.output.source === "template";
    setTurns((prev) => [...prev, { n: r.turn, teacher: shown, child: r.child_text, speaker: r.speaker, badge: r.badge, slow, layers: r.layers, textEn: r.child_text_en ?? "", move: r.move ?? null, meters: r.children ?? [] }]);
    setSpeaker(r.speaker);
    if (r.turn === 1) setGoalOpen(false);
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
    setVoiceOn(false);
  };
  const useVoice = () => {
    localStorage.setItem(VOICE_PREF_KEY, "1");
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

  return (
    <section aria-labelledby="pr-title">
      <h1 id="pr-title">{tr("practice.title")}</h1>
      {tabs}
      {banner}
      {session && session.language !== lang ? (
        <div className="card" role="status" data-testid="lang-banner">
          <p>{tr("practice.lang_changed", { lang: LANG_NAMES[session.language as Lang] ?? session.language })}</p>
          <button type="button" className="btn btn-secondary" onClick={() => void start(session.seed)} data-testid="lang-restart">
            {tr("practice.lang_restart", { lang: LANG_NAMES[lang] })}
          </button>
        </div>
      ) : null}
      {session ? (
        <details className="card" open={goalOpen} onToggle={(e) => setGoalOpen(e.currentTarget.open)} data-testid="goal">
          <summary>{tr("practice.goal_title")}</summary>
          <p>{tr("practice.goal_line", { error: tr(`err.desc.${session.goal.error}` as "err.desc.SUB-SFL") })}</p>
          <p className="muted">{tr("practice.goal_tips")}</p>
          <ul className="plain">
            {session.goal.tips.map((tip) => (
              <li key={tip}>{tip}</li>
            ))}
          </ul>
        </details>
      ) : null}
      {session ? <ChildrenRow children={session.children} speaker={speaker} /> : null}
      <p className="muted" data-testid="turn-counter">
        {tr("practice.turn", { n: turns.length, cap })}
      </p>
      {judgeMode ? (
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
            {judgeMode && t.meters.length > 0 ? <Meters children={t.meters} /> : null}
            {judgeMode && showLayers ? <LayersPanel layers={t.layers} /> : null}
          </div>
        ))}
        {busy ? <p className="muted" role="status">{tr("practice.sending")}</p> : null}
      </div>
      {notice ? <p role="alert">{tr(notice as "practice.error")}</p> : null}
      {over ? <p role="status" data-testid="over">{tr(over as "practice.over_all")}</p> : null}
      {session ? <Materials items={session.materials} disabled={busy || over !== null} onTap={tap} /> : null}
      {session ? (
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
      ) : null}
      {voiceOn ? (
        <div className="compose">
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
          {session?.voice.mode === "stub" ? (
            <p className="muted" data-testid="voice-stub">
              {tr("practice.voice_stub")}
            </p>
          ) : null}
          <p className="muted" role="status" data-testid="voice-state">
            {vstate === "listening" ? tr("practice.listening") : ""}
          </p>
          <button type="button" className="btn btn-secondary" onClick={useText} data-testid="use-text">
            {tr("practice.use_text")}
          </button>
        </div>
      ) : (
        <>
          {judgeMode ? (
            <label className="check">
              <input type="checkbox" checked={hintsOn} onChange={(e) => setHintsOn(e.target.checked)} data-testid="hints-toggle" />
              <span>{tr("hints.toggle")}</span>
            </label>
          ) : null}
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
          {canRecord() ? (
            <button type="button" className="btn btn-secondary" onClick={useVoice} data-testid="use-voice">
              {tr("practice.use_voice")}
            </button>
          ) : null}
        </>
      )}
      {judgeMode ? <BreakIt /> : null}
      <button type="button" className="btn btn-secondary" onClick={() => void end()} disabled={busy || turns.length === 0 || phase === "ending"} data-testid="end">
        {tr("practice.end")}
      </button>
    </section>
  );
}
