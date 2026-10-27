// The officer's weekly view: the error map, the funnel and the track results. Aggregates only, every
// figure with its source, nothing covering fewer than 5 classes or teachers. The numbers are computed
// by the server from class-level counts; this screen only shows them. A failed track counts against the
// track, not the teacher. Percentages appear here (an officer view) and nowhere a teacher sees.
import { useEffect, useState } from "react";
import { Icon } from "../components/icons";
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

export default function OfficerHome() {
  const { tr } = useApp();
  const [map, setMap] = useState<{ cells: Cell[]; simulated: boolean } | null>(null);
  const [res, setRes] = useState<{ tracks: Track[]; note: string } | null>(null);
  const [fun, setFun] = useState<FunnelRow[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    void Promise.all([get<{ cells: Cell[]; simulated: boolean }>("error-map"), get<{ tracks: Track[]; note: string }>("results"), get<{ rows: FunnelRow[] }>("funnel")])
      .then(([m, r, f]) => {
        setMap(m);
        setRes(r);
        setFun(f.rows);
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

      <div className="panel" data-testid="funnel">
        <h2>{tr("officer.funnel")}</h2>
        <p className="muted">{tr("officer.funnel_help")}</p>
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
