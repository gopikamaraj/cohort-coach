// The officer's weekly view: the error map, the funnel and the track results. Aggregates only, every
// figure with its source, nothing covering fewer than 5 classes or teachers. The numbers are computed
// by the server from class-level counts; this screen only shows them. A failed track counts against the
// track, not the teacher. Percentages appear here (an officer view) and nowhere a teacher sees.
import { useEffect, useState } from "react";
import { Icon } from "../components/icons";
import OfficerCohorts from "../components/OfficerCohorts";
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
  min_classes: number;
  lowered: boolean;
  terms: number[];
  error_map: { term: number | null; classes: number; cells: { error: string; hidden: boolean; classes?: number; showing?: number; share_percent?: number; children_showing?: number; children_checked?: number }[] };
  results: { classes: number; hidden: boolean; rows: { error: string; before: number; before_of: number; after: number; after_of: number; fall_points: number | null }[] };
}

/** The classes that really entered a check (3A, 3B, ...): error map, track results and what of the funnel is counted. */
function EnteredOfficer() {
  const { tr } = useApp();
  const [d, setD] = useState<Entered | null>(null);
  useEffect(() => {
    get<Entered>("entered").then(setD, () => setD(null));
  }, []);
  if (!d || d.terms.length === 0) return null;
  return (
    <div className="panel" data-testid="officer-entered">
      <h2>{tr("officer.real.title")}</h2>
      <p className="muted">{tr("officer.real.note", { classes: d.error_map.classes, term: d.error_map.term ?? 1 })}</p>
      {d.lowered ? <p className="note">{tr("officer.real.lowered")}</p> : null}
      <h3>{tr("officer.real.map")}</h3>
      <ul className="plain" data-testid="entered-map">
        {d.error_map.cells.map((c) => (
          <li key={c.error}>
            <strong>{tr(`err.${c.error}` as Key)}</strong>:{" "}
            {c.hidden ? tr("officer.real.hidden", { min: d.min_classes }) : tr("officer.real.map_row", { pct: `${c.share_percent ?? 0}%`, showing: c.showing ?? 0, classes: c.classes ?? 0, n: c.children_showing ?? 0, total: c.children_checked ?? 0 })}
          </li>
        ))}
      </ul>
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

  useEffect(() => {
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
      <p className="note">
        <Icon name="shield" size={18} /> {tr("officer.rule")}
      </p>
      {failed ? (
        <p role="alert" className="banner">
          {tr("officer.error")}
        </p>
      ) : null}

      <EnteredOfficer />

      <OfficerCohorts />

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
