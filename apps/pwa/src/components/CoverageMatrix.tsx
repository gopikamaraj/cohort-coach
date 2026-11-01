// "Which items check each error": one row per error, one column per item, a dot where the item checks
// that error, and a count of items. The paper page and the results page both draw it from here, so
// they cannot differ. On the results page the class's own counts are added as a last column, and a
// row or a column can be chosen to mark the same questions in the answer map.
import type { Key } from "../i18n";
import { useApp } from "../state";

export interface MatrixItem {
  n: number;
  extra?: boolean; // an adaptive item
}
export interface MatrixRow {
  code: string;
  items: ReadonlySet<number>;
  assessed: boolean;
  confirmed?: number; // this class: children who show the error
  possible?: number; // this class: children who made it once
}

export function CoverageMatrix({
  rows,
  items,
  testId = "coverage-grid",
  caption,
  withClass = false,
  activeCode = null,
  activeItem = null,
  onCode,
  onItem,
  rowTestPrefix = "coverage-",
}: {
  rows: MatrixRow[];
  items: MatrixItem[];
  testId?: string;
  caption: string;
  withClass?: boolean;
  activeCode?: string | null;
  activeItem?: number | null;
  onCode?: (code: string | null) => void;
  onItem?: (n: number | null) => void;
  rowTestPrefix?: string;
}) {
  const { tr } = useApp();
  const nameOf = (code: string) => tr(`err.${code}` as Key);
  const inActiveRow = (n: number) => activeCode !== null && (rows.find((r) => r.code === activeCode)?.items.has(n) ?? false);
  return (
    <div className="table-scroll coverage-scroll" role="region" tabIndex={0} aria-label={caption}>
      <table className="coverage" data-testid={testId}>
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr>
            <th scope="col" className="cov-code">
              {tr("papers.coverage_col_code")}
            </th>
            {items.map((it) => (
              <th key={it.n} scope="col" className={activeItem === it.n || inActiveRow(it.n) ? "cov-on" : undefined} data-testid={`${testId}-col-${it.n}`}>
                {onItem ? (
                  <button type="button" className="cov-pick" aria-pressed={activeItem === it.n} aria-label={tr("results.why.pick_col", { n: it.n })} onClick={() => onItem(activeItem === it.n ? null : it.n)}>
                    <span className="nowrap">{it.n}</span>
                  </button>
                ) : (
                  <span className="nowrap">{it.n}</span>
                )}
                {it.extra ? <span className="cov-extra">{tr("results.map.extra")}</span> : null}
              </th>
            ))}
            <th scope="col">{tr("papers.coverage_col_count")}</th>
            {withClass ? <th scope="col">{tr("results.why.col_children")}</th> : null}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.code} data-testid={`${rowTestPrefix}${row.code}`} className={activeCode === row.code || (activeItem !== null && row.items.has(activeItem)) ? "cov-row-on" : undefined}>
              <th scope="row" className="cov-code">
                {onCode ? (
                  <button type="button" className="cov-pick cov-pick-row" aria-pressed={activeCode === row.code} aria-label={`${row.code}: ${tr("results.why.pick_row")}`} onClick={() => onCode(activeCode === row.code ? null : row.code)}>
                    <span className="nowrap cov-code-text">{row.code}</span>
                    <span className="cov-name">{nameOf(row.code)}</span>
                  </button>
                ) : (
                  <>
                    <span className="nowrap cov-code-text">{row.code}</span>
                    <span className="cov-name">{nameOf(row.code)}</span>
                  </>
                )}
              </th>
              {items.map((it) => {
                const yes = row.items.has(it.n);
                return (
                  <td key={it.n} className={activeItem === it.n || (activeCode === row.code && yes) ? "cov-on" : undefined}>
                    <span aria-hidden="true">{yes ? "●" : ""}</span>
                    <span className="sr-only">{tr(yes ? "papers.coverage_yes" : "papers.coverage_no", { n: it.n })}</span>
                  </td>
                );
              })}
              <td className="nowrap">{row.assessed ? row.items.size : tr("papers.not_assessed")}</td>
              {withClass ? (
                <td data-testid={`${rowTestPrefix}${row.code}-class`}>
                  {row.assessed ? (
                    row.confirmed || row.possible ? (
                      <>
                        <span className="nowrap">{tr("results.why.confirmed", { n: row.confirmed ?? 0 })}</span>
                        {row.possible ? <span className="cov-name">{tr("results.why.possible", { n: row.possible })}</span> : null}
                      </>
                    ) : (
                      <span className="muted">{tr("results.why.none")}</span>
                    )
                  ) : (
                    <span className="muted">{tr("papers.coverage_not_assessed")}</span>
                  )}
                </td>
              ) : null}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
