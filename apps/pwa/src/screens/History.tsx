// Where she can see everything she has entered on this phone: her checks (typed or from photos), whether
// their class counts were sent, her rehearsals and the observations she sent. Per-child answers stay here.
import { useEffect, useState } from "react";
import { listChecks, type CheckSummary } from "../lib/history";
import { db } from "../lib/db";
import { href } from "../lib/router";
import { BLANK, UNREADABLE } from "../lib/check";
import { useApp } from "../state";

export default function History() {
  const { tr, lang } = useApp();
  const [checks, setChecks] = useState<CheckSummary[] | null>(null);
  const [rehearsals, setRehearsals] = useState(0);
  const [observations, setObservations] = useState({ total: 0, waiting: 0 });
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      setChecks(await listChecks());
      const rows = await db.transcripts.toArray();
      setRehearsals(rows.filter((r) => r.turns.length > 0).length);
      const obs = rows.filter((r) => r.observation);
      setObservations({ total: obs.length, waiting: obs.filter((r) => !r.observation?.sent).length });
    })();
  }, []);

  if (checks === null) return <p role="status">{tr("common.loading")}</p>;
  const when = (ms: number) => new Date(ms).toLocaleString(lang, { dateStyle: "medium", timeStyle: "short" });
  const cell = (c: string) => (c === "" ? "–" : c === BLANK ? tr("check.value_blank") : c === UNREADABLE ? "?" : c);

  return (
    <section aria-labelledby="hi-title" data-testid="history">
      <h1 id="hi-title">{tr("history.title")}</h1>
      <p className="muted">{tr("history.private")}</p>

      <h2>{tr("history.checks")}</h2>
      {checks.length === 0 ? (
        <p data-testid="history-empty">{tr("history.empty")}</p>
      ) : (
        <ul className="plain">
          {checks.map((c) => (
            <li key={c.id} className="card" data-testid="history-check">
              <p>
                <strong>{tr("history.check_line", { term: c.term, form: c.formKey, n: c.children })}</strong>
              </p>
              <p className="muted">{when(c.updatedAt)}</p>
              <p className="muted">{c.viaPhoto > 0 ? tr("history.photo_n", { n: c.viaPhoto }) : tr("history.typed")}</p>
              <p data-testid="history-state">{tr(`history.state.${c.state}` as "history.state.sent")}</p>
              <button type="button" className="btn btn-secondary" aria-expanded={open === c.id} onClick={() => setOpen(open === c.id ? null : c.id)} data-testid="history-toggle">
                {open === c.id ? tr("history.hide") : tr("history.show")}
              </button>
              {open === c.id ? (
                <div className="table-scroll">
                  <table data-testid="history-table">
                    <thead>
                      <tr>
                        <th>{tr("history.child_col")}</th>
                        {c.rows[0]?.map((_, i) => <th key={i}>{i + 1}</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {c.rows.map((r, k) => (
                        <tr key={k}>
                          <th>{k + 1}</th>
                          {r.map((v, i) => <td key={i}>{cell(v)}</td>)}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}
            </li>
          ))}
        </ul>
      )}
      <a className="btn btn-secondary" href={href("/check")}>
        {tr("history.open_check")}
      </a>

      <h2>{tr("history.practice")}</h2>
      <p data-testid="history-rehearsals">{tr("history.rehearsals", { n: rehearsals })}</p>
      <p data-testid="history-observations">{tr("history.observations", { n: observations.total, w: observations.waiting })}</p>
      <a className="btn btn-secondary" href={href("/practice")}>
        {tr("history.open_review")}
      </a>

      <p className="muted">{tr("history.server_note")}</p>
    </section>
  );
}
