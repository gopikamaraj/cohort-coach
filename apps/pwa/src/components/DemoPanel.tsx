// The demo stepper: "Demo step n of 12" on every screen while the judge runs the demo, with Back,
// Next (the right screen, as the right role), a link to the judge guide's question for the step,
// and Reset demo. It only moves between the product's own screens.
import { useEffect, useState } from "react";
import type { Key } from "../i18n";
import { clearDemoClass, demoStep, LAST_STEP, resetDemo, setDemoStep, stepHref, STEPS } from "../lib/demoStudio";
import { useApp } from "../state";

export function useDemoStep(): number | null {
  const [step, setStep] = useState<number | null>(demoStep());
  useEffect(() => {
    const on = () => setStep(demoStep());
    window.addEventListener("cc-demo", on);
    window.addEventListener("storage", on);
    return () => {
      window.removeEventListener("cc-demo", on);
      window.removeEventListener("storage", on);
    };
  }, []);
  return step;
}

export function DemoPanel() {
  const { tr, setRole, reload } = useApp();
  const step = useDemoStep();
  if (step === null) return null;
  const go = (n: number) => {
    const s = STEPS[n - 1];
    if (!s) return;
    setRole(s.role);
    setDemoStep(n);
    window.location.hash = stepHref(s).slice(1);
  };
  const current = STEPS[step - 1];
  const optional = step > LAST_STEP;
  return (
    <aside className="demo-panel" aria-label={tr("demo.panel")} data-testid="demo-panel">
      <p className="demo-panel-step">
        <strong data-testid="demo-panel-n">{optional ? tr("demo.panel.optional") : tr("demo.panel.step", { n: step, total: LAST_STEP })}</strong> · {tr(`demo.s${step}.line` as Key)}
      </p>
      <div className="demo-panel-actions">
        <button type="button" className="chip-btn" disabled={step <= 1} onClick={() => go(step - 1)} data-testid="demo-back">
          {tr("demo.panel.back")}
        </button>
        <button type="button" className="chip-btn chip-on" disabled={step >= STEPS.length} onClick={() => go(step + 1)} data-testid="demo-next">
          {step === LAST_STEP ? tr("demo.panel.next_optional") : tr("demo.panel.next")}
        </button>
        {current ? (
          <a className="chip-btn" href={`#/assistant?ask=${current.question}`} data-testid="demo-guide">
            {tr("demo.panel.guide")}
          </a>
        ) : null}
        <button
          type="button"
          className="chip-btn"
          onClick={() => {
            if (!window.confirm(tr("demo.panel.reset_confirm"))) return;
            void resetDemo()
              .then(clearDemoClass)
              .then(reload)
              .then(() => (window.location.hash = "#/demo?step=1"));
          }}
          data-testid="demo-reset"
        >
          {tr("demo.panel.reset")}
        </button>
      </div>
    </aside>
  );
}
