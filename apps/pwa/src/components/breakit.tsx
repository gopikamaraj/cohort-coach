// "Try to break it": prepared adversarial lines, or the visitor's own line, run through the real
// pre-filter. The visitor sees the line, which check stopped it and why, or that it passed. A typed
// line is checked by rules on the server and is never stored, logged or sent to a model.
import { useState } from "react";
import type { Key } from "../i18n";
import { tryBreak, tryBreakText, type BreakResult } from "../lib/breakit";
import { useApp } from "../state";

const KINDS = ["injection", "harsh", "phone", "child_name"] as const;

export function BreakIt() {
  const { tr, lang } = useApp();
  const [result, setResult] = useState<BreakResult | null>(null);
  const [failed, setFailed] = useState(false);
  const [typed, setTyped] = useState("");
  const run = (kind: (typeof KINDS)[number]) => {
    setFailed(false);
    tryBreak(kind, lang).then(setResult, () => setFailed(true));
  };
  return (
    <section aria-labelledby="break-title" data-testid="break-it">
      <h2 id="break-title">{tr("break.title")}</h2>
      <p className="muted">{tr("break.intro")}</p>
      <div className="chips">
        {KINDS.map((k) => (
          <button key={k} type="button" className="chip-btn" onClick={() => run(k)} data-testid={`break-${k}`}>
            {tr(`break.${k}` as Key)}
          </button>
        ))}
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!typed.trim()) return;
          setFailed(false);
          tryBreakText(typed.trim(), lang).then(setResult, () => setFailed(true));
        }}
      >
        <label className="field">
          <span>{tr("break.type_label")}</span>
          <textarea value={typed} maxLength={200} rows={2} onChange={(e) => setTyped(e.target.value)} data-testid="break-text" />
        </label>
        <p className="muted">{tr("break.typed_note")}</p>
        <button type="submit" className="btn btn-primary" disabled={!typed.trim()} data-testid="break-check">
          {tr("break.check")}
        </button>
      </form>
      {failed ? <p role="alert">{tr("flow.error")}</p> : null}
      {result ? (
        <div className="panel" role="status" data-testid="break-result">
          <p>
            <strong>{tr("break.line")}:</strong> “{result.line}”
          </p>
          <p>
            <span className={result.blocked ? "chip chip-negative" : "chip chip-positive"} data-testid="break-verdict">
              {tr(result.blocked ? "break.verdict_blocked" : "break.verdict_passed")}
            </span>
          </p>
          <p data-testid="break-explanation">{result.explanation}</p>
          {result.blocked ? (
            <p className="muted">
              {tr("break.stopped_by")}: {result.layer}
            </p>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
