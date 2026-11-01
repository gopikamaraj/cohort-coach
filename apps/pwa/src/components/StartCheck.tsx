// Start a check: choose one of the class's papers from a dropdown (each says whether it is Checked), say
// how many papers there are, and start. The kind and the paper's answer key come with the paper;
// papers are made on the Papers page, never here. Starting fetches the key to this phone.
import { useState } from "react";
import type { CheckKind } from "../lib/db";
import { today } from "../lib/checks";
import { fetchPaperKey } from "../lib/paperKeys";
import type { HubPaper } from "../lib/paperHub";
import { useApp } from "../state";
import { PaperSelect, useHubIdentity } from "./PaperHubParts";

export interface CheckMeta {
  kind: CheckKind;
  checkDate: string;
  expectedChildren: number | null;
  paperId?: string | null;
  paperCode?: string | null;
}

export function StartCheck({ className, term, onStart, lastCount, preferKind }: { className: string; term: number; onStart: (form: string, meta: CheckMeta) => void; lastCount?: number | null; preferKind?: string }) {
  const { tr } = useApp();
  const who = useHubIdentity();
  const [paper, setPaper] = useState<HubPaper | null>(null);
  const [expected, setExpected] = useState(lastCount ? String(lastCount) : "");
  const [starting, setStarting] = useState(false);
  const [keyError, setKeyError] = useState(false);
  const expectedOk = /^\d+$/.test(expected) && Number(expected) >= 1 && Number(expected) <= 100;

  async function startOn() {
    if (!paper) return;
    setStarting(true);
    setKeyError(false);
    try {
      await fetchPaperKey(paper.id, who); // the paper's own answer key, to read its answers on this phone
      const kind = (["pre", "post", "termly"].includes(paper.kind) ? paper.kind : "pre") as CheckKind;
      onStart(paper.id, { kind, checkDate: today(), expectedChildren: Number(expected), paperId: paper.id, paperCode: paper.check_code });
    } catch {
      setKeyError(true);
    } finally {
      setStarting(false);
    }
  }

  return (
    <section aria-labelledby="start-title" data-testid="start-check">
      <h1 id="start-title">{tr("check.start_title")}</h1>
      <p className="muted" data-testid="start-class">
        {className} · {tr("check.term_n", { n: term })}
      </p>
      <PaperSelect who={who} chosen={paper?.id ?? null} onChoose={setPaper} preferKind={preferKind} />
      {paper ? (
        <p className="muted" data-testid="paper-attached">
          {tr("papers.attached", { code: paper.check_code })}
        </p>
      ) : null}
      <label className="field">
        <span>{tr("check.expected_label")}</span>
        <span className="muted" id="expected-hint">
          {tr("check.expected_hint")}
        </span>
        <input inputMode="numeric" required aria-describedby="expected-hint" aria-invalid={!expectedOk} value={expected} maxLength={3} onChange={(e) => setExpected(e.target.value.replace(/\D/g, ""))} data-testid="check-expected" />
      </label>
      <div className="stack">
        <button type="button" className="btn btn-primary" disabled={!paper || !expectedOk || starting} onClick={() => void startOn()} data-testid="start-check-go">
          {tr("check.start_go")}
        </button>
        {!paper ? (
          <p className="muted" data-testid="start-need-paper">
            {tr("check.need_paper")}
          </p>
        ) : null}
        {keyError ? (
          <p role="alert" data-testid="key-error">
            {tr("check.key_error")}
          </p>
        ) : null}
      </div>
    </section>
  );
}
