// J1: judge mode. No login. A five-minute test script with deep links, the demo controls, and
// links to the raw AI map and audit trail (pretty versions arrive with the Practice Class).
import { href, type Route } from "../lib/router";
import { useApp } from "../state";
import { SimulatedBanner } from "../components/parts";

export default function Judge() {
  const { tr, klass, term, forcedOffline, setOffline, loadDemo, advanceTerm, reset } = useApp();
  const steps: { key: "judge.step1" | "judge.step2" | "judge.step3" | "judge.step4" | "judge.step5" | "judge.step6"; to: Route | null }[] = [
    { key: "judge.step1", to: null },
    { key: "judge.step2", to: "/home" },
    { key: "judge.step3", to: "/check" },
    { key: "judge.step4", to: "/cards" },
    { key: "judge.step5", to: null },
    { key: "judge.step6", to: "/cards" },
  ];
  return (
    <section aria-labelledby="judge-title">
      <h1 id="judge-title">{tr("judge.title")}</h1>
      <p>{tr("judge.intro")}</p>
      {klass?.simulated ? <SimulatedBanner /> : null}

      <h2>{tr("judge.steps")}</h2>
      <ol className="steps">
        {steps.map((s) => (
          <li key={s.key}>
            <span>{tr(s.key)}</span>
            {s.to ? (
              <a className="btn btn-secondary" href={href(s.to)}>
                {tr("judge.go")}
              </a>
            ) : null}
          </li>
        ))}
      </ol>

      <div className="stack">
        <button type="button" className="btn btn-primary" onClick={() => void loadDemo()} data-testid="load-demo">
          {tr("judge.load_demo")}
        </button>
        {klass?.simulated ? (
          <p role="status" data-testid="demo-loaded">
            {tr("judge.demo_loaded")}
          </p>
        ) : null}
        <p>{tr("judge.term", { term })}</p>
        <button type="button" className="btn btn-secondary" onClick={() => void advanceTerm()} disabled={term >= 2} data-testid="advance">
          {tr("judge.advance")}
        </button>
        <button type="button" className="btn btn-secondary" onClick={() => setOffline(!forcedOffline)} aria-pressed={forcedOffline} data-testid="offline-toggle">
          {forcedOffline ? tr("judge.offline_off") : tr("judge.offline_on")}
        </button>
        <button type="button" className="btn btn-secondary" onClick={() => void reset()} data-testid="reset">
          {tr("judge.reset")}
        </button>
      </div>

      <h2>{tr("judge.links")}</h2>
      <ul className="plain">
        <li>
          <a href="/api/judge/ai-map" target="_blank" rel="noopener noreferrer">
            {tr("judge.ai_map")}
          </a>
        </li>
        <li>
          <a href="/api/judge/audit" target="_blank" rel="noopener noreferrer">
            {tr("judge.audit")}
          </a>
        </li>
      </ul>
      <p className="muted">{tr("judge.later")}</p>
    </section>
  );
}
