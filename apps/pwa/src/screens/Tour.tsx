// The guided tour (judge mode): nine steps in one path. Each step names the role, says what to notice, and opens the
// real screen. A progress bar, Skip and Back, and a deep link per step. The mentor and coach steps say their data is mocked.
import { useEffect } from "react";
import { PilotClassBanner, SimulatedBanner } from "../components/parts";
import type { Key } from "../i18n";
import { go, href, useHash } from "../lib/router";
import { stepFromHash, TOUR, TOUR_SECONDS } from "../lib/tour";
import { useJudge } from "../lib/roles";
import { useApp, type Role } from "../state";
import { track } from "../lib/tester";

export default function Tour() {
  const { tr, setRole, klass } = useApp();
  const judge = useJudge();
  const n = stepFromHash(useHash()) ?? 1;
  const step = TOUR[n - 1]!;
  useEffect(() => {
    if (n === 1) track("tour_started", { tour_id: "main" });
    track("tour_step_viewed", { tour_id: "main", step_id: String(n) });
  }, [n]);
  const goStep = (k: number) => {
    const next = TOUR[k - 1];
    if (!next) return;
    setRole(next.role as Role);
    window.location.hash = `/tour/${k}`;
  };
  if (!judge) {
    return (
      <section aria-labelledby="tour-title">
        <h1 id="tour-title">{tr("tour.title")}</h1>
        <p role="status">{tr("watch.demo_only")}</p>
      </section>
    );
  }
  return (
    <section aria-labelledby="tour-title" data-testid="tour">
      <h1 id="tour-title">{tr("tour.title")}</h1>
      {klass?.simulated ? <SimulatedBanner /> : null}
      <PilotClassBanner />
      <progress max={TOUR.length} value={n} aria-label={tr("tour.step", { n, total: TOUR.length })} data-testid="tour-progress" />
      <p className="muted" data-testid="tour-step">
        {tr("tour.step", { n, total: TOUR.length })} · {tr("tour.time", { s: step.seconds, total: Math.round(TOUR_SECONDS / 60) })}
      </p>
      <p className="chip" role="status" data-testid="tour-banner">
        {tr("tour.now", { role: tr(`role.${step.role}` as Key) })}
      </p>
      <h2>{tr(step.title as Key)}</h2>
      <p data-testid="tour-notice">
        <strong>{tr("tour.notice")}:</strong> {tr(step.notice as Key)}
      </p>
      {step.mocked ? (
        <p className="note" role="note" data-testid="tour-mocked">
          {tr("tour.mocked")}
        </p>
      ) : null}
      <p>
        <a className="btn btn-primary" href={href(step.route)} data-testid="tour-open">
          {tr("tour.open")}
        </a>
      </p>

      <div className="row">
        <button type="button" className="btn btn-secondary" onClick={() => goStep(n - 1)} disabled={n === 1} data-testid="tour-back">
          {tr("tour.back")}
        </button>
        <button type="button" className="btn btn-primary" onClick={() => {
            if (n === TOUR.length) {
              track("tour_completed", { tour_id: "main" });
              go("/roles");
            } else goStep(n + 1);
          }} data-testid="tour-next">
          {n === TOUR.length ? tr("tour.finish") : tr("tour.skip")}
        </button>
        <a className="btn btn-secondary" href={href("/roles")} data-testid="tour-leave" onClick={() => track("tour_skipped", { tour_id: "main", step_id: String(n) })}>
          {tr("tour.leave")}
        </a>
      </div>
    </section>
  );
}
