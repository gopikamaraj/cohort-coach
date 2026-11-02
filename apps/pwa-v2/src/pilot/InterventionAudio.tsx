// Page 2: Intervention audio. The coordinator chooses how many lessons, a language and a voice and
// taps Generate; each lesson waits for the coach before it is voiced; an approved file can be played,
// downloaded and shared on WhatsApp from this phone. Nothing is published before approval.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Icon } from "../components/icons";
import type { Key } from "../i18n";
import {
  canDo,
  jsonInit,
  pilotJson,
  PilotApiError,
  type AudioPage,
  type AudioStatus,
  type Card,
  type Config,
  type Summary,
} from "./api";
import { loadPage, queueGenerate, savePage, flushJobs, waitingJobs, getAudioBlob, realDeps } from "./audioCache";
import { usePilot } from "./context";
import { goPilot } from "./route";
import { messageWithLink, saveToPhone, shareLink, whatsappUrl } from "./share";

const STATUS: Record<AudioStatus, { key: Key; icon: string; tone: string }> = {
  draft: { key: "pilot.au.st.draft", icon: "edit", tone: "" },
  needs_review: { key: "pilot.au.st.needs_review", icon: "flag", tone: "p-watch" },
  approved: { key: "pilot.au.st.approved", icon: "ok", tone: "p-live" },
  audio_ready: { key: "pilot.au.st.audio_ready", icon: "speaker", tone: "p-ok" },
  failed: { key: "pilot.au.st.failed", icon: "close", tone: "p-bad" },
};
const REASONS = ["wrong_maths", "culturally_off", "too_complex_for_medium", "tone_issue", "factually_shaky"] as const;
const NO_TRACK: Record<string, Key> = { not_enough: "pilot.au.no.not_enough", no_error: "pilot.au.no.no_error" };

export function minutes(seconds: number): string {
  const s = Math.round(seconds);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

/** The reason line for a card that failed or waits on a person, from the server's short note. */
export function noteKey(note: string | null): Key | null {
  if (!note) return null;
  if (note.startsWith("checker_down")) return "pilot.au.note.checker_down";
  if (note.startsWith("audio:")) return "pilot.au.note.audio";
  if (note.startsWith("rejected")) return "pilot.au.note.rejected";
  return "pilot.au.note.gate";
}

export default function InterventionAudio() {
  const { tr, session, online, lang } = usePilot();
  const isCoordinator = canDo(session, "coordinator");
  const isCoach = canDo(session, "coach");
  const [config, setConfig] = useState<Config | null>(null);
  const [page, setPage] = useState<AudioPage | null>(null);
  const [cached, setCached] = useState(false);
  const [teachers, setTeachers] = useState<string[]>([]);
  const [language, setLanguage] = useState<string>(lang);
  const [voice, setVoice] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ text: string; bad?: boolean } | null>(null);
  const [waiting, setWaiting] = useState(0);
  const [logCards, setLogCards] = useState<Card[] | null>(null);
  const [allUnsupported, setAllUnsupported] = useState(false);

  const load = useCallback(async () => {
    try {
      const [cfg, p] = await Promise.all([
        pilotJson<Config>("/api/pilot/config", {}, session),
        pilotJson<AudioPage>("/api/pilot/audio", {}, session),
      ]);
      setConfig(cfg);
      setVoice((v) => v || cfg.voice_default);
      setPage(p);
      setCached(false);
      void savePage(p);
      if (isCoordinator) {
        pilotJson<Summary>("/api/pilot/sheets/summary", {}, session)
          .then((s) => setTeachers(s.teachers))
          .catch(() => undefined);
      }
    } catch {
      const saved = await loadPage();
      if (saved) {
        setPage(saved);
        setCached(true);
      }
    }
  }, [session, isCoordinator]);

  useEffect(() => {
    void load();
  }, [load]);
  useEffect(() => {
    void waitingJobs().then((j) => setWaiting(j.length));
  }, [online]);
  // back online: run the Generate requests that waited
  useEffect(() => {
    if (!online || !isCoordinator) return;
    void flushJobs(session).then(async (ran) => {
      if (ran) {
        setWaiting((await waitingJobs()).length);
        await load();
      }
    });
  }, [online, isCoordinator, session, load]);
  // while lessons are being voiced in the background, look again every few seconds
  const voicing = page?.cards.some((c) => c.status === "approved");
  useEffect(() => {
    if (!voicing || !online) return;
    const id = setInterval(() => void load(), 3000);
    return () => clearInterval(id);
  }, [voicing, online, load]);

  const cards = useMemo(() => (page?.cards ?? []).filter((c) => c.language === language), [page, language]);
  const sharable = cards.filter((c) => c.shareable && c.active);

  async function setCount(next: number) {
    if (!config) return;
    try {
      await pilotJson("/api/pilot/config/audio-count", jsonInit("PUT", { audio_count: next }), session);
      setConfig({ ...config, audio_count: next });
      await load();
    } catch (e) {
      setMsg({ text: e instanceof PilotApiError && e.offline ? tr("pilot.err.offline") : tr("pilot.err.generic"), bad: true });
    }
  }

  async function generate(force = false) {
    const body = { language, voice: voice || config?.voice_default || "ritu", force };
    if (!online) {
      await queueGenerate(body);
      setWaiting((await waitingJobs()).length);
      setMsg({ text: tr("pilot.au.queued") });
      return;
    }
    setBusy(true);
    setMsg({ text: tr("pilot.au.generating") });
    try {
      const out = await pilotJson<{ made: number }>("/api/pilot/audio/generate", jsonInit("POST", body), session);
      setMsg({ text: out.made ? tr("pilot.au.generated", { n: out.made }) : tr("pilot.au.up_to_date") });
      await load();
    } catch (e) {
      if (e instanceof PilotApiError && e.offline) {
        await queueGenerate(body);
        setWaiting((await waitingJobs()).length);
        setMsg({ text: tr("pilot.au.queued") });
      } else if (e instanceof PilotApiError && e.reason && NO_TRACK[e.reason]) {
        setMsg({ text: tr(NO_TRACK[e.reason]!), bad: true });
      } else {
        setMsg({ text: tr("pilot.err.generic"), bad: true });
      }
    } finally {
      setBusy(false);
    }
  }

  async function shareAll() {
    let links: string[];
    try {
      links = await Promise.all(
        sharable.map(async (c) => (await pilotJson<{ url: string }>(`/api/pilot/audio/${c.id}/lesson-link`, {}, session)).url),
      );
    } catch {
      setMsg({ text: online ? tr("pilot.err.generic") : tr("pilot.au.need_signal"), bad: true });
      return;
    }
    const text = [tr("pilot.sh.message_all"), ...links].join("\n");
    const out = await shareLink(text);
    if (out === "shared") setLogCards(sharable);
    else if (out === "unsupported" || out === "failed") {
      setAllUnsupported(true);
      window.open(whatsappUrl(text), "_blank", "noopener");
      setMsg({ text: tr(out === "failed" ? "pilot.sh.failed" : "pilot.sh.unsupported"), bad: out === "failed" });
    }
  }

  const empty = page !== null && page.sheets_read === 0;

  return (
    <>
      <h1>{tr("pilot.au.title")}</h1>
      <p className="p-muted">{tr("pilot.au.intro")}</p>
      {cached ? (
        <p className="p-msg" role="status">
          <Icon name="wifi" size={18} />
          {tr("pilot.au.cached")}
        </p>
      ) : null}

      {isCoordinator && config ? (
        <section className="p-card" aria-labelledby="set-h">
          <h2 id="set-h">{tr("pilot.au.count")}</h2>
          <div className="p-stepper">
            <button type="button" aria-label={tr("pilot.au.fewer")} disabled={!online || config.audio_count <= 1} onClick={() => void setCount(config.audio_count - 1)} data-testid="count-dec">
              <Icon name="minus" />
            </button>
            <output aria-live="polite" data-testid="count-value">
              {config.audio_count}
            </output>
            <button type="button" aria-label={tr("pilot.au.more")} disabled={!online || config.audio_count >= config.audio_max} onClick={() => void setCount(config.audio_count + 1)} data-testid="count-inc">
              <Icon name="plus" />
            </button>
            <span className="p-small p-muted">{tr("pilot.au.count_help", { max: config.audio_max })}</span>
          </div>
          <div className="p-grid2" style={{ marginTop: 16 }}>
            <div className="p-field">
              <span>{tr("pilot.au.language")}</span>
              <div className="p-seg" role="group" aria-label={tr("pilot.au.language")}>
                {config.languages.map((l) => (
                  <button key={l} type="button" aria-pressed={language === l} onClick={() => setLanguage(l)} data-testid={`lang-${l}`}>
                    {l === "en" ? "English" : l === "hi" ? "हिन्दी" : "தமிழ்"}
                  </button>
                ))}
              </div>
            </div>
            <label className="p-field">
              <span>{tr("pilot.au.voice")}</span>
              <select value={voice} onChange={(e) => setVoice(e.target.value)} data-testid="voice">
                {config.voices.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <button type="button" className="p-btn p-block" disabled={busy || empty} onClick={() => void generate()} data-testid="generate">
            <Icon name="speaker" size={20} />
            {busy ? tr("pilot.au.generating") : tr("pilot.au.generate")}
          </button>
          {waiting > 0 ? (
            <p className="p-msg" role="status" style={{ marginTop: 12, marginBottom: 0 }}>
              <Icon name="wifi" size={18} />
              {tr("pilot.au.queued")}
            </p>
          ) : null}
        </section>
      ) : (
        <div className="p-field">
          <span>{tr("pilot.au.language")}</span>
          <div className="p-seg" role="group" aria-label={tr("pilot.au.language")}>
            {["en", "hi", "ta"].map((l) => (
              <button key={l} type="button" aria-pressed={language === l} onClick={() => setLanguage(l)}>
                {l === "en" ? "English" : l === "hi" ? "हिन्दी" : "தமிழ்"}
              </button>
            ))}
          </div>
        </div>
      )}

      {msg ? (
        <p className={msg.bad ? "p-msg p-bad" : "p-msg"} role={msg.bad ? "alert" : "status"}>
          <Icon name={msg.bad ? "close" : "info"} size={18} />
          {msg.text}
        </p>
      ) : null}

      {empty ? (
        <section className="p-card p-watch" data-testid="empty-state">
          <div className="p-note">
            <Icon name="info" />
            <div>
              <h2>{tr("pilot.au.empty.title")}</h2>
              <p>{tr("pilot.au.empty.body")}</p>
              <button type="button" className="p-pillbtn p-go" onClick={() => goPilot("/upload")}>
                <Icon name="camera" size={18} />
                {tr("pilot.au.empty.link")}
              </button>
            </div>
          </div>
        </section>
      ) : page && page.cards.length > 0 ? (
        <p className="p-small p-muted">{tr("pilot.au.based", { n: page.sheets_read, classes: page.classes_read })}</p>
      ) : null}

      {isCoordinator && sharable.length > 1 ? (
        <button type="button" className="p-btn p-secondary p-block" style={{ marginBottom: 12 }} onClick={() => void shareAll()} data-testid="share-all">
          <Icon name="send" size={20} />
          {tr("pilot.au.share_all", { n: sharable.length })}
        </button>
      ) : null}
      {allUnsupported && sharable.length > 1 ? <p className="p-small p-muted">{tr("pilot.sh.unsupported")}</p> : null}

      <div data-testid="audio-cards">
        {cards.map((c) => (
          <AudioCard key={c.id} card={c} isCoordinator={isCoordinator} isCoach={isCoach} teachers={teachers} onChanged={load} onLog={(cs) => setLogCards(cs)} setMsg={setMsg} />
        ))}
      </div>

      {logCards ? (
        <ShareLog
          cards={logCards}
          teachers={teachers}
          onDone={(n) => {
            setLogCards(null);
            if (n) setMsg({ text: tr("pilot.sh.log.saved", { n }) });
            void load();
          }}
        />
      ) : null}
    </>
  );
}

interface CardProps {
  card: Card;
  isCoordinator: boolean;
  isCoach: boolean;
  teachers: string[];
  onChanged: () => Promise<void>;
  onLog: (cards: Card[]) => void;
  setMsg: (m: { text: string; bad?: boolean } | null) => void;
}

function AudioCard({ card, isCoordinator, isCoach, onChanged, onLog, setMsg }: CardProps) {
  const { tr, session, online } = usePilot();
  const [src, setSrc] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [fallback, setFallback] = useState(false);
  const [reason, setReason] = useState<(typeof REASONS)[number]>("tone_issue");
  const urlRef = useRef<string | null>(null);
  useEffect(() => () => void (urlRef.current && URL.revokeObjectURL(urlRef.current)), []);

  const st = STATUS[card.status];
  const nk = noteKey(card.note);
  const fileOk = card.ready && card.active;
  const canShare = card.shareable && card.active;
  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await fn();
      await onChanged();
    } catch (e) {
      setMsg({ text: e instanceof PilotApiError && e.offline ? tr("pilot.err.offline") : tr("pilot.err.generic"), bad: true });
    } finally {
      setBusy(false);
    }
  };

  async function play() {
    setBusy(true);
    try {
      const { blob } = await getAudioBlob(card.id, session, realDeps());
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
      urlRef.current = URL.createObjectURL(blob);
      setSrc(urlRef.current);
    } catch {
      setMsg({ text: online ? tr("pilot.err.generic") : tr("pilot.au.need_signal"), bad: true });
    } finally {
      setBusy(false);
    }
  }

  async function download() {
    setBusy(true);
    try {
      const { blob } = await getAudioBlob(card.id, session, realDeps());
      saveToPhone(blob, card.file_name);
      setMsg({ text: tr("pilot.au.saved_offline") });
    } catch {
      setMsg({ text: online ? tr("pilot.err.generic") : tr("pilot.au.need_signal"), bad: true });
    } finally {
      setBusy(false);
    }
  }

  async function share() {
    setBusy(true);
    try {
      const url = await link();
      if (!url) return;
      const out = await shareLink(tr("pilot.sh.lesson_message", { slot: card.slot }), url);
      if (out === "shared") onLog([card]);
      else if (out === "unsupported" || out === "failed") {
        setFallback(true);
        if (out === "failed") setMsg({ text: tr("pilot.sh.failed"), bad: true });
      }
    } catch {
      setFallback(true);
    } finally {
      setBusy(false);
    }
  }

  /** The lesson link a teacher opens: the approved words, with audio made on the first tap. */
  async function link(): Promise<string | null> {
    try {
      const out = await pilotJson<{ url: string }>(`/api/pilot/audio/${card.id}/lesson-link`, {}, session);
      return out.url;
    } catch {
      setMsg({ text: online ? tr("pilot.err.generic") : tr("pilot.au.need_signal"), bad: true });
      return null;
    }
  }

  async function copyLink() {
    const url = await link();
    if (!url) return;
    try {
      await navigator.clipboard.writeText(url);
      setMsg({ text: tr("pilot.sh.lesson_link_copied", { days: 14 }) });
    } catch {
      window.prompt(tr("pilot.sh.copy_link"), url);
    }
  }

  async function openWhatsApp() {
    const url = await link();
    if (url) window.open(whatsappUrl(messageWithLink(tr("pilot.sh.lesson_message", { slot: card.slot }), url)), "_blank", "noopener");
  }


  return (
    <article className={card.active ? "p-card" : "p-card p-off"} data-testid={`card-${card.slot}`} data-status={card.status} data-active={card.active}>
      <h2>
        <Icon name="speaker" size={20} />
        {tr("pilot.au.lesson", { slot: card.slot })}
      </h2>
      <p style={{ marginBottom: 4 }}>{card.title}</p>
      <div className="p-meta">
        <span className={`p-chip ${st.tone}`} data-testid="status">
          <Icon name={st.icon} size={16} />
          {tr(st.key)}
        </span>
        <span className="p-chip">{card.language.toUpperCase()}</span>
        {card.ready ? <span className="p-chip">{minutes(card.duration_s)}</span> : null}
        <span className="p-chip">{tr("pilot.au.version", { n: card.version })}</span>
      </div>
      {!card.active ? <p className="p-small p-muted">{tr("pilot.au.inactive")}</p> : null}
      {nk ? <p className="p-small">{tr(nk)}</p> : null}
      {card.stale && card.active ? <p className="p-small p-muted">{tr("pilot.au.stale")}</p> : null}

      {fileOk ? (
        src ? (
          <audio controls autoPlay src={src} />
        ) : (
          <button type="button" className="p-pillbtn p-go" disabled={busy} onClick={() => void play()} data-testid="play">
            <Icon name="play" size={18} />
            {tr("pilot.au.play")}
          </button>
        )
      ) : null}

      <details className="p-script">
        <summary>{tr("pilot.au.script")}</summary>
        <pre>{card.script}</pre>
      </details>

      {canShare && !fileOk ? (
        <p className="p-small p-muted" data-testid="text-only">
          {tr("pilot.au.text_only")}
        </p>
      ) : null}

      {/* One main action per card, by who she is and where the lesson stands; the rest sit under More */}
      {isCoach && card.status === "needs_review" ? (
        <button type="button" className="p-btn p-block" disabled={busy || !online} onClick={() => void act(() => pilotJson(`/api/pilot/audio/${card.id}/approve`, jsonInit("POST"), session))} data-testid="approve">
          <Icon name="ok" size={18} />
          {tr("pilot.au.approve")}
        </button>
      ) : canShare && isCoordinator ? (
        <button type="button" className="p-btn p-block" disabled={busy || !online} onClick={() => void share()} data-testid="share">
          <Icon name="send" size={18} />
          {tr("pilot.au.share_link")}
        </button>
      ) : null}
      {!canShare ? (
        <p className="p-small p-muted" style={{ margin: "8px 0 0" }}>
          {tr("pilot.au.only_approved")}
        </p>
      ) : null}

      {fileOk || (isCoordinator && (canShare || card.active)) || (isCoach && card.status === "needs_review") ? (
        <details className="p-more" data-testid="more">
          <summary>{tr("pilot.au.more_options")}</summary>
          <div className="p-actions">
            {fileOk ? (
              <button type="button" className="p-pillbtn" disabled={busy} onClick={() => void download()} data-testid="download">
                <Icon name="download" size={18} />
                {tr("pilot.au.download")}
              </button>
            ) : null}
            {isCoordinator && canShare && !fileOk ? (
              <button type="button" className="p-pillbtn" disabled={busy || !online} onClick={() => void act(() => pilotJson(`/api/pilot/audio/${card.id}/render`, jsonInit("POST"), session))} data-testid="make-audio">
                <Icon name="speaker" size={18} />
                {tr("pilot.au.make_audio")}
              </button>
            ) : null}
            {isCoordinator && card.status === "failed" && card.note?.startsWith("audio:") ? (
              <button type="button" className="p-pillbtn p-go" disabled={busy || !online} onClick={() => void act(() => pilotJson(`/api/pilot/audio/${card.id}/render`, jsonInit("POST"), session))}>
                <Icon name="refresh" size={18} />
                {tr("pilot.au.voice_again")}
              </button>
            ) : null}
            {isCoordinator && card.active ? (
              <button type="button" className="p-pillbtn" disabled={busy || !online} onClick={() => void act(() => pilotJson(`/api/pilot/audio/${card.id}/regenerate`, jsonInit("POST"), session))} data-testid="regenerate">
                <Icon name="refresh" size={18} />
                {tr("pilot.au.regenerate")}
              </button>
            ) : null}
          </div>
          {isCoach && card.status === "needs_review" ? (
            <div className="p-sub">
              <label className="p-field">
                <span>{tr("pilot.au.return_reason")}</span>
                <select value={reason} onChange={(e) => setReason(e.target.value as (typeof REASONS)[number])}>
                  {REASONS.map((r) => (
                    <option key={r} value={r}>
                      {tr(`pilot.au.reason.${r}` as Key)}
                    </option>
                  ))}
                </select>
              </label>
              <button type="button" className="p-pillbtn" disabled={busy || !online} onClick={() => void act(() => pilotJson(`/api/pilot/audio/${card.id}/reject`, jsonInit("POST", { reason }), session))}>
                {tr("pilot.au.return")}
              </button>
            </div>
          ) : null}
        </details>
      ) : null}

      {canShare && fallback && isCoordinator ? (
        <div className="p-sub" data-testid="share-fallback">
          <h2>{tr("pilot.sh.title")}</h2>
          <p className="p-small">{tr("pilot.sh.unsupported")}</p>
          <div className="p-actions" style={{ marginTop: 0 }}>
            <button type="button" className="p-pillbtn" disabled={!online} onClick={() => void copyLink()} data-testid="copy-link">
              <Icon name="chat" size={18} />
              {tr("pilot.sh.copy_link")}
            </button>
            <button type="button" className="p-pillbtn p-go" disabled={!online} onClick={() => void openWhatsApp()} data-testid="open-whatsapp">
              <Icon name="send" size={18} />
              {tr("pilot.sh.open_wa")}
            </button>
            <button type="button" className="p-pillbtn" onClick={() => onLog([card])}>
              {tr("pilot.sh.log.title")}
            </button>
          </div>
        </div>
      ) : null}

      {card.shared_with.length > 0 ? (
        <p className="p-small p-muted" style={{ marginTop: 8, marginBottom: 0 }}>
          {tr("pilot.sh.sent_to", { teachers: card.shared_with.join(", ") })}
        </p>
      ) : null}

      {card.versions.length > 1 ? (
        <details className="p-script">
          <summary>{tr("pilot.au.versions")}</summary>
          <ul className="p-list">
            {card.versions
              .filter((v) => v.id !== card.id)
              .map((v) => (
                <li key={v.id}>
                  <span className="p-grow">{tr("pilot.au.version", { n: v.version })}</span>
                  <span className="p-chip">{tr(STATUS[v.status].key)}</span>
                </li>
              ))}
          </ul>
        </details>
      ) : null}
    </article>
  );
}

function ShareLog({ cards, teachers, onDone }: { cards: Card[]; teachers: string[]; onDone: (recorded: number) => void }) {
  const { tr, session } = usePilot();
  const [picked, setPicked] = useState<string[]>([]);
  const [extra, setExtra] = useState("");
  const [bad, setBad] = useState(false);
  const all = [...new Set([...teachers, ...picked])];
  const toggle = (t: string) => setPicked((p) => (p.includes(t) ? p.filter((x) => x !== t) : [...p, t]));

  async function save() {
    try {
      for (const c of cards) {
        await pilotJson(`/api/pilot/audio/${c.id}/shares`, jsonInit("POST", { teacher_refs: picked }), session);
      }
      onDone(picked.length);
    } catch {
      setBad(true);
    }
  }

  return (
    <section className="p-card p-focus" aria-labelledby="log-h" data-testid="share-log">
      <h2 id="log-h">{tr("pilot.sh.log.title")}</h2>
      <p className="p-small">{tr("pilot.sh.log.help")}</p>
      {all.length === 0 ? <p className="p-small">{tr("pilot.sh.log.none")}</p> : null}
      <div className="p-checks">
        {all.map((t) => (
          <label key={t}>
            <input type="checkbox" checked={picked.includes(t)} onChange={() => toggle(t)} />
            {t}
          </label>
        ))}
      </div>
      <label className="p-field">
        <span>{tr("pilot.sh.log.add")}</span>
        <input
          type="text"
          value={extra}
          maxLength={24}
          onChange={(e) => setExtra(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && extra.trim()) {
              e.preventDefault();
              setPicked((p) => [...new Set([...p, extra.trim()])]);
              setExtra("");
            }
          }}
        />
      </label>
      {bad ? (
        <p className="p-msg p-bad" role="alert">
          <Icon name="close" size={18} />
          {tr("pilot.err.generic")}
        </p>
      ) : null}
      <div className="p-actions">
        <button type="button" className="p-btn" disabled={picked.length === 0} onClick={() => void save()} data-testid="log-save">
          {tr("pilot.sh.log.save")}
        </button>
        <button type="button" className="p-pillbtn" onClick={() => onDone(0)}>
          {tr("pilot.sh.log.skip")}
        </button>
      </div>
    </section>
  );
}
