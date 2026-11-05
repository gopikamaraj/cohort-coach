// The officer's weekly view: the error map, the funnel and the track results. Aggregates only, every
// figure with its source, nothing covering fewer than 5 classes or teachers. The numbers are computed
// by the server from class-level counts; this screen only shows them. A failed track counts against the
// track, not the teacher. Percentages appear here (an officer view) and nowhere a teacher sees.
import { ErrorRuleControl, RuleLine } from "../components/ErrorRuleControl";
import { ruleQuery, useErrorRule } from "../lib/errorRule";
import { useEffect, useState } from "react";
import { Icon } from "../components/icons";
import OfficerCohorts from "../components/OfficerCohorts";
import { CohortMaker } from "../components/CohortMaker";
import { API_BASE } from "../lib/api";
import type { Key } from "../i18n";
import { useApp } from "../state";

interface ReviewWaiting {
  waiting: number;
  over_7_days: number;
  oldest_days: number | null;
  source: string;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}/api/officer/${path}`, { headers: { "X-Role": "officer" } });
  if (!res.ok) throw new Error(String(res.status));
  return (await res.json()) as T;
}

/** The position of a value on a -40..+10 point scale, as a percentage of the chart width. */
export function pos(v: number): number {
  return Math.max(0, Math.min(100, ((v + 40) / 50) * 100));
}

interface Entered {
  rule?: { min_hits: number };
  caps?: { off: boolean; label: string | null };
  min_classes: number;
  lowered: boolean;
  has_data: boolean;
  error_map?: { classes: number; cells: { error: string; hidden: boolean; classes?: number; showing?: number; share_percent?: number; children_showing?: number; children_checked?: number }[] };
  results: { classes: number; hidden: boolean; rows: { error: string; before: number; before_of: number; after: number; after_of: number; fall_points: number | null }[] };
}

/** One button: the server forms a cohort for every mistake that two or more entered classes show. */
function FormCohorts() {
  const { tr } = useApp();
  const [busy, setBusy] = useState(false);
  const [out, setOut] = useState<{ created: { name: string; classes: number }[]; already: number; waiting: string[] } | null>(null);
  const [failed, setFailed] = useState(false);
  const [rule] = useErrorRule();
  async function press() {
    setBusy(true);
    setFailed(false);
    try {
      const res = await fetch(`${API_BASE}/api/cohorts/class-only/form?${ruleQuery(rule)}`, { method: "POST", headers: { "X-Role": "officer" } });
      if (!res.ok) throw new Error(String(res.status));
      setOut((await res.json()) as NonNullable<typeof out>);
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="panel stack" data-testid="form-cohorts">
      <h2>{tr("officer.form.title")}</h2>
      <p className="muted">{tr("officer.form.note")}</p>
      <button type="button" className="btn btn-primary" disabled={busy} onClick={() => void press()} data-testid="form-cohorts-button">
        {tr("officer.form.button")}
      </button>
      {failed ? <p role="alert">{tr("officer.form.failed")}</p> : null}
      {out ? (
        <ul className="plain" data-testid="form-cohorts-result">
          {out.created.map((c) => (
            <li key={c.name}>{tr("officer.form.created", { name: c.name, classes: c.classes })}</li>
          ))}
          {out.already > 0 ? <li>{tr("officer.form.already", { n: out.already })}</li> : null}
          {out.created.length === 0 && out.already === 0 ? <li>{tr("officer.form.none")}</li> : null}
        </ul>
      ) : null}
    </div>
  );
}

/** The classes that really entered a check (3A, 3B, ...): error map, track results and what of the funnel is counted. */
function EnteredOfficer() {
  const { tr } = useApp();
  const [d, setD] = useState<Entered | null>(null);
  const [rule] = useErrorRule();
  useEffect(() => {
    get<Entered>(`entered?${ruleQuery(rule)}`).then(setD, () => setD(null));
  }, [rule]);
  if (!d || !d.has_data) return null;
  return (
    <div className="panel" data-testid="officer-entered">
      <h2>{tr("officer.real.title")}</h2>
      <p className="muted">{tr("officer.real.note", { classes: d.error_map?.classes ?? 0 })}</p>
      <ErrorRuleControl name="rule-officer" />
      <RuleLine minHits={d.rule?.min_hits} />
      {d.caps?.off ? <p className="note" data-testid="demo-caps">{tr("officer.caps.demo")}</p> : null}
      {d.lowered && !d.caps?.off ? <p className="note">{tr("officer.real.lowered")}</p> : null}
      <h3>{tr("officer.real.results")}</h3>
      {d.results.hidden ? <p className="muted">{tr("officer.real.hidden", { min: d.min_classes })}</p> : null}
      {d.results.classes === 0 ? <p>{tr("officer.real.results_none")}</p> : null}
      {d.results.rows.length > 0 ? (
        <>
          <ul className="plain" data-testid="entered-results">
            {d.results.rows.map((r) => (
              <li key={r.error}>{tr("officer.real.results_row", { error: tr(`err.${r.error}` as Key), before: r.before, before_of: r.before_of, after: r.after, after_of: r.after_of, fall: r.fall_points ?? 0 })}</li>
            ))}
          </ul>
          <p className="muted">{tr("officer.real.results_note", { classes: d.results.classes })}</p>
        </>
      ) : null}
    </div>
  );
}

export default function OfficerHome() {
  const { tr } = useApp();
  const [waiting, setWaiting] = useState<ReviewWaiting | null>(null);
  const [failed, setFailed] = useState(false);
  const [demo, setDemo] = useState<boolean | null>(null); // the server says demo mode: every minimum group size is off

  useEffect(() => {
    get<{ caps?: { off: boolean } }>("entered").then((e) => setDemo(Boolean(e.caps?.off)), () => setDemo(null));
    get<{ review_waiting?: ReviewWaiting }>("funnel").then(
      (f) => setWaiting(f.review_waiting ?? null),
      () => setFailed(true),
    );
  }, []);

  return (
    <section aria-labelledby="of-title" data-testid="officer">
      <h1 id="of-title">
        <Icon name="programme" /> {tr("role.officer")}
      </h1>
      {demo !== false ? null : (  /* shown only once the server has said production */
        <p className="note">
          <Icon name="shield" size={18} /> {tr("officer.rule")}
        </p>
      )}
      {failed ? (
        <p role="alert" className="banner">
          {tr("officer.error")}
        </p>
      ) : null}

      <EnteredOfficer />

      <CohortMaker who="officer" />

      <FormCohorts />

      <OfficerCohorts demo={demo === true} />

      {waiting ? (
        <div className="panel" data-testid="funnel">
          <p data-testid="review-waiting">
            {waiting.waiting === 0 ? tr("officer.review_none") : tr("officer.review_waiting", { n: waiting.waiting, m: waiting.over_7_days, d: waiting.oldest_days ?? 0 })}{" "}
            <span className="muted">({waiting.source})</span>
          </p>
        </div>
      ) : null}
    </section>
  );
}
