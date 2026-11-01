// The guided tour (judge mode): six steps, each a real screen, switching roles as it goes. A progress
// bar, a "What to notice" line naming the judging criterion, Skip and Back, and a deep link per step.
// Steps whose feature is built in a later phase say so plainly instead of pretending.
import { useEffect, useState } from "react";
import { SimulatedBanner } from "../components/parts";
import type { Key } from "../i18n";
import { go, href, useHash, type Route } from "../lib/router";
import { roleChanged, stepFromHash, TOUR, TOUR_SECONDS } from "../lib/tour";
import { useJudge } from "../lib/roles";
import { useApp, type Role } from "../state";
import AiMap from "./AiMap";
import Cards from "./Cards";
import Check from "./Check";
import Programme from "./Programme";
import Watch from "./Watch";
import TestingEvidence from "./TestingEvidence";
import { track } from "../lib/tester";
import { activeClass } from "../lib/db";
import { samplePaper } from "../lib/papers";
import { fetchPaperKey } from "../lib/paperKeys";

function Pending({ phase, children }: { phase: string; children?: React.ReactNode }) {
  const { tr } = useApp();
  return (
    <div className="panel" role="note" data-testid="tour-pending">
      <p>{tr("tour.pending", { phase })}</p>
      {children}
    </div>
  );
}

export default function Tour() {
  const { tr, lang, setRole, term, advanceTerm, profile, reload } = useApp();
  const [paperTick, setPaperTick] = useState(0);
  const [paperBusy, setPaperBusy] = useState(false);
  // Enter check chooses a paper that exists; on the tour the judge makes the standard one first.
  const makeStandardPaper = async () => {
    setPaperBusy(true);
    try {
      const cls = await activeClass(false);
      const p = await samplePaper(`${cls.id}:${term}`, "pre", "3A", term, lang);
      await fetchPaperKey(p.id, { role: "teacher", classId: cls.id });
      await reload();
      setPaperTick((n) => n + 1);
    } finally {
      setPaperBusy(false);
    }
  };
  const judge = useJudge();
  const n = stepFromHash(useHash()) ?? 1;
  const step = TOUR[n - 1]!;
  const [checked, setChecked] = useState(false);
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
  const showCards = checked || (profile?.stages && step.screen === "check" && profile.simulated);
  return (
    <section aria-labelledby="tour-title" data-testid="tour">
      <h1 id="tour-title">{tr("tour.title")}</h1>
      <SimulatedBanner />
      <progress max={TOUR.length} value={n} aria-label={tr("tour.step", { n, total: TOUR.length })} data-testid="tour-progress" />
      <p className="muted" data-testid="tour-step">
        {tr("tour.step", { n, total: TOUR.length })} · {tr("tour.time", { s: step.seconds, total: Math.round(TOUR_SECONDS / 60) })}
      </p>
      {roleChanged(n) ? (
        <p className="chip" role="status" data-testid="tour-banner">
          {tr("tour.now", { role: tr(`role.${step.role}` as Key) })}
        </p>
      ) : null}
      <h2>{tr(step.title as Key)}</h2>
      <p data-testid="tour-notice">
        <strong>{tr("tour.notice")}:</strong> {tr(step.notice as Key)}
      </p>

      {step.screen === "check" ? (
        <>
          {showCards ? null : (
            <>
              <div className="card stack" data-testid="tour-paper">
                <p className="muted">{tr("tour.paper_note")}</p>
                <button type="button" className="btn btn-secondary" onClick={() => void makeStandardPaper()} disabled={paperBusy} data-testid="tour-standard-paper">
                  {tr("tour.paper_button")}
                </button>
              </div>
              <Check key={paperTick} onDone={() => setChecked(true)} />
            </>
          )}
          {showCards ? <Cards /> : null}
        </>
      ) : null}
      {step.screen === "cohort" ? <Pending phase="P12" /> : null}
      {step.screen === "content" ? <Pending phase="P11, P12" /> : null}
      {step.screen === "practice" ? (
        <>
          <Watch />
          <a className="btn btn-secondary" href={href("/practice" as Route)} data-testid="tour-practice-link">
            {tr("tour.try_practice")}
          </a>
        </>
      ) : null}
      {step.screen === "term2" ? (
        <>
          <button type="button" className="btn btn-primary" onClick={() => void advanceTerm()} disabled={term >= 2} data-testid="tour-advance">
            {tr("judge.advance")}
          </button>
          <p className="muted">{tr("judge.term", { term })}</p>
          <Pending phase="P12" />
          <Programme />
        </>
      ) : null}
      {step.screen === "hood" ? <AiMap /> : null}
      {step.screen === "testing" ? <TestingEvidence embedded /> : null}

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
