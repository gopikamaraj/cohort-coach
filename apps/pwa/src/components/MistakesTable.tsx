// "Mistakes in this class" as one table: each row is a mistake with its colour and letters, the sentence,
// how many children made it (confirmed, and possible when shown), an example from her class, and the listen
// and flag buttons. Choosing a row marks the same mistake in the answer map and the matrix. The checkbox
// above it keeps only the mistakes seen on enough questions (the engine's own rule); unchecked, everything
// is shown, confirmed and possible.
import type { ReactNode } from "react";
import type { Key } from "../i18n";
import { keys } from "../lib/diagnosis";
import { SHORT, type LegendEntry } from "../lib/results";
import { IconButton } from "./icons";
import { Sticks } from "./parts";
import { useToast } from "./toast";
import { useApp } from "../state";

export interface MistakeRow {
  code: string;
  confirmed: number;
  possible: number;
  total: number;
  isFocus: boolean;
  example: string | null;
}

export function mistakeRows(
  cards: { code: string; count: number; total: number; isFocus: boolean; example: string | null }[],
  legend: LegendEntry[] | null,
  total: number,
  onlyConfirmed: boolean,
): MistakeRow[] {
  const possibleOf = (code: string) => (legend?.find((l) => l.code === code)?.possible ?? 0);
  const rows: MistakeRow[] = cards.map((c) => ({ code: c.code, confirmed: c.count, possible: onlyConfirmed ? 0 : possibleOf(c.code), total: c.total, isFocus: c.isFocus, example: c.example }));
  if (!onlyConfirmed) {
    for (const l of legend ?? []) {
      if (!rows.some((r) => r.code === l.code)) rows.push({ code: l.code, confirmed: 0, possible: l.possible, total, isFocus: false, example: null });
    }
  }
  return rows;
}

export function MistakesTable({
  rows,
  activeCode,
  onCode,
  onlyConfirmed,
  onOnlyConfirmed,
  flagged,
  onFlag,
  canHighlight,
}: {
  rows: MistakeRow[];
  activeCode: string | null;
  onCode: (code: string | null) => void;
  onlyConfirmed: boolean;
  onOnlyConfirmed: (on: boolean) => void;
  flagged: ReadonlySet<string>;
  onFlag: (code: string) => void;
  canHighlight: boolean;
}) {
  const { tr } = useApp();
  const toast = useToast();
  const name = (code: string) => tr(`err.${code}` as Key);
  const cell = (r: MistakeRow): ReactNode =>
    r.confirmed > 0 ? (
      <p data-testid={`line-${r.code}`}>{tr("cards.line", { n: r.confirmed, total: r.total, desc: tr(`err.desc.${r.code}` as Key) })}</p>
    ) : (
      <p className="muted" data-testid={`line-${r.code}`}>
        {tr("results.table.possible_only")}
      </p>
    );
  return (
    <section className="stack results-detail" aria-labelledby="mistakes-title" data-testid="mistakes">
      <h2 id="mistakes-title">{tr("results.map.legend")}</h2>
      <label className="check-line">
        <input type="checkbox" checked={onlyConfirmed} onChange={(e) => onOnlyConfirmed(e.target.checked)} data-testid="only-confirmed" />
        <span>{tr("results.table.only_confirmed", { n: keys.rules.min_hits })}</span>
      </label>
      {canHighlight ? <p className="muted">{tr("results.map.legend_hint")}</p> : null}
      {rows.length === 0 ? <p className="muted">{tr("cards.not_shown")}</p> : null}
      {rows.length > 0 ? (
        <div className="table-scroll mistakes-scroll" role="region" tabIndex={0} aria-label={tr("results.map.legend")}>
          <table className="mistakes" data-testid="mistakes-table">
            <caption className="sr-only">{tr("results.map.legend")}</caption>
            <thead>
              <tr>
                <th scope="col">{tr("results.table.col_mistake")}</th>
                <th scope="col">{tr("results.table.col_children")}</th>
                <th scope="col">
                  <span className="sr-only">{tr("cards.audio")}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.code} data-testid={`card-${r.code}`} data-kind="error" className={r.isFocus ? "mistake-focus" : undefined}>
                  <th scope="row" className="mistake-name">
                    {canHighlight ? (
                      <button type="button" className={`amap-chip amap-${r.code.toLowerCase()}${activeCode === r.code ? " amap-chip-on" : ""}`} aria-pressed={activeCode === r.code} onClick={() => onCode(activeCode === r.code ? null : r.code)} data-testid={`legend-${r.code}`}>
                        <span className="amap-swatch" aria-hidden="true">
                          {SHORT[r.code]}
                        </span>
                        <span>{name(r.code)}</span>
                      </button>
                    ) : (
                      <strong>{name(r.code)}</strong>
                    )}
                    {cell(r)}
                    {r.example ? <p className="example">{tr("cards.example", { example: r.example })}</p> : null}
                    {r.isFocus ? <p className="focus">{tr("cards.focus")}</p> : null}
                  </th>
                  <td className="mistake-count">
                    <span className="numeral">{r.confirmed}</span> <span className="muted">/ {r.total}</span>
                    {r.possible > 0 ? <span className="cov-name">{tr("results.map.legend_possible", { n: r.possible })}</span> : null}
                    <Sticks count={r.confirmed} total={r.total} label={name(r.code)} />
                  </td>
                  <td className="mistake-actions">
                    <IconButton icon="speaker" label={tr("cards.audio")} iconOnly testId={`listen-${r.code}`} onClick={() => toast(tr("cards.audio_soon"))} />
                    <IconButton icon="flag" label={tr("cards.flag")} iconOnly variant="flag" testId={`flag-${r.code}`} onClick={() => onFlag(r.code)} disabled={flagged.has(r.code)} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}

