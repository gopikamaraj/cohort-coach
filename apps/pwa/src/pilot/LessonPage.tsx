// The page a teacher opens from a lesson link. No sign-in: the unguessable link is the key, and it
// opens one approved lesson only. The words show at once; the audio is made (one Sarvam call) the
// first time anyone taps Download audio, and kept for every later tap. Where a phone has a voice of
// its own for the lesson's language, a later step can read the words aloud on the phone and skip
// the server voice (not built yet: see docs/build/PARKING.md).
import { useCallback, useEffect, useState } from "react";
import { Icon } from "../components/icons";
import { isLang, t, type Key, type Lang } from "../i18n";
import { useOnline } from "../lib/net";
import { PilotApiError, fetchLesson, fetchLessonAudio, type LessonAudio, type LessonView } from "./api";
import "./pilot.css";

type Phase = "loading" | "ended" | "ready";

function storedLang(): Lang {
  try {
    const v = localStorage.getItem("cc.lang");
    return isLang(v) ? v : "en";
  } catch {
    return "en";
  }
}

/** Saves a file the server sends as an attachment; the browser handles the download itself. */
export function startDownload(url: string, name: string): void {
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
}

export default function LessonPage({ token }: { token: string }) {
  const online = useOnline();
  const [phase, setPhase] = useState<Phase>("loading");
  const [lesson, setLesson] = useState<LessonView | null>(null);
  const [audio, setAudio] = useState<LessonAudio | null>(null);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<Key | null>(null);
  const [lang, setLang] = useState<Lang>(storedLang);
  const tr = useCallback((key: Key, params?: Record<string, string | number>) => t(lang, key, params), [lang]);

  useEffect(() => {
    let live = true;
    fetchLesson(token)
      .then((view) => {
        if (!live) return;
        setLesson(view);
        if (isLang(view.language)) setLang(view.language); // the lesson's own language
        setPhase("ready");
      })
      .catch((e: unknown) => {
        if (!live) return;
        if (e instanceof PilotApiError && e.offline) setProblem("lesson.err.offline");
        setPhase(e instanceof PilotApiError && !e.offline ? "ended" : "loading");
      });
    return () => {
      live = false;
    };
  }, [token]);
  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  async function download() {
    if (!lesson) return;
    setBusy(true);
    setProblem(null);
    try {
      const out = await fetchLessonAudio(token);
      setAudio(out);
      setLesson({ ...lesson, audio_ready: true });
      startDownload(out.url, out.file_name);
    } catch (e) {
      if (e instanceof PilotApiError && e.offline) setProblem("lesson.err.offline");
      else if (e instanceof PilotApiError && e.status === 429) setProblem("lesson.err.busy");
      else if (e instanceof PilotApiError && e.status === 404) setPhase("ended");
      else setProblem("lesson.err.voice");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="pilot" data-testid="lesson-page">
      <header className="p-top">
        <span className="p-brand">{tr("pilot.title")}</span>
        <span className={online ? "p-pill-state" : "p-pill-state p-off"} data-testid="pilot-net">
          <Icon name="wifi" size={16} />
          {online ? tr("pilot.pill.offline_ready") : tr("pilot.pill.offline_now")}
        </span>
      </header>
      <main className="p-page">
        {phase === "loading" ? (
          <p className="p-msg" role="status" data-testid="lesson-loading">
            {problem ? tr(problem) : tr("lesson.opening")}
          </p>
        ) : null}
        {phase === "ended" ? (
          <p className="p-msg p-bad" role="alert" data-testid="lesson-ended">
            <Icon name="close" size={18} />
            {tr("lesson.err.ended")}
          </p>
        ) : null}
        {phase === "ready" && lesson ? (
          <article className="p-card" data-testid="lesson-card">
            <h1>{lesson.title}</h1>
            <div className="p-meta">
              <span className="p-chip p-ok" data-testid="lesson-badge">
                <Icon name="ok" size={16} />
                {tr("lesson.badge")}
              </span>
              <span className="p-chip">{lesson.language.toUpperCase()}</span>
            </div>
            {audio ? (
              <div className="p-sub" data-testid="lesson-audio">
                <audio controls src={audio.url} />
                <p className="p-small p-muted">{tr("lesson.ready")}</p>
                <button type="button" className="p-pillbtn" onClick={() => startDownload(audio.url, audio.file_name)}>
                  <Icon name="download" size={18} />
                  {tr("lesson.save_again")}
                </button>
              </div>
            ) : (
              <div className="p-actions">
                <button type="button" className="p-btn" disabled={busy || !online} onClick={() => void download()} data-testid="lesson-download">
                  <Icon name="download" size={18} />
                  {busy ? tr("lesson.making") : tr("lesson.download")}
                </button>
              </div>
            )}
            <p className="p-lesson-text" data-testid="lesson-text">
              {lesson.script}
            </p>

            {problem ? (
              <p className="p-msg p-bad" role="alert" data-testid="lesson-problem">
                <Icon name="close" size={18} />
                {tr(problem)}
              </p>
            ) : null}
          </article>
        ) : null}
      </main>
    </div>
  );
}
