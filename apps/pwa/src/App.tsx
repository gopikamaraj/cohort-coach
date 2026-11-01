import Cards from "./screens/Cards";
import Check from "./screens/Check";
import AiMap from "./screens/AiMap";
import Audit from "./screens/Audit";
import Home from "./screens/Home";
import Practice from "./screens/Practice";
import Judge from "./screens/Judge";
import History from "./screens/History";
import Programme from "./screens/Programme";
import { OfflineNote } from "./components/parts";
import { TopBar } from "./components/TopBar";
import { Icon } from "./components/icons";
import { ToastProvider } from "./components/toast";
import Admin from "./screens/Admin";
import PrivacyNotice from "./screens/PrivacyNotice";
import Profile from "./screens/Profile";
import { Coach, Mentor } from "./screens/RoleScreens";
import Officer from "./screens/OfficerHome";
import Flow from "./screens/Flow";
import Landing from "./screens/Landing";
import Watch from "./screens/Watch";
import Tour from "./screens/Tour";
import Review from "./screens/Review";
import Papers from "./screens/Papers";
import DemoStudio from "./screens/DemoStudio";
import TwoClasses from "./screens/TwoClasses";
import { DemoPanel } from "./components/DemoPanel";
import Cohort from "./screens/Cohort";
import Assistant, { AssistantButton, AssistantDrawer } from "./screens/Assistant";
import TestingEvidence from "./screens/TestingEvidence";
import { TesterRoot } from "./components/TesterUI";
import { useEffect, useState } from "react";
import { href, useRoute, type Route } from "./lib/router";
import { AppProvider, useApp, type Role } from "./state";

const ICONS: Record<string, string> = {
  "/judge": "judge", "/home": "home", "/check": "check", "/cards": "cards", "/practice": "practice", "/programme": "programme",
  "/history": "history", "/profile": "profile", "/coach": "coach", "/mentor": "mentor", "/admin": "admin", "/officer": "programme", "/testing": "info", "/roles": "home", "/watch": "practice", "/tour": "judge", "/review": "check", "/cohort": "chat", "/assistant": "info", "/papers": "papers", "/demo": "judge", "/two-classes": "chat",
};  // fmt: skip

function Shell() {
  const route = useRoute();
  const { tr, role } = useApp();
  const teacherTabs: { to: Route; label: string }[] = [
    { to: "/home", label: tr("nav.home") },
    { to: "/papers", label: tr("papers.nav") },
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
    coach: [{ to: "/coach", label: tr("role.coach") }, { to: "/review", label: tr("queue.nav") }, { to: "/papers", label: tr("papers.nav") }, { to: "/cohort", label: tr("cohort.nav") }, mine],
    officer: [{ to: "/officer", label: tr("role.officer") }, { to: "/review", label: tr("queue.nav") }, mine],
    admin: [{ to: "/admin", label: tr("role.admin") }, mine],
    judge: [{ to: "/judge", label: tr("role.judge") }, { to: "/demo", label: tr("demo.nav") }, { to: "/two-classes", label: tr("run.nav") }, ...teacherTabs, { to: "/coach", label: tr("role.coach") }, { to: "/review", label: tr("queue.nav") }, { to: "/cohort", label: tr("cohort.nav") }, { to: "/admin", label: tr("role.admin") }, mine],
  };
  const tabs = route === "/roles" || route === "/tour" ? [] : byRole[role];
  // A phone fits four tabs and a More button; the rest sit in a sheet, so nothing hides off-screen.
  const [more, setMore] = useState(false);
  const [asOpen, setAsOpen] = useState(false);
  useEffect(() => {
    const open = () => setAsOpen(true); // the old #/assistant link, for everyone but the judge
    document.addEventListener("cc:assistant-open", open);
    return () => document.removeEventListener("cc:assistant-open", open);
  }, []);
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
  const wide = route === "/roles" || route === "/tour" || route === "/watch" || route === "/testing" || route === "/review" || route === "/cohort" || role === "coach" || role === "officer" || role === "admin";
  return (
    <div className={wide ? "stage stage-wide" : "stage stage-narrow"}>
      <div className={tabs.length === 0 ? "frame frame-bare" : "frame"}>
        <TopBar assistant={<AssistantButton onOpen={() => setAsOpen(true)} />} />
        <AssistantDrawer open={asOpen} onClose={() => setAsOpen(false)} screen={route === "/roles" ? "landing" : route.slice(1)} />
        {route !== "/roles" ? <DemoPanel /> : null}
        <OfflineNote />
        <TesterRoot />
        <main tabIndex={0} aria-label={tr("common.main")}>
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
          {route === "/cohort" ? <Cohort /> : null}
          {route === "/officer" ? <Officer /> : null}
          {route === "/assistant" ? <Assistant /> : null}
          {route === "/testing" ? <TestingEvidence /> : null}
          {route === "/papers" ? <Papers /> : null}
          {route === "/demo" ? <DemoStudio /> : null}
          {route === "/two-classes" ? <TwoClasses /> : null}
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
          {rest.map((tab) => (
            <a key={tab.to} href={href(tab.to)} aria-current={route === tab.to ? "page" : undefined} className={route === tab.to ? "navtab navtab-rest navtab-on" : "navtab navtab-rest"}>
              <Icon name={ICONS[tab.to] ?? "info"} />
              <span>{tab.label}</span>
            </a>
          ))}
          {rest.length > 0 ? (
            <button type="button" className={restOn || more ? "navtab navtab-morebtn navtab-on" : "navtab navtab-morebtn"} aria-expanded={more} aria-controls="more-sheet" data-testid="nav-more" onClick={() => setMore((v) => !v)}>
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
