// T1: this term's status and the one next action. One primary action per screen.
import { href } from "../lib/router";
import { useApp } from "../state";
import { SimulatedBanner } from "../components/parts";
import type { Key } from "../i18n";

export default function Home() {
  const { tr, term, klass, profile } = useApp();
  const errorName = profile?.track ? tr(`err.${profile.track}` as Key) : null;
  return (
    <section aria-labelledby="home-title">
      <h1 id="home-title">{tr("home.title")}</h1>
      <p className="muted">{tr("home.term", { term })}</p>
      {klass?.simulated ? <SimulatedBanner /> : null}
      {profile ? (
        <>
          <p data-testid="home-status">{tr("home.status.checked", { n: profile.childrenChecked })}</p>
          <p>{errorName ? tr("home.status.track", { error: errorName }) : tr("home.status.no_track")}</p>
          <a className="btn btn-primary" href={href("/cards")} data-testid="home-action">
            {tr("home.action.cards")}
          </a>
          <a className="btn btn-secondary" href={href("/practice")} data-testid="home-practice">
            {tr("home.action.practice")}
          </a>
        </>
      ) : (
        <>
          <p data-testid="home-status">{tr("home.status.none")}</p>
          <a className="btn btn-primary" href={href("/check")} data-testid="home-action">
            {tr("home.action.check")}
          </a>
          <p className="muted">{tr("home.demo_hint")}</p>
        </>
      )}
    </section>
  );
}
