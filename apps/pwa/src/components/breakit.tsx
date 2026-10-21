// "Try to break it": prepared adversarial lines run through the real pre-filter. The visitor sees the
// line, which check stopped it and why. The lines live on the server; nothing typed here is sent.
import { useState } from "react";
import type { Key } from "../i18n";
import { tryBreak, type BreakResult } from "../lib/breakit";
import { useApp } from "../state";

const KINDS = ["injection", "harsh", "phone", "child_name"] as const;

export function BreakIt() {
  const { tr, lang } = useApp();
  const [result, setResult] = useState<BreakResult | null>(null);
  const [failed, setFailed] = useState(false);
  const run = (kind: (typeof KINDS)[number]) => {
    setFailed(false);
    tryBreak(kind, lang).then(setResult, () => setFailed(true));
  };
  return (
    <section aria-labelledby="break-title" data-testid="break-it">
      <h2 id="break-title">{tr("break.title")}</h2>
      <p className="muted">{tr("break.intro")}</p>
      <div className="row">
        {KINDS.map((k) => (
          <button key={k} type="button" className="btn btn-secondary" onClick={() => run(k)} data-testid={`break-${k}`}>
            {tr(`break.${k}` as Key)}
          </button>
        ))}
      </div>
      {failed ? <p role="alert">{tr("flow.error")}</p> : null}
      {result ? (
        <div className="panel" role="status" data-testid="break-result">
          <p>
            <strong>{tr("break.line")}:</strong> “{result.line}”
          </p>
          <p data-testid="break-explanation">{result.explanation}</p>
          <p className="muted">
            {tr("break.stopped_by")}: {result.layer}
          </p>
        </div>
      ) : null}
    </section>
  );
}
