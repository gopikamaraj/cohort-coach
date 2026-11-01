// T1: this term's status and the one next action. One primary action per screen.
import { href } from "../lib/router";
import { useApp } from "../state";
import { SimulatedBanner } from "../components/parts";
import type { Key } from "../i18n";
import { Icon } from "../components/icons";
import { useConsent } from "../lib/useConsent";
import { useJudge } from "../lib/roles";

export default function Home() {
  const { tr, term, klass, profile } = useApp();
  const consent = useConsent();
  const judge = useJudge();
  const errorName = profile?.track ? tr(`err.${profile.track}` as Key) : null;
  return (
    <section aria-labelledby="home-title">
      <h1 id="home-title">{tr("home.title")}</h1>
      <p className="muted">{tr("home.term", { term })}</p>
      {klass?.simulated ? <SimulatedBanner /> : null}
      {!consent ? (
        <div className="panel notice-card" data-testid="privacy-prompt">
          <h2>
            <Icon name="shield" /> <span>{tr("home.privacy_title")}</span>
          </h2>
          <p>{tr("home.privacy_body")}</p>
          <a className="btn btn-primary btn-with-icon" href={href("/privacy")} data-testid="privacy-start">
            <Icon name="info" /> <span>{tr("home.privacy_btn")}</span>
          </a>
        </div>
      ) : null}
      {profile ? (
        <>
          <p data-testid="home-status">{tr("home.status.checked", { n: profile.childrenChecked })}</p>
          <p>{errorName ? tr("home.status.track", { error: errorName }) : tr("home.status.no_track")}</p>
          <a className="btn btn-primary" href={href("/cards")} data-testid="home-action">
            {tr("home.action.cards")}
          </a>
          <div className="tiles">
            <a className="tile" href={href("/practice")} data-testid="home-practice">
              <Icon name="practice" size={28} /> <span>{tr("home.action.practice")}</span>
            </a>
            <a className="tile" href={href("/programme")} data-testid="home-programme">
              <Icon name="programme" size={28} /> <span>{tr("home.action.programme")}</span>
            </a>
            <a className="tile" href={href("/history")} data-testid="home-history">
              <Icon name="history" size={28} /> <span>{tr("home.action.history")}</span>
            </a>
            {judge ? (
              <a className="tile" href={href("/watch")} data-testid="home-watch">
                <Icon name="practice" size={28} /> <span>{tr("home.action.watch")}</span>
              </a>
            ) : null}
            <a className="tile" href={href("/flow")} data-testid="home-flow">
              <Icon name="practice" size={28} /> <span>{tr("home.action.flow")}</span>
            </a>
            <a className="tile" href={href("/profile")} data-testid="home-profile">
              <Icon name="profile" size={28} /> <span>{tr("home.action.profile")}</span>
            </a>
          </div>
        </>
      ) : (
        <>
          <p data-testid="home-status">{tr("home.status.none")}</p>
          <a className="btn btn-primary" href={href("/check")} data-testid="home-action">
            {tr("home.action.check")}
          </a>
          <p className="muted">{tr("home.demo_hint")}</p>
          <div className="tiles">
            <a className="tile" href={href("/programme")}>
              <Icon name="programme" size={28} /> <span>{tr("home.action.programme")}</span>
            </a>
            <a className="tile" href={href("/history")}>
              <Icon name="history" size={28} /> <span>{tr("home.action.history")}</span>
            </a>
            <a className="tile" href={href("/profile")}>
              <Icon name="profile" size={28} /> <span>{tr("home.action.profile")}</span>
            </a>
          </div>
        </>
      )}
    </section>
  );
}
