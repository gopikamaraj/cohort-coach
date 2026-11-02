// Before and after: two checks of one class set side by side. Children are matched on this phone by
// roll order and only counts are shown (never a child, never a percentage). The default pair is the
// latest two checks; she can pick any two with the switcher.
import { useEffect, useMemo, useState } from "react";
import { db, type CheckRow } from "../lib/db";
import { COMPETENCIES, formatDate, formName, kindName, pairChecks } from "../lib/checks";
import { enteredChildren } from "../lib/check";
import { useApp } from "../state";

const byDate = (a: CheckRow, b: CheckRow) => (a.checkDate ?? "").localeCompare(b.checkDate ?? "") || a.updatedAt - b.updatedAt;

/** `hideWhenEmpty`: show nothing until there are two checks to compare (the class findings screen,
 *  where a lone "nothing to compare yet" line reads as one more finding). */
export function BeforeAfter({ hideWhenEmpty = false }: { hideWhenEmpty?: boolean } = {}) {
  const { tr, lang, klass, check } = useApp();
  const [rows, setRows] = useState<CheckRow[]>([]);
  const [pick, setPick] = useState<{ from: string; to: string } | null>(null);

  useEffect(() => {
    const id = klass?.id;
    if (!id) return;
    void db.checks.where("classId").equals(id).toArray().then((all) => setRows(all.filter((c) => enteredChildren(c.children).length > 0).sort(byDate)));
  }, [klass?.id, check]);

  const from = rows.find((c) => c.id === pick?.from) ?? rows[rows.length - 2];
  const to = rows.find((c) => c.id === pick?.to) ?? rows[rows.length - 1];
  const result = useMemo(() => (from && to && from.id !== to.id ? pairChecks(from.formKey, from.children, to.formKey, to.children, new Set(from.absent ?? []), new Set(to.absent ?? [])) : null), [from, to]);

  const name = (c: CheckRow) => `${kindName(tr, c.kind ?? "pre")} ${formName(tr, c)} (${c.checkDate ? formatDate(c.checkDate, lang) : "—"})`;
  if (hideWhenEmpty && (!result || !from || !to)) return null;
  const option = (c: CheckRow) => tr("ba.check_option", { kind: kindName(tr, c.kind ?? "pre"), f: formName(tr, c), date: c.checkDate ? formatDate(c.checkDate, lang) : "—" });

  return (
    <section aria-labelledby="ba-title" data-testid="before-after">
      <h2 id="ba-title">{tr("ba.title")}</h2>
      {klass?.simulated ? <p className="chip" data-testid="ba-demo">{tr("ba.demo")}</p> : null}
      {!result || !from || !to ? (
        <p data-testid="ba-none">{tr("ba.none")}</p>
      ) : (
        <>
          {rows.length > 2 ? (
            <div className="row">
              <label className="field">
                <span>{tr("ba.from")}</span>
                <select value={from.id} onChange={(e) => setPick({ from: e.target.value, to: to.id })} data-testid="ba-from">
                  {rows.map((c) => (
                    <option key={c.id} value={c.id}>
                      {option(c)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>{tr("ba.to")}</span>
                <select value={to.id} onChange={(e) => setPick({ from: from.id, to: e.target.value })} data-testid="ba-to">
                  {rows.map((c) => (
                    <option key={c.id} value={c.id}>
                      {option(c)}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          ) : null}
          <p data-testid="ba-label">
            <strong>{tr("ba.label", { a: name(from), b: name(to) })}</strong>
          </p>
          <div className="table-scroll" role="region" tabIndex={0} aria-label={tr("ba.title")}>
            <table data-testid="ba-table">
              <thead>
                <tr>
                  <th>{tr("ba.col_skill")}</th>
                  <th>{tr("ba.col_before")}</th>
                  <th>{tr("ba.col_fixed")}</th>
                  <th>{tr("ba.col_still")}</th>
                  <th>{tr("ba.col_new")}</th>
                </tr>
              </thead>
              <tbody>
                {Object.keys(COMPETENCIES).map((c) => {
                  const ch = result.by_competency[c];
                  if (!ch) return null;
                  const skill = tr(`ba.${c}` as "ba.C1");
                  return (
                    <tr key={c} data-testid={`ba-row-${c}`}>
                      <th scope="row">{skill}</th>
                      <td>{ch.flagged_before}</td>
                      <td>{ch.fixed}</td>
                      <td>{ch.still_flagged}</td>
                      <td>{ch.newly_flagged}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <ul className="plain ba-bars">
            {Object.keys(COMPETENCIES).map((c) => {
              const ch = result.by_competency[c];
              if (!ch || ch.flagged_before === 0) return null;
              const skill = tr(`ba.${c}` as "ba.C1");
              return (
                <li key={c} data-testid={`ba-bar-${c}`}>
                  <span>{tr("ba.bar_label", { skill, fixed: ch.fixed, before: ch.flagged_before })}</span>
                  <span className="ba-track" role="img" aria-label={tr("ba.bar_label", { skill, fixed: ch.fixed, before: ch.flagged_before })}>
                    <span className="ba-fill" style={{ width: `${(ch.fixed / ch.flagged_before) * 100}%` }} />
                  </span>
                </li>
              );
            })}
          </ul>
          <p className="muted" data-testid="ba-paired">
            {tr("ba.paired", { n: result.paired, x: result.excluded_absent + result.excluded_not_entered + result.excluded_unmatched })}
          </p>
          {result.small_sample ? <p data-testid="ba-small">{tr("ba.small")}</p> : null}
          <p className="muted">{tr("ba.counts_note")}</p>
        </>
      )}
    </section>
  );
}
