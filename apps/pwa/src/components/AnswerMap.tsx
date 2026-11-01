// The answer map: roll number against question, every cell the engine's reading of that answer
// (a tick, a two-letter mistake code, a neutral mark, a dash or a question mark). A mistake is shown by
// colour, letters and a pattern together. The table stays on this phone. Choosing a mistake in the legend, or
// a question in the header, marks the same questions in "Why an error is flagged".
import { useMemo, useRef, useState, type KeyboardEvent } from "react";
import type { Key } from "../i18n";
import { explanationFor, pick } from "../lib/errorContent";
import { coverageFromKey, SHORT, sortRolls, type AnswerMap as Map, type MapCell, type SortBy } from "../lib/results";
import { keys } from "../lib/diagnosis";
import { useApp } from "../state";

const GLYPH: Record<string, string> = { correct: "✓", other: "×", blank: "–", unreadable: "?" };

function slug(code: string): string {
  return code.toLowerCase();
}

export function AnswerMap({
  map,
  activeCode,
  activeItem,
  onCode,
  onItem,
  onExplain,
}: {
  map: Map;
  activeCode: string | null;
  activeItem: number | null;
  onCode: (code: string | null) => void;
  onItem: (n: number | null) => void;
  onExplain: (code: string) => void;
}) {
  const { tr, lang } = useApp();
  const [sort, setSort] = useState<SortBy>("roll");
  const [open, setOpen] = useState<{ roll: number; n: number } | null>(null);
  const [cursor, setCursor] = useState<{ r: number; c: number }>({ r: 0, c: 0 });
  const tableRef = useRef<HTMLTableElement>(null);
  const rolls = useMemo(() => sortRolls(map.rolls, sort), [map.rolls, sort]);
  const cov = useMemo(() => coverageFromKey(map.formKey), [map.formKey]);
  const nameOf = (code: string) => tr(`err.${code}` as Key);
  const markedCols = new Set<number>([...(activeCode ? (cov[activeCode] ?? []) : []), ...(activeItem !== null ? [activeItem] : [])]);

  const state = (c: MapCell): string => {
    if (c.kind === "error" && c.code) return tr(c.confirmed ? "results.map.state.error" : "results.map.state.error_possible", { name: nameOf(c.code) });
    return tr(`results.map.state.${c.kind}` as Key);
  };

  const move = (e: KeyboardEvent<HTMLTableElement>) => {
    const delta: Record<string, [number, number]> = { ArrowRight: [0, 1], ArrowLeft: [0, -1], ArrowDown: [1, 0], ArrowUp: [-1, 0] };
    const d = delta[e.key];
    if (e.key === "Escape" && open) {
      setOpen(null);
      return;
    }
    if (!d) return;
    e.preventDefault();
    const r = Math.min(rolls.length - 1, Math.max(0, cursor.r + d[0]));
    const c = Math.min(map.items.length - 1, Math.max(0, cursor.c + d[1]));
    setCursor({ r, c });
    requestAnimationFrame(() => tableRef.current?.querySelector<HTMLButtonElement>(`[data-r="${r}"][data-c="${c}"]`)?.focus());
  };

  const opened = open ? rolls.find((r) => r.roll === open.roll)?.cells.find((c) => c.n === open.n) : undefined;
  const openedItem = open ? map.items.find((i) => i.n === open.n) : undefined;

  return (
    <div className="stack results-detail" data-testid="answer-map">
      <p className="muted">{tr("results.map.intro")}</p>

      {map.legend.length > 0 ? (
        <div>
          <h3 className="amap-h">{tr("results.map.legend")}</h3>
          <ul className="plain amap-legend" data-testid="amap-legend">
            {map.legend.map((l) => (
              <li key={l.code}>
                <button
                  type="button"
                  className={`amap-chip amap-${slug(l.code)}${activeCode === l.code ? " amap-chip-on" : ""}`}
                  aria-pressed={activeCode === l.code}
                  onClick={() => onCode(activeCode === l.code ? null : l.code)}
                  data-testid={`legend-${l.code}`}
                >
                  <span className="amap-swatch" aria-hidden="true">
                    {SHORT[l.code]}
                  </span>
                  <span>
                    {tr("results.map.legend_chip", { code: SHORT[l.code] ?? l.code, name: nameOf(l.code), n: l.confirmed })}
                    {l.possible > 0 ? <span className="muted"> · {tr("results.map.legend_possible", { n: l.possible })}</span> : null}
                  </span>
                </button>
              </li>
            ))}
          </ul>
          <p className="muted">{tr("results.map.legend_hint")}</p>
        </div>
      ) : null}

      <div className="subtabs" role="group" aria-label={tr("results.map.sort_label")}>
        {(["roll", "errors"] as const).map((by) => (
          <button key={by} type="button" className={by === sort ? "subtab subtab-on" : "subtab"} aria-pressed={by === sort} onClick={() => setSort(by)} data-testid={`amap-sort-${by}`}>
            {tr(by === "roll" ? "results.map.sort_roll" : "results.map.sort_errors")}
          </button>
        ))}
      </div>

      <div className="table-scroll amap-scroll" role="region" tabIndex={0} aria-label={tr("results.map.table_label")}>
        <table className="amap" ref={tableRef} onKeyDown={move} data-testid="amap-table">
          <caption className="sr-only">{tr("results.map.table_label")}</caption>
          <thead>
            <tr>
              <th scope="col" className="amap-roll">
                {tr("results.map.roll")}
              </th>
              {map.items.map((it) => (
                <th key={it.n} scope="col" className={markedCols.has(it.n) ? "amap-col-on" : undefined} data-testid={`amap-col-${it.n}`}>
                  <button type="button" className="cov-pick" aria-pressed={activeItem === it.n} aria-label={`${tr("results.map.question_head", { n: it.n })}: ${it.question}`} onClick={() => onItem(activeItem === it.n ? null : it.n)}>
                    <span className="nowrap">{it.n}</span>
                    <span className="amap-q nowrap">{it.question}</span>
                  </button>
                  {it.extra ? <span className="cov-extra">{tr("results.map.extra")}</span> : null}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rolls.map((r, ri) => (
              <tr key={r.roll} data-testid={`amap-row-${r.roll}`}>
                <th scope="row" className="amap-roll">
                  {r.roll}
                </th>
                {r.cells.map((c, ci) => {
                  const isActive = activeCode !== null && c.codes.includes(activeCode);
                  const dim = activeCode !== null && !isActive;
                  const cls = [
                    "amap-cell",
                    c.kind === "error" && c.code ? `amap-err amap-${slug(c.code)}` : `amap-${c.kind}`,
                    c.kind === "error" && !c.confirmed ? "amap-possible" : "",
                    dim ? "amap-dim" : "",
                    markedCols.has(c.n) ? "amap-col-on" : "",
                  ]
                    .filter(Boolean)
                    .join(" ");
                  return (
                    <td key={c.n} className={markedCols.has(c.n) ? "amap-col-on" : undefined}>
                      <button
                        type="button"
                        className={cls}
                        data-r={ri}
                        data-c={ci}
                        data-testid={`cell-${r.roll}-${c.n}`}
                        data-kind={c.kind}
                        data-code={c.code ?? ""}
                        data-confirmed={c.confirmed ? "1" : "0"}
                        tabIndex={cursor.r === ri && cursor.c === ci ? 0 : -1}
                        aria-label={tr("results.map.cell_label", { roll: r.roll, q: c.n, state: state(c) })}
                        aria-haspopup="dialog"
                        onFocus={() => setCursor({ r: ri, c: ci })}
                        onClick={() => setOpen(open && open.roll === r.roll && open.n === c.n ? null : { roll: r.roll, n: c.n })}
                      >
                        <span aria-hidden="true">{c.kind === "error" && c.code ? (SHORT[c.code] ?? "×") : (GLYPH[c.kind] ?? "")}</span>
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr data-testid="amap-total">
              <th scope="row" className="amap-roll">
                {tr("results.map.total")}
              </th>
              {map.wrongByItem.map((n, q) => (
                <td key={q} className="amap-total-cell" data-testid={`amap-total-${map.items[q]?.n}`} aria-label={tr("results.map.total_label", { q: map.items[q]?.n ?? q + 1, n })}>
                  {n}
                </td>
              ))}
            </tr>
          </tfoot>
        </table>
      </div>

      {opened && openedItem && open ? (
        <div className="amap-pop panel" role="dialog" aria-label={tr("results.pop.title", { roll: open.roll, q: open.n })} data-testid="amap-pop">
          <div className="row amap-pop-head">
            <strong>{tr("results.pop.title", { roll: open.roll, q: open.n })}</strong>
            <button type="button" className="btn btn-secondary" onClick={() => setOpen(null)} data-testid="amap-pop-close">
              {tr("results.pop.close")}
            </button>
          </div>
          <p>{tr(openedItem.type === "dictation" ? "results.pop.dictation" : "results.pop.question", { question: openedItem.question })}</p>
          <p>{tr("results.pop.given", { given: opened.kind === "blank" || opened.kind === "unreadable" ? tr(`results.map.state.${opened.kind}` as Key) : String(opened.given) })}</p>
          <p>{tr("results.pop.correct", { correct: opened.correct })}</p>
          {opened.kind === "error" && opened.code ? (
            <>
              <p>
                <strong>{tr("results.pop.mistake", { name: nameOf(opened.code) })}</strong>
              </p>
              <p>{tr(opened.confirmed ? "results.pop.confirmed" : "results.pop.possible", { n: keys.rules.min_hits })}</p>
              {(() => {
                const what = pick(explanationFor(opened.code)?.what, lang);
                return what ? <p>{tr("results.pop.did", { what: what.value })}</p> : null;
              })()}
              <button type="button" className="btn btn-secondary" onClick={() => onExplain(opened.code as string)} data-testid="amap-pop-more">
                {tr("results.pop.more")}
              </button>
            </>
          ) : (
            <p className="muted">{tr(`results.pop.state_${opened.kind}` as Key)}</p>
          )}
        </div>
      ) : null}

      {map.absent.length > 0 ? <p className="muted">{tr("results.map.absent", { n: map.absent.length })}</p> : null}
      {map.notEntered > 0 ? <p className="muted">{tr("results.map.not_entered", { n: map.notEntered })}</p> : null}
      <p className="muted" data-testid="amap-local">
        {tr("results.map.local")}
      </p>
    </div>
  );
}
