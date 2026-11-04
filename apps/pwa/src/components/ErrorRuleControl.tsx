// The one control for the error rule, shown wherever counts appear. See lib/errorRule.ts.
import { useErrorRule } from "../lib/errorRule";
import { useApp } from "../state";

export function ErrorRuleControl({ name = "rule" }: { name?: string }) {
  const { tr } = useApp();
  const [rule, setRule] = useErrorRule();
  return (
    <fieldset className="rule-control" data-testid="rule-control">
      <legend>{tr("rule.legend")}</legend>
      <label className="check-line">
        <input type="radio" name={name} checked={rule === 2} onChange={() => setRule(2)} data-testid="rule-2" /> <span>{tr("rule.two")}</span>
      </label>
      <label className="check-line">
        <input type="radio" name={name} checked={rule === 1} onChange={() => setRule(1)} data-testid="rule-1" /> <span>{tr("rule.one")}</span>
      </label>
      <p className="muted" data-testid="rule-shown">
        {tr(rule === 2 ? "rule.showing_two" : "rule.showing_one")}
      </p>
    </fieldset>
  );
}

/** One line saying which rule a set of counts was made under (from the server's `rule.min_hits`). */
export function RuleLine({ minHits }: { minHits: number | undefined }) {
  const { tr } = useApp();
  if (minHits !== 1 && minHits !== 2) return null;
  return (
    <p className="muted" data-testid="rule-line">
      {tr(minHits === 2 ? "rule.showing_two" : "rule.showing_one")}
    </p>
  );
}
