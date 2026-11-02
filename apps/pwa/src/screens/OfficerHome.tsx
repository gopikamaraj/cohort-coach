// The officer's weekly view: the error map, the funnel and the track results. Aggregates only, every
// figure with its source, nothing covering fewer than 5 classes or teachers. The numbers are computed
// by the server from class-level counts; this screen only shows them. A failed track counts against the
// track, not the teacher. Percentages appear here (an officer view) and nowhere a teacher sees.
import { useEffect, useState } from "react";
import { Icon } from "../components/icons";
import OfficerCohorts from "../components/OfficerCohorts";
import { SimulatedBanner } from "../components/parts";
import { API_BASE } from "../lib/api";
import type { Key } from "../i18n";
import { useApp } from "../state";

interface Cell {
  medium: string;
  error: string;
  hidden: boolean;
  classes: number | null;
  showing?: number;
  share_percent?: number;
}
interface Track {
  version: string;
  verdict: "working" | "not_working" | "inconclusive";
  hidden: boolean;
  reason: string;
  confidence_note: string | null;
  estimate_points?: number | null;
  ci_low?: number | null;
  ci_high?: number | null;
  n_track?: number;
  n_comparison?: number;
}
interface FunnelCell {
  hidden: boolean;
  teachers: number | null;
  source: string;
}
interface ReviewWaiting {
  waiting: number;
  over_7_days: number;
  oldest_days: number | null;
  source: string;
}
interface FunnelRow {
  error: string;
  delivered: FunnelCell;
  tried: FunnelCell;
  outcomes: Record<string, number> | null;
  practised: { recorded: boolean; source: string };
  changed: { status: string; source: string };
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

function IntervalChart({ t, tr }: { t: Track; tr: (k: Key) => string }) {
  if (t.hidden || t.estimate_points == null || t.ci_low == null || t.ci_high == null) return null;
  const zero = pos(0);
  return (
    <svg viewBox="0 0 100 12" role="img" aria-label={`${t.version}: ${t.estimate_points.toFixed(1)} (${t.ci_low.toFixed(1)} to ${t.ci_high.toFixed(1)})`} style={{ width: "100%", maxWidth: 420 }} data-testid={`chart-${t.version}`}>
      <line x1={zero} x2={zero} y1="0" y2="12" stroke="currentColor" strokeDasharray="1 1" strokeWidth="0.4" />
      <line x1={pos(t.ci_low)} x2={pos(t.ci_high)} y1="6" y2="6" stroke="currentColor" strokeWidth="1.2" />
      <circle cx={pos(t.estimate_points)} cy="6" r="1.8" fill="currentColor" />
      <title>{tr("officer.chart_help")}</title>
    </svg>
  );
}

interface Entered {
  min_classes: number;
  lowered: boolean;
  terms: number[];
  error_map: { term: number | null; classes: number; cells: { error: string; hidden: boolean; classes?: number; showing?: number; share_percent?: number; children_showing?: number; children_checked?: number }[] };
  results: { classes: number; hidden: boolean; rows: { error: string; before: number; before_of: number; after: number; after_of: number; fall_points: number | null }[] };
  funnel: { cohorts: { error: string; classes: number }[] };
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
      <h3>{tr("officer.real.funnel")}</h3>
      {d.funnel.cohorts.length === 0 ? <p>{tr("officer.real.funnel_none")}</p> : null}
      <ul className="plain">
        {d.funnel.cohorts.map((c, i) => (
          <li key={i}>{tr("officer.real.funnel_grouped", { n: c.classes, error: tr(`err.${c.error}` as Key) })}</li>
        ))}
      </ul>
      <p className="muted">{tr("officer.real.funnel_wip")}</p>
    </div>
  );
}

export default function OfficerHome() {
  const { tr } = useApp();
  const [map, setMap] = useState<{ cells: Cell[]; simulated: boolean } | null>(null);
  const [res, setRes] = useState<{ tracks: Track[]; note: string } | null>(null);
  const [fun, setFun] = useState<FunnelRow[] | null>(null);
  const [waiting, setWaiting] = useState<ReviewWaiting | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    void Promise.all([get<{ cells: Cell[]; simulated: boolean }>("error-map"), get<{ tracks: Track[]; note: string }>("results"), get<{ rows: FunnelRow[]; review_waiting?: ReviewWaiting }>("funnel")])
      .then(([m, r, f]) => {
        setMap(m);
        setRes(r);
        setFun(f.rows);
        setWaiting(f.review_waiting ?? null);
      })
      .catch(() => setFailed(true));
  }, []);

  const media = [...new Set((map?.cells ?? []).map((c) => c.medium))];
  const errors = [...new Set((map?.cells ?? []).map((c) => c.error))];

  return (
    <section aria-labelledby="of-title" data-testid="officer">
      <h1 id="of-title">
        <Icon name="programme" /> {tr("role.officer")}
      </h1>
      {map?.simulated ? <SimulatedBanner /> : null}
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

      <div className="panel" data-testid="funnel">
        <h2>{tr("officer.funnel")}</h2>
        <p className="muted">{tr("officer.funnel_help")}</p>
        {waiting ? (
          <p data-testid="review-waiting">
            {waiting.waiting === 0 ? tr("officer.review_none") : tr("officer.review_waiting", { n: waiting.waiting, m: waiting.over_7_days, d: waiting.oldest_days ?? 0 })}{" "}
            <span className="muted">({waiting.source})</span>
          </p>
        ) : null}
        {(fun ?? []).map((r) => (
          <div key={r.error} data-testid={`funnel-${r.error}`} className="panel">
            <strong>{r.error}</strong>
            <ul className="plain">
              {(["delivered", "tried"] as const).map((k) => (
                <li key={k}>
                  {tr(`officer.step.${k}` as Key)}: {r[k].hidden ? tr("officer.hidden_teachers") : tr("officer.teachers", { n: r[k].teachers ?? 0 })} <span className="muted">({r[k].source})</span>
                </li>
              ))}
              <li>
                {tr("officer.step.practised")}: {tr("officer.not_counted")} <span className="muted">({r.practised.source})</span>
              </li>
              <li>
                {tr("officer.step.changed")}: {tr(r.changed.status === "awaiting next check" ? "officer.awaiting" : "officer.see_results")} <span className="muted">({r.changed.source})</span>
              </li>
            </ul>
          </div>
        ))}
      </div>

      <div className="panel" data-testid="results">
        <h2>{tr("officer.results")}</h2>
        <p className="muted">{res?.note}</p>
        {(res?.tracks ?? []).map((t) => (
          <div key={t.version} className="panel" data-testid={`track-${t.version}`}>
            <strong>{t.version}</strong>{" "}
            <span className={`chip chip-${t.verdict === "working" ? "positive" : t.verdict === "not_working" ? "negative" : "none"}`} data-testid="verdict">
              {tr(`officer.verdict.${t.verdict}` as Key)}
            </span>
            {t.hidden ? (
              <p className="muted">{tr("officer.fewer_than_5_classes")}</p>
            ) : (
              <>
                <p>
                  {tr("officer.effect", {
                    est: (t.estimate_points ?? 0).toFixed(1),
                    lo: (t.ci_low ?? 0).toFixed(1),
                    hi: (t.ci_high ?? 0).toFixed(1),
                    nt: t.n_track ?? 0,
                    nc: t.n_comparison ?? 0,
                  })}
                </p>
                <IntervalChart t={t} tr={tr} />
              </>
            )}
            {t.confidence_note ? <p className="muted">{t.confidence_note}</p> : null}
            <p className="muted">{tr(`officer.verdict_meaning.${t.verdict}` as Key)}</p>
          </div>
        ))}
      </div>

      <div className="panel" data-testid="error-map">
        <h2>{tr("officer.map")}</h2>
        <p className="muted">{tr("officer.map_help")}</p>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th />
                {media.map((m) => (
                  <th key={m}>{m}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {errors.map((e) => (
                <tr key={e}>
                  <th scope="row">{e}</th>
                  {media.map((m) => {
                    const c = map?.cells.find((x) => x.medium === m && x.error === e);
                    return <td key={m}>{!c || c.hidden ? tr("officer.fewer_than_5_classes") : `${c.share_percent}% (${c.showing}/${c.classes})`}</td>;
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
