// Testing evidence (judge mode): live counts of the people who agreed to share, what they said, and
// what we changed. All numbers come from the server; empty data shows empty states, never placeholders.
// Every chart is inline SVG with a text version beside it.
import { useEffect, useState } from "react";
import type { Key } from "../i18n";
import { loadEvidence, percent, stageLabel, type Evidence } from "../lib/testingEvidence";
import { useJudge } from "../lib/roles";
import { useApp } from "../state";

type Row = { label: string; value: number };

/** A horizontal bar chart in SVG. The same numbers are listed as text for a screen reader. */
function Bars({ title, rows, testid }: { title: string; rows: Row[]; testid: string }) {
  const { tr } = useApp();
  const max = Math.max(1, ...rows.map((r) => r.value));
  const h = 30;
  return (
    <figure className="te-chart" data-testid={testid}>
      <figcaption>
        <strong>{title}</strong>
      </figcaption>
      {rows.length === 0 ? (
        <p className="muted">{tr("tester.ev.empty_chart")}</p>
      ) : (
        <>
          <svg role="img" aria-label={`${title}: ${rows.map((r) => `${r.label} ${r.value}`).join(", ")}`} viewBox={`0 0 100 ${rows.length * h}`} preserveAspectRatio="none" className="te-svg" style={{ height: rows.length * h }}>
            {rows.map((r, i) => (
              <rect key={r.label} x="0" y={i * h + 4} width={Math.max(r.value > 0 ? 1 : 0, (r.value / max) * 100)} height={h - 10} className="te-bar" />
            ))}
          </svg>
          <ul className="te-rows" aria-label={tr("tester.ev.chart_text")}>
            {rows.map((r) => (
              <li key={r.label}>
                <span>{r.label}</span>
                <b>{r.value}</b>
              </li>
            ))}
          </ul>
        </>
      )}
    </figure>
  );
}

function Card({ label, value, testid }: { label: string; value: string; testid: string }) {
  return (
    <div className="te-card" data-testid={testid}>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

export default function TestingEvidence({ embedded = false }: { embedded?: boolean }) {
  const { tr } = useApp();
  const judge = useJudge();
  const [flagged, setFlagged] = useState(false);
  const [data, setData] = useState<Evidence | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!judge) return;
    let live = true;
    setFailed(false);
    loadEvidence(flagged).then(
      (d) => live && setData(d),
      () => live && setFailed(true),
    );
    return () => {
      live = false;
    };
  }, [judge, flagged]);

  if (!judge || failed) {
    return (
      <section aria-labelledby="te-title" data-testid="testing-evidence">
        {embedded ? null : <h1 id="te-title">{tr("tester.ev.title")}</h1>}
        <p role="status">{tr("tester.ev.unavailable")}</p>
      </section>
    );
  }
  if (!data) {
    return (
      <section aria-labelledby="te-title" data-testid="testing-evidence">
        <p role="status">{tr("tester.ev.loading")}…</p>
      </section>
    );
  }
  const c = data.cards;
  const none = tr("tester.ev.none");
  const stage = (s: string): string => {
    const l = stageLabel(s);
    return l.key === "step" ? tr("tester.ev.stage.step", { n: l.n ?? 0 }) : tr(`tester.ev.stage.${l.key}` as Key);
  };
  const H = embedded ? "h3" : "h2";
  return (
    <section aria-labelledby="te-title" data-testid="testing-evidence">
      {embedded ? null : <h1 id="te-title">{tr("tester.ev.title")}</h1>}
      <p>{tr("tester.ev.intro")}</p>
      <p role="status" data-testid="te-range">
        {c.date_from && c.date_to ? tr("tester.ev.range", { from: c.date_from, to: c.date_to }) : tr("tester.ev.no_range")}
      </p>

      <dl className="te-cards">
        <Card testid="te-testers" label={tr("tester.ev.c.testers")} value={String(c.testers)} />
        <Card testid="te-sessions" label={tr("tester.ev.c.sessions")} value={String(c.sessions)} />
        <Card testid="te-returning" label={tr("tester.ev.c.returning")} value={String(c.returning_testers)} />
        <Card testid="te-roles" label={tr("tester.ev.c.roles")} value={c.roles_tried_avg === null ? none : String(c.roles_tried_avg)} />
        <Card testid="te-tours" label={tr("tester.ev.c.tours")} value={String(c.tours_completed)} />
        <Card testid="te-feedback" label={tr("tester.ev.c.feedback")} value={String(c.feedback_received)} />
        <Card testid="te-rating" label={tr("tester.ev.c.rating")} value={c.average_rating === null ? none : `${c.average_rating} / 5`} />
        <Card testid="te-offline" label={tr("tester.ev.c.offline")} value={c.offline_share === null ? none : percent(c.offline_share)} />
      </dl>

      <Bars testid="te-days" title={tr("tester.ev.ch.days")} rows={data.testers_by_day.map((d) => ({ label: d.day, value: d.testers }))} />
      <Bars testid="te-role-funnel" title={tr("tester.ev.ch.roles")} rows={data.role_funnel.map((r) => ({ label: stage(r.stage), value: r.testers }))} />
      <Bars testid="te-tour-funnel" title={tr("tester.ev.ch.tour")} rows={data.tour_funnel.map((r) => ({ label: stage(r.stage), value: r.testers }))} />
      <Bars testid="te-source" title={tr("tester.ev.ch.source")} rows={data.by_source.map((r) => ({ label: r.label, value: r.testers }))} />
      <Bars testid="te-device" title={tr("tester.ev.ch.device")} rows={data.device_class.map((r) => ({ label: r.label, value: r.testers }))} />
      <Bars testid="te-language" title={tr("tester.ev.ch.language")} rows={data.language.map((r) => ({ label: r.label, value: r.testers }))} />

      <H>{tr("tester.ev.t.title")}</H>
      {data.testers.length === 0 ? (
        <p className="muted" data-testid="te-testers-empty">{tr("tester.ev.none")}</p>
      ) : (
        <div className="table-scroll" tabIndex={0} role="region" aria-label={tr("tester.ev.t.title")}>
          <table data-testid="te-table">
            <thead>
              <tr>
                {(["name", "device", "roles", "tours", "features", "sessions", "last", "rating"] as const).map((k) => (
                  <th key={k} scope="col">{tr(`tester.ev.t.${k}` as Key)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.testers.map((t) => (
                <tr key={t.hash6 + t.name}>
                  <td>{t.listed ? t.name : t.name.replace(/Anonymous tester (\d+)/, (_m, n: string) => tr("tester.ev.t.anon", { n }))}</td>
                  <td><code>{t.hash6}</code></td>
                  <td>{t.roles_tried}</td>
                  <td>{t.tours_completed}</td>
                  <td>{t.features_used}</td>
                  <td>{t.sessions}</td>
                  <td>{t.last_seen}</td>
                  <td>{t.rating ?? "–"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <H>{tr("tester.ev.f.title")}</H>
      {data.feedback.length === 0 ? (
        <p className="muted" data-testid="te-feedback-empty">{tr("tester.ev.f.none")}</p>
      ) : (
        <ul className="plain te-feedback" data-testid="te-feedback-list">
          {data.feedback.map((f, i) => (
            <li key={i} className="panel">
              <p>
                <strong>{tr("tester.ev.f.rating", { n: f.rating })}</strong>
                {f.role ? <span className="chip"> {f.role}</span> : null}
                {f.tags.map((t) => (
                  <span key={t} className="chip"> {tr(`tester.tag.${t}` as Key)}</span>
                ))}
              </p>
              <p>{f.comment ?? <span className="muted">{tr("tester.ev.f.no_comment")}</span>}</p>
            </li>
          ))}
        </ul>
      )}

      <H>{tr("tester.ev.c2.title")}</H>
      {data.changes.length === 0 ? (
        <p className="muted" data-testid="te-changes-empty">{tr("tester.ev.c2.none")}</p>
      ) : (
        <ul className="plain" data-testid="te-changes">
          {data.changes.map((r, i) => (
            <li key={i} className="panel">
              <p className="muted">{r.date}{r.commit ? ` · ${r.commit}` : ""}</p>
              <p><strong>{tr("tester.ev.c2.said")}:</strong> {r.feedback}</p>
              <p><strong>{tr("tester.ev.c2.did")}:</strong> {r.change}</p>
            </li>
          ))}
        </ul>
      )}

      <H>{tr("tester.ev.notes.title")}</H>
      <p data-testid="te-excluded">{tr("tester.ev.notes.excluded", { judge: data.excluded.judge_devices, team: data.excluded.team_devices })}</p>
      <label className="switch">
        <input type="checkbox" checked={flagged} onChange={(e) => setFlagged(e.target.checked)} data-testid="te-include" />
        <span>{tr("tester.ev.notes.toggle")}</span>
      </label>
      <p>{tr("tester.ev.notes.collected")}</p>
      <p>{tr("tester.ev.notes.never")}</p>
    </section>
  );
}
