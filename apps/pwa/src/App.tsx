import { LANG_NAMES, LANGS, isLang } from "./i18n";
import Cards from "./screens/Cards";
import Check from "./screens/Check";
import AiMap from "./screens/AiMap";
import Audit from "./screens/Audit";
import Home from "./screens/Home";
import Practice from "./screens/Practice";
import Judge from "./screens/Judge";
import History from "./screens/History";
import Programme from "./screens/Programme";
import { StatusLine } from "./components/parts";
import { Icon } from "./components/icons";
import { ToastProvider } from "./components/toast";
import Admin from "./screens/Admin";
import PrivacyNotice from "./screens/PrivacyNotice";
import Profile from "./screens/Profile";
import { Coach, Mentor, Officer } from "./screens/RoleScreens";
import Flow from "./screens/Flow";
import Landing from "./screens/Landing";
import Watch from "./screens/Watch";
import Tour from "./screens/Tour";
import Review from "./screens/Review";
import { useEffect, useState } from "react";
import { go, href, useRoute, type Route } from "./lib/router";
import { AppProvider, ROLES, useApp, type Role } from "./state";

const ROLE_HOME: Record<Role, Route> = {
  teacher: "/home",
  judge: "/judge",
  mentor: "/mentor",
  coach: "/coach",
  officer: "/officer",
  admin: "/admin",
};

const ICONS: Record<string, string> = {
  "/judge": "judge", "/home": "home", "/check": "check", "/cards": "cards", "/practice": "practice", "/programme": "programme",
  "/history": "history", "/profile": "profile", "/coach": "coach", "/mentor": "mentor", "/admin": "admin", "/officer": "programme", "/roles": "home", "/watch": "practice", "/tour": "judge", "/review": "check",
};  // fmt: skip

function Shell() {
  const route = useRoute();
  const { tr, role, setRole, lang, setLang } = useApp();
  const teacherTabs: { to: Route; label: string }[] = [
    { to: "/home", label: tr("nav.home") },
    { to: "/check", label: tr("nav.check") },
    { to: "/cards", label: tr("nav.cards") },
    { to: "/practice", label: tr("nav.practice") },
    { to: "/programme", label: tr("nav.programme") },
    { to: "/history", label: tr("nav.history") },
  ];
  const mine = { to: "/profile" as Route, label: tr("nav.profile") };
  const byRole: Record<Role, { to: Route; label: string }[]> = {
    teacher: [...teacherTabs, mine],
    mentor: [{ to: "/mentor", label: tr("role.mentor") }, ...teacherTabs, mine],
    coach: [{ to: "/coach", label: tr("role.coach") }, { to: "/review", label: tr("queue.nav") }, mine],
    officer: [{ to: "/officer", label: tr("role.officer") }, { to: "/review", label: tr("queue.nav") }, mine],
    admin: [{ to: "/admin", label: tr("role.admin") }, mine],
    judge: [{ to: "/judge", label: tr("role.judge") }, ...teacherTabs, { to: "/coach", label: tr("role.coach") }, { to: "/review", label: tr("queue.nav") }, { to: "/admin", label: tr("role.admin") }, mine],
  };
  const tabs = route === "/roles" || route === "/tour" ? [] : byRole[role];
  // A phone fits four tabs and a More button; the rest sit in a sheet, so nothing hides off-screen.
  const [more, setMore] = useState(false);
  useEffect(() => setMore(false), [route, role]);
  useEffect(() => {
    if (!more) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setMore(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [more]);
  const bar = tabs.length > 5 ? tabs.slice(0, 4) : tabs;
  const rest = tabs.length > 5 ? tabs.slice(4) : [];
  const restOn = rest.some((tab) => tab.to === route);
  const wide = route === "/roles" || route === "/tour" || route === "/watch" || route === "/review" || role === "coach" || role === "officer" || role === "admin";
  return (
    <div className={wide ? "stage stage-wide" : "stage stage-narrow"}>
      <div className="frame">
        <div className="strip">
          <label>
            <span className="sr">{tr("common.menu")}</span>
            <select
              value={role}
              data-testid="role"
              onChange={(e) => {
                const next = e.target.value as Role;
                setRole(next);
                go(next === "judge" ? "/roles" : ROLE_HOME[next]);
              }}
            >
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {tr(`role.${r}`)}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="sr">{tr("common.language")}</span>
            <select
              value={lang}
              data-testid="lang"
              onChange={(e) => {
                if (isLang(e.target.value)) setLang(e.target.value);
              }}
            >
              {LANGS.map((l) => (
                <option key={l} value={l}>
                  {LANG_NAMES[l]}
                </option>
              ))}
            </select>
          </label>
        </div>
        <header className="top">
          <span className="brand">{tr("app.title")}</span>
          <StatusLine />
        </header>
        <main>
          {route === "/judge" ? <Judge /> : null}
          {route === "/home" ? <Home /> : null}
          {route === "/check" ? <Check /> : null}
          {route === "/cards" ? <Cards /> : null}
          {route === "/practice" ? <Practice /> : null}
          {route === "/programme" ? <Programme /> : null}
          {route === "/history" ? <History /> : null}
          {route === "/aimap" ? <AiMap /> : null}
          {route === "/audit" ? <Audit /> : null}
          {route === "/profile" ? <Profile /> : null}
          {route === "/privacy" ? <PrivacyNotice /> : null}
          {route === "/admin" ? <Admin /> : null}
          {route === "/coach" ? <Coach /> : null}
          {route === "/mentor" ? <Mentor /> : null}
          {route === "/flow" ? <Flow /> : null}
          {route === "/roles" ? <Landing /> : null}
          {route === "/watch" ? <Watch /> : null}
          {route === "/tour" ? <Tour /> : null}
          {route === "/review" ? <Review /> : null}
          {route === "/officer" ? <Officer /> : null}
        </main>
        {more ? (
          <>
            <button type="button" className="more-backdrop" aria-label={tr("common.close")} onClick={() => setMore(false)} />
            <ul className="more-sheet" id="more-sheet" data-testid="more-sheet">
              {rest.map((tab) => (
                <li key={tab.to}>
                  <a href={href(tab.to)} aria-current={route === tab.to ? "page" : undefined} className={route === tab.to ? "more-link more-on" : "more-link"}>
                    <Icon name={ICONS[tab.to] ?? "info"} />
                    <span>{tab.label}</span>
                  </a>
                </li>
              ))}
            </ul>
          </>
        ) : null}
        <nav className="navbar" aria-label={tr("common.menu")}>
          {bar.map((tab) => (
            <a key={tab.to} href={href(tab.to)} aria-current={route === tab.to ? "page" : undefined} className={route === tab.to ? "navtab navtab-on" : "navtab"}>
              <Icon name={ICONS[tab.to] ?? "info"} />
              <span>{tab.label}</span>
            </a>
          ))}
          {rest.length > 0 ? (
            <button type="button" className={restOn || more ? "navtab navtab-on" : "navtab"} aria-expanded={more} aria-controls="more-sheet" data-testid="nav-more" onClick={() => setMore((v) => !v)}>
              <Icon name="more" />
              <span>{tr("nav.more")}</span>
            </button>
          ) : null}
        </nav>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AppProvider>
      <ToastProvider>
        <Shell />
      </ToastProvider>
    </AppProvider>
  );
}
