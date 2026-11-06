// J1: judge mode. No login. A five-minute test script with deep links, the demo controls, and
// links to the raw AI map and audit trail (pretty versions arrive with the Practice Class).
import { isPilotUser } from "../lib/pilot";
import { href, type Route } from "../lib/router";
import type { Key } from "../i18n";
import { useApp } from "../state";
import { SimulatedBanner } from "../components/parts";

export default function Judge() {
  const { tr, klass, checkCount, forcedOffline, setOffline, loadDemo, addLaterDemo, reset } = useApp();
  const pilot = isPilotUser(); // pilot classes are real data: no simulated class is loaded into their account
  const steps: { key: Key; to: Route | null }[] = [
    { key: "judge.step1", to: null },
    { key: "judge.step2", to: "/home" },
    { key: "judge.step3", to: "/check" },
    { key: "judge.step4", to: "/cards" },
    { key: "judge.step5", to: null },
    { key: "judge.step6", to: "/cards" },
    { key: "judge.step7", to: "/practice" },
    { key: "judge.step8", to: "/practice" },
    { key: "judge.step9", to: "/aimap" },
  ];
  return (
    <section aria-labelledby="judge-title">
      <h1 id="judge-title">{tr("judge.title")}</h1>
      <p>{tr("judge.intro")}</p>
      <a className="btn btn-primary" href="#/demo?step=1" data-testid="judge-demo-flow">
        {tr("demo.start_link")}
      </a>
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
        {pilot ? null : (
          <button type="button" className="btn btn-primary" onClick={() => void loadDemo()} data-testid="load-demo">
            {tr("judge.load_demo")}
          </button>
        )}
        {klass?.simulated ? (
          <p role="status" data-testid="demo-loaded">
            {tr("judge.demo_loaded")}
          </p>
        ) : null}
        {pilot ? null : (
          <button type="button" className="btn btn-secondary" onClick={() => void addLaterDemo()} disabled={checkCount >= 2} data-testid="advance">
            {tr("judge.advance")}
          </button>
        )}
        <button type="button" className="btn btn-secondary" onClick={() => setOffline(!forcedOffline)} aria-pressed={forcedOffline} data-testid="offline-toggle">
          {forcedOffline ? tr("judge.offline_off") : tr("judge.offline_on")}
        </button>
        <button type="button" className="btn btn-secondary" onClick={() => void reset(false)} data-testid="reset">
          {tr("judge.reset")}
        </button>
      </div>

      <h2>{tr("judge.links")}</h2>
      <ul className="plain">
        <li>
          <a href={href("/aimap")}>{tr("judge.ai_map")}</a>
        </li>
        <li>
          <a href={href("/audit")}>{tr("judge.audit")}</a>
        </li>
        <li>
          <a href={href("/testing")} data-testid="judge-testing">{tr("judge.testing")}</a>
        </li>
      </ul>
    </section>
  );
}
