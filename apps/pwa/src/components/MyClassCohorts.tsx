// The teacher's own cohort(s) of one class on the cohort page: the label, what it works on, and the
// intervention pack built from her results. The coach's list shows the same cohorts in counts only.
import { RuleLine } from "./ErrorRuleControl";
import { useEffect, useState } from "react";
import type { Key } from "../i18n";
import { forCoach, readAll, syncPending, type ClassCohort, type CoachRow } from "../lib/classCohort";
import { href } from "../lib/router";
import { useApp } from "../state";
import { CoachModules } from "./CoachModules";
import { InterventionPack } from "./InterventionPack";

export function MyClassCohorts() {
  const { tr, lang, online } = useApp();
  const [rows, setRows] = useState<ClassCohort[]>(readAll);
  const [pick, setPick] = useState<string | null>(null);
  useEffect(() => {
    if (online) void syncPending(lang).then(() => setRows(readAll()));
  }, [online, lang]);
  const current = rows.find((r) => r.id === pick) ?? rows[0];
  return (
    <section className="stack" data-testid="my-class-cohorts" aria-labelledby="mine-title">
      <h2 id="mine-title">{tr("cohort.mine.section")}</h2>
      {rows.length === 0 ? (
        <p className="muted" data-testid="mine-none">
          {tr("cohort.mine.none")} <a href={href("/cards")}>{tr("nav.cards")}</a>
        </p>
      ) : (
        <>
          {rows.length > 1 ? (
            <div className="subtabs" role="group" aria-label={tr("cohort.mine.section")}>
              {rows.map((r) => (
                <button key={r.id} type="button" className={r === current ? "subtab subtab-on" : "subtab"} aria-pressed={r === current} onClick={() => setPick(r.id)}>
                  {r.name}
                </button>
              ))}
            </div>
          ) : null}
          {current ? (
            <div className="card stack" data-testid="mine-card">
              <p>
                <strong>{current.name}</strong>
              </p>
              <p>
                <span className="chip" data-testid="mine-label">
                  {tr("cohort.mine.label")}
                </span>
              </p>
              <p>{tr("cohort.mine.errors_line", { names: current.errors.map((c) => tr(`err.${c}` as Key)).join("; ") })}</p>
              <RuleLine minHits={current.rule} />
              {!current.synced ? <p className="muted">{tr("cohort.mine.saved_here")}</p> : null}
            </div>
          ) : null}
          {current ? <InterventionPack cohort={current} /> : null}
        </>
      )}
    </section>
  );
}

/** The coach's Cohorts view: cohorts of one class, in counts, each labelled. */
export function ClassOnlyForCoach() {
  const { tr } = useApp();
  const [rows, setRows] = useState<CoachRow[] | null>(null);
  useEffect(() => {
    void forCoach().then(setRows, () => setRows([]));
  }, []);
  return (
    <section className="stack" data-testid="class-only-coach" aria-labelledby="co-one">
      <h2 id="co-one">{tr("cohort.mine.coach_title")}</h2>
      {rows && rows.length === 0 ? <p className="muted">{tr("cohort.mine.coach_none")}</p> : null}
      <ul className="plain">
        {(rows ?? []).map((r) => (
          <li key={r.id} className="card" data-testid={`class-only-${r.id}`}>
            <p>{tr("cohort.mine.coach_line", { name: r.name, total: r.children_checked })}</p>
            <p>
              <span className="chip">{tr("cohort.mine.label")}</span>
            </p>
            <p className="muted">{r.errors.map((c) => `${tr(`err.${c}` as Key)}: ${r.counts[c] ?? 0}`).join(" · ")}</p>
            <CoachModules cohortId={r.id} />
          </li>
        ))}
      </ul>
    </section>
  );
}
