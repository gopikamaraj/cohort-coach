// The title bar on every screen: the brand, the current page with a one-line description, the
// connection (online or works offline, with the network speed), the language switch, the current
// role (a link back to the role picker), the Assistant and, when the AI is not live, its badge.
import { useState, useSyncExternalStore } from "react";
import type { Key } from "../i18n";
import { LANGS } from "../i18n";
import { href, useRoute } from "../lib/router";
import { getPrefs, subscribePrefs } from "../lib/tester";
import { useApp } from "../state";
import { Icon } from "./icons";
import { AiModeBadge, StatusLine } from "./parts";

const PAGES = new Set(["roles", "judge", "home", "papers", "check", "cards", "practice", "cohort", "history", "profile", "privacy", "coach", "mentor", "officer", "review", "cohort_chat", "demo", "two-classes", "assistant", "testing", "watch", "tour", "aimap", "audit", "admin", "flow"]);

export function TopBar({ assistant }: { assistant: React.ReactNode }) {
  const { tr, role, lang, setLang } = useApp();
  const route = useRoute().slice(1);
  const nickname = useSyncExternalStore(subscribePrefs, getPrefs, getPrefs).nickname;
  const page = PAGES.has(route) ? route : null;
  const [info, setInfo] = useState(false); // phone: the description opens from the info icon
  return (
    <header className="top">
      <div className="top-left">
        <a className="brand" href={href("/roles")} data-testid="brand">
          <img className="brand-icon" src="/icon.svg" alt="" width={32} height={32} />
          {tr("app.title")}
        </a>
        {page ? (
          <div className="top-page" data-testid="top-page" role="group" aria-label={tr("top.page")}>
            <p className="top-title" data-testid="top-title">
              {tr(`page.${page}.title` as Key)}
              <button type="button" className="top-info" aria-expanded={info} aria-controls="top-sub" aria-label={tr("top.about")} onClick={() => setInfo((v) => !v)} data-testid="top-info">
                <Icon name="info" size={18} />
              </button>
            </p>
            <p id="top-sub" className={info ? "top-sub is-open" : "top-sub"} data-testid="top-sub">
              {tr(`page.${page}.sub` as Key)}
            </p>
          </div>
        ) : null}
      </div>
      <div className="top-tools">
        <StatusLine />
        <div className="seg" role="group" aria-label={tr("top.lang")} data-testid="lang">
          {LANGS.map((l) => (
            <button key={l} type="button" lang={l} aria-pressed={lang === l} aria-label={{ en: "English", hi: "हिन्दी", ta: "தமிழ்" }[l]} onClick={() => setLang(l)} data-testid={`lang-${l}`}>
              {tr(`top.lang.${l}` as Key)}
            </button>
          ))}
        </div>
        {route === "roles" ? (
          <button type="button" className="role-chip" onClick={() => document.dispatchEvent(new CustomEvent("cc:nickname"))} data-testid="nickname-chip">
            {nickname || tr("profile.nickname_set")}
          </button>
        ) : ( // the picker is where the role is chosen: no role chip there
          <a className="role-chip" href={href("/roles")} title={tr("top.change_role")} data-testid="role-chip">
            {nickname ? tr("top.as_named", { role: tr(`role.${role}` as Key), name: nickname }) : tr("top.as", { role: tr(`role.${role}` as Key) })}
          </a>
        )}
        {assistant}
        <AiModeBadge />
      </div>
    </header>
  );
}
