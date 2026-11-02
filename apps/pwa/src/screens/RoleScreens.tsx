// Coach (a DIET-like role) and Mentor (one of the teachers). Both are small for now and say plainly what is
// built and what is not. The coach sees aggregates only, from the simulated block; nothing about one class.
import { useEffect, useState } from "react";
import { Icon } from "../components/icons";
import { SimulatedBanner } from "../components/parts";
import { API_BASE } from "../lib/api";
import type { Key } from "../i18n";
import { CohortMaker } from "../components/CohortMaker";
import { useApp } from "../state";

interface EnteredCheck {
  teacher: string;
  id: string;
  data: { kind?: string; term?: number; checkDate?: string; status?: string; entered?: number; absent?: number };
}

/** Every teacher's entered checks as counts: who (a label), which check, how many children, how many absent. */
function EnteredChecks() {
  const { tr, role } = useApp();
  const [rows, setRows] = useState<EnteredCheck[] | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    fetch(`${API_BASE}/api/store/all/checks`, { headers: { "X-Role": role } })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((d) => setRows(d as EnteredCheck[]))
      .catch(() => setFailed(true));
  }, [role]);
  return (
    <section className="panel" aria-labelledby="entered-title" data-testid="entered-checks">
      <h2 id="entered-title">{tr("entered.title")}</h2>
      <p className="muted">{tr("entered.note")}</p>
      {failed ? <p role="alert">{tr("prog.offline")}</p> : null}
      {rows && rows.length === 0 ? <p>{tr("entered.none")}</p> : null}
      {rows && rows.length > 0 ? (
        <div className="table-scroll" role="region" tabIndex={0} aria-label={tr("entered.title")}>
          <table className="mistakes" data-testid="entered-table">
            <thead>
              <tr>
                <th scope="col">{tr("entered.col_teacher")}</th>
                <th scope="col">{tr("entered.col_check")}</th>
                <th scope="col">{tr("entered.col_entered")}</th>
                <th scope="col">{tr("entered.col_absent")}</th>
                <th scope="col">{tr("entered.col_status")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={`${r.teacher}-${r.id}`}>
                  <th scope="row">{r.teacher}</th>
                  <td>{[r.data.kind, r.data.term ? `T${r.data.term}` : null, r.data.checkDate].filter(Boolean).join(" Â· ")}</td>
                  <td>{r.data.entered ?? 0}</td>
                  <td>{r.data.absent ?? 0}</td>
                  <td>{r.data.status ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}

interface Summary {
  terms: Record<string, { classes: number; children_checked: number; children_showing: Record<string, number> }>;
  classes: { teacher: string; class: string; term: number; errors: string[] }[];
}

/** The classes that really entered a check (3A, 3B, ...), added up; and where the coach makes a cohort from them. */
function EnteredClasses() {
  const { tr, role } = useApp();
  const [sum, setSum] = useState<Summary | null>(null);
  const load = () => {
    fetch(`${API_BASE}/api/store/coach-summary`, { headers: { "X-Role": role } })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((d) => setSum(d as Summary))
      .catch(() => setSum(null));
  };
  useEffect(load, [role]);
  if (!sum) return null;
  const label = (n: string) => n || "?";
  return (
    <>
      <section className="panel" data-testid="coach-real">
        <h2>{tr("coach.real.title")}</h2>
        <p className="muted">{tr("coach.real.note")}</p>
        {sum.classes.length === 0 ? <p>{tr("coach.real.none")}</p> : null}
        {Object.entries(sum.terms).map(([term, t]) => (
          <div key={term} data-testid={`coach-real-${term}`}>
            <h3>{tr("coach.real.term", { term, classes: t.classes, total: t.children_checked })}</h3>
            <ul className="plain">
              {ERRORS.map((e) => (
                <li key={e}>
                  <strong>{tr(`err.${e}` as Key)}</strong>: {tr("coach.count", { n: t.children_showing[e] ?? 0, total: t.children_checked })}
                </li>
              ))}
            </ul>
          </div>
        ))}
        {sum.classes.length > 0 ? <p className="muted">{tr("coach.real.classes", { list: sum.classes.map((c) => `${label(c.class)} (${c.teacher}, T${c.term})`).join("; ") })}</p> : null}
      </section>
      <CohortMaker who="coach" />
    </>
  );
}

interface Block {
  classes: number;
  schools: number;
  terms: Record<string, { classes: number; children_checked: number; children_showing: Record<string, number> }>;
}

const ERRORS = ["PV-HEARD", "PV-REVERSE", "ADD-NOCARRY", "SUB-SFL", "SUB-NODEC"] as const;
const MIN_CLASSES = 5; // a figure covering fewer than 5 classes is hidden

export function Coach() {
  const { tr } = useApp();
  const [block, setBlock] = useState<Block | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    fetch(`${API_BASE}/api/demo/block`)
      .then((r) => r.json())
      .then((b) => setBlock(b as Block))
      .catch(() => setFailed(true));
  }, []);
  return (
    <section aria-labelledby="co-title" data-testid="coach">
      <h1 id="co-title">
        <Icon name="coach" /> {tr("coach.title")}
      </h1>
      <SimulatedBanner />
      <p>{tr("coach.intro")}</p>
      {failed ? <p role="alert">{tr("prog.offline")}</p> : null}
      {block ? (
        Object.entries(block.terms).map(([term, t]) => (
          <div key={term} className="panel" data-testid={`coach-${term}`}>
            <h2>{tr("coach.term", { term, classes: t.classes, schools: block.schools })}</h2>
            {t.classes < MIN_CLASSES ? (
              <p>{tr("coach.hidden", { min: MIN_CLASSES })}</p>
            ) : (
              <ul className="plain">
                {ERRORS.map((e) => (
                  <li key={e}>
                    <strong>{tr(`err.${e}` as Key)}</strong>: {tr("coach.count", { n: t.children_showing[e] ?? 0, total: t.children_checked })}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))
      ) : null}
      <EnteredClasses />
      <EnteredChecks />
      <p className="muted">{tr("coach.later")}</p>
    </section>
  );
}

export function Mentor() {
  const { tr } = useApp();
  return (
    <section aria-labelledby="me-title" data-testid="mentor">
      <h1 id="me-title">
        <Icon name="mentor" /> {tr("mentor.title")}
      </h1>
      <SimulatedBanner />
      <p>{tr("mentor.intro")}</p>
      <ol className="steps prog">
        {(["1", "2", "3", "4"] as const).map((n) => (
          <li key={n}>
            <strong>
              <Icon name="mic" size={20} /> {tr(`mentor.step${n}` as "mentor.step1")}
            </strong>
          </li>
        ))}
      </ol>
      <EnteredChecks />
      <p className="muted">{tr("mentor.later")}</p>
    </section>
  );
}
