// The detail under "What my class gets wrong": the answer map, why each error is flagged (the matrix
// of which items check which error, with this class's counts) and what each error means. One selected
// error or question marks the same questions in all of them.
import { useMemo, useState } from "react";
import { keys } from "../lib/diagnosis";
import { buildAnswerMap, classCoverage } from "../lib/results";
import { useApp } from "../state";
import { AnswerMap } from "./AnswerMap";
import { CoverageMatrix } from "./CoverageMatrix";
import { ErrorExplanations } from "./ErrorExplanations";

export function ResultsDetail({ untracked, activeCode, onCode, onlyConfirmed }: { untracked: number; activeCode: string | null; onCode: (c: string | null) => void; onlyConfirmed: boolean }) {
  const { tr, check, role } = useApp();
  const code = activeCode;
  const setCode = onCode;
  const [item, setItem] = useState<number | null>(null);
  const [openExplain, setOpenExplain] = useState<Set<string>>(new Set());
  const map = useMemo(() => (check ? buildAnswerMap(check.formKey, check.children, check.absent ?? [], check.approved) : null), [check]);
  if (role !== "teacher" && role !== "judge") {
    return (
      <p className="muted" data-testid="results-detail-role">
        {tr("results.map.role_hidden")}
      </p>
    );
  }
  if (!check || !map || map.rolls.length === 0) {
    return (
      <p className="muted" data-testid="results-detail-none">
        {tr("results.map.none")}
      </p>
    );
  }
  const rows = classCoverage(map);
  const wide = typeof window !== "undefined" && window.matchMedia?.("(min-width: 900px)").matches;
  const explain = (c: string) => {
    setOpenExplain((s) => new Set(s).add(c));
    requestAnimationFrame(() => document.getElementById(`explain-${c}`)?.scrollIntoView({ block: "start" }));
  };
  return (
    <div className="stack results-detail" data-testid="results-detail">
      <h2 id="amap-title">{tr("results.map.title")}</h2>
      <AnswerMap map={map} onlyConfirmed={onlyConfirmed} activeCode={code} activeItem={item} onItem={setItem} onExplain={explain} />

      <details className="results-why" open={wide} data-testid="results-why">
        <summary>
          <h2 className="inline-h">{tr("results.why.title")}</h2>
        </summary>
        <CoverageMatrix
          rows={rows.map((r) => ({ code: r.code, items: new Set(r.items), assessed: r.assessed, confirmed: r.confirmed, possible: onlyConfirmed ? undefined : r.possible }))}
          items={map.items.map((i) => ({ n: i.n, extra: i.extra }))}
          caption={tr("results.why.title")}
          withClass
          activeCode={code}
          activeItem={item}
          onCode={(c) => {
            setItem(null);
            setCode(c);
          }}
          onItem={(n) => {
            setCode(null);
            setItem(n);
          }}
          testId="results-coverage"
          rowTestPrefix="results-coverage-"
        />
        <p data-testid="results-rule">{tr("results.why.rule", { n: keys.rules.min_hits })}</p>
        <p className="muted" data-testid="results-shared">
          {tr("results.why.shared")}
        </p>
      </details>

      <h2 id="explain-title">{tr("results.explain.title")}</h2>
      <ErrorExplanations
        map={map}
        untracked={untracked}
        openCodes={openExplain}
        onToggle={(c, open) =>
          setOpenExplain((s) => {
            const next = new Set(s);
            if (open) next.add(c);
            else next.delete(c);
            return next;
          })
        }
      />
    </div>
  );
}
