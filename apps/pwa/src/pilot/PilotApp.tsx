// Pilot mode's whole app: sign-in, then two pages. No other screen of the full app is imported here,
// so none can be reached; the router sends every other address to Upload sheets.
import { useCallback, useEffect, useMemo, useState } from "react";
import { Icon } from "../components/icons";
import { LANG_NAMES, LANGS, isLang, t, type Key, type Lang } from "../i18n";
import { useOnline } from "../lib/net";
import InterventionAudio from "./InterventionAudio";
import SignIn from "./SignIn";
import UploadSheets from "./UploadSheets";
import { loadSession, onSessionEnded, saveSession, type Session } from "./api";
import { PilotCtx } from "./context";
import LessonPage from "./LessonPage";
import { enforceRoute, href, useLessonToken, usePilotRoute } from "./route";
import "./pilot.css";

const SHORT: Record<Lang, string> = { en: "EN", hi: "हिं", ta: "தமி" };

function storedLang(): Lang {
  try {
    const v = localStorage.getItem("cc.lang");
    return isLang(v) ? v : "en";
  } catch {
    return "en";
  }
}

export default function PilotApp() {
  const [lang, setLangState] = useState<Lang>(storedLang);
  const [session, setSession] = useState<Session | null>(loadSession);
  const [ended, setEnded] = useState(false);
  const route = usePilotRoute();
  const lesson = useLessonToken();
  const online = useOnline();

  useEffect(() => {
    enforceRoute();
    window.addEventListener("hashchange", enforceRoute);
    return () => window.removeEventListener("hashchange", enforceRoute);
  }, []);
  useEffect(
    () =>
      onSessionEnded(() => {
        saveSession(null);
        setSession(null);
        setEnded(true);
      }),
    [],
  );
  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const setLang = useCallback((next: Lang) => {
    setLangState(next);
    try {
      localStorage.setItem("cc.lang", next);
    } catch {
      /* private mode */
    }
  }, []);
  const tr = useCallback((key: Key, params?: Record<string, string | number>) => t(lang, key, params), [lang]);
  const state = useMemo(() => (session ? { lang, tr, session, online } : null), [lang, tr, session, online]);

  if (lesson) return <LessonPage token={lesson} />; // a teacher's lesson link: no sign-in

  const langSwitch = (
    <div className="p-seg" role="group" aria-label={tr("pilot.au.language")}>
      {LANGS.map((l) => (
        <button key={l} type="button" aria-pressed={lang === l} lang={l} title={LANG_NAMES[l]} onClick={() => setLang(l)}>
          {SHORT[l]}
        </button>
      ))}
    </div>
  );

  if (!state || !session) {
    return (
      <div className="pilot">
        <header className="p-top">
          <span className="p-brand">{tr("pilot.title")}</span>
          {langSwitch}
        </header>
        <SignIn
          tr={tr}
          online={online}
          ended={ended}
          onSignedIn={(s) => {
            saveSession(s);
            setEnded(false);
            setSession(s);
          }}
        />
      </div>
    );
  }

  return (
    <PilotCtx.Provider value={state}>
      <div className="pilot">
        <header className="p-top">
          <span className="p-brand">{tr("pilot.title")}</span>
          <span className={online ? "p-pill-state" : "p-pill-state p-off"} data-testid="pilot-net">
            <Icon name="wifi" size={16} />
            {online ? tr("pilot.pill.offline_ready") : tr("pilot.pill.offline_now")}
          </span>
          <div className="p-bar">
            {langSwitch}
            <button
              type="button"
              className="p-pillbtn"
              data-testid="pilot-signout"
              title={tr("pilot.signed_as", { name: session.name })}
              onClick={() => {
                saveSession(null);
                setSession(null);
              }}
            >
              <Icon name="profile" size={18} />
              {tr("pilot.signout")}
            </button>
          </div>
        </header>
        <nav className="p-nav" aria-label={tr("pilot.nav.label")}>
          <a href={href("/upload")} aria-current={route === "/upload" ? "page" : undefined} data-testid="nav-upload">
            <Icon name="camera" />
            {tr("pilot.nav.upload")}
          </a>
          <a href={href("/audio")} aria-current={route === "/audio" ? "page" : undefined} data-testid="nav-audio">
            <Icon name="speaker" />
            {tr("pilot.nav.audio")}
          </a>
        </nav>
        <main className="p-page">{route === "/audio" ? <InterventionAudio /> : <UploadSheets />}</main>
      </div>
    </PilotCtx.Provider>
  );
}
