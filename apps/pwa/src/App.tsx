import { LANG_NAMES, LANGS, isLang } from "./i18n";
import Cards from "./screens/Cards";
import Check from "./screens/Check";
import AiMap from "./screens/AiMap";
import Audit from "./screens/Audit";
import Home from "./screens/Home";
import Practice from "./screens/Practice";
import Judge from "./screens/Judge";
import { StatusLine } from "./components/parts";
import { go, href, useRoute, type Route } from "./lib/router";
import { AppProvider, useApp, type Role } from "./state";

const ROLE_HOME: Record<Role, Route> = {
  teacher: "/home",
  judge: "/judge",
  mentor: "/later",
  officer: "/later",
};

function Later() {
  const { tr, role } = useApp();
  return (
    <section aria-labelledby="later-title">
      <h1 id="later-title">{tr(`role.${role}`)}</h1>
      <p data-testid="later">{tr("role.later")}</p>
      <a className="btn btn-primary" href={href("/home")}>
        {tr("nav.home")}
      </a>
    </section>
  );
}

function Shell() {
  const route = useRoute();
  const { tr, role, setRole, lang, setLang } = useApp();
  const tabs: { to: Route; label: string }[] = [
    ...(role === "judge" ? [{ to: "/judge" as Route, label: tr("role.judge") }] : []),
    { to: "/home", label: tr("nav.home") },
    { to: "/check", label: tr("nav.check") },
    { to: "/cards", label: tr("nav.cards") },
    { to: "/practice", label: tr("nav.practice") },
  ];
  return (
    <div className="stage">
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
                go(ROLE_HOME[next]);
              }}
            >
              {(["judge", "teacher", "mentor", "officer"] as Role[]).map((r) => (
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
          {route === "/aimap" ? <AiMap /> : null}
          {route === "/audit" ? <Audit /> : null}
          {route === "/later" ? <Later /> : null}
        </main>
        <nav className="tabs" aria-label={tr("common.menu")}>
          {tabs.map((tab) => (
            <a key={tab.to} href={href(tab.to)} aria-current={route === tab.to ? "page" : undefined} className={route === tab.to ? "tab tab-on" : "tab"}>
              {tab.label}
            </a>
          ))}
        </nav>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AppProvider>
      <Shell />
    </AppProvider>
  );
}
