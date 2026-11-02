// The officer's cohort list: propose a cohort for one error, then move it through its lifecycle.
// The server decides what is allowed (and writes the audit row); this only shows the buttons the
// current status allows and sends the choice. Member and school counts under 5 arrive as null.
import { useCallback, useEffect, useState } from "react";
import { ccall, type CohortSummary } from "../lib/cohort";
import type { Key } from "../i18n";
import { useApp } from "../state";

const NEXT: Record<string, string[]> = {
  proposed: ["active", "cancelled"],
  active: ["closing", "cancelled"],
  closing: ["closed"],
  closed: [],
  cancelled: [],
};

export default function OfficerCohorts() {
  const { tr } = useApp();
  const [rows, setRows] = useState<CohortSummary[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [reason, setReason] = useState<Record<string, string>>({});

  const load = useCallback(() => {
    ccall<CohortSummary[]>("/officer/cohorts", "officer").then(
      (r) => {
        setRows(r);
        setFailed(false);
      },
      () => setFailed(true),
    );
  }, []);
  useEffect(load, [load]);

  async function act(path: string, body: unknown) {
    try {
      await ccall(path, "officer", { method: "POST", body });
      setFailed(false);
      load();
    } catch {
      setFailed(true);
    }
  }
  const move = (id: string, to: string, extra: object = {}) => act(`/officer/cohorts/${id}/status`, { to, ...extra });

  return (
    <div className="panel" data-testid="officer-cohorts">
      <h2>{tr("officer.cohorts")}</h2>
      <p className="muted">{tr("officer.cohorts_help")}</p>
      {/* A coach starts a cohort now (Coach screen); the officer moves existing ones through their lifecycle. */}
      {failed ? (
        <p role="alert" data-testid="cohort-failed">
          {tr("officer.cohort_failed")}
        </p>
      ) : null}
      {rows && rows.length === 0 ? <p className="muted">{tr("officer.cohort_none")}</p> : null}
      <ul className="plain">
        {rows?.map((c) => {
          const r = reason[c.id] ?? "";
          const next = NEXT[c.status] ?? [];
          return (
            <li key={c.id} data-testid={`cohort-${c.id}`}>
              <strong>{c.error}</strong> · {tr(`officer.status_${c.status}` as Key)} · {tr("officer.cohort_members")}:{" "}
              {c.members ?? tr("officer.cohort_hidden")}
              {c.simulated ? ` · ${tr("common.simulated")}` : ""}
              <div>
                {next.includes("active") ? (
                  <button type="button" className="btn btn-secondary" onClick={() => void move(c.id, "active")} data-testid={`activate-${c.id}`}>
                    {tr("officer.cohort_activate")}
                  </button>
                ) : null}
                {next.includes("closing") ? (
                  <button type="button" className="btn btn-secondary" onClick={() => void move(c.id, "closing")} data-testid={`closing-${c.id}`}>
                    {tr("officer.cohort_closing")}
                  </button>
                ) : null}
                {next.includes("closed") ? (
                  <>
                    <button type="button" className="btn btn-secondary" onClick={() => void move(c.id, "closed", { post_test_received: true })} data-testid={`close-post-${c.id}`}>
                      {tr("officer.cohort_close_post")}
                    </button>
                    <label>
                      {tr("officer.cohort_reason")}
                      <input value={r} maxLength={60} onChange={(e) => setReason({ ...reason, [c.id]: e.target.value })} data-testid={`reason-${c.id}`} />
                    </label>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      disabled={!r.trim()}
                      onClick={() => void move(c.id, "closed", { post_test_received: false, reason: r.trim() })}
                      data-testid={`close-without-${c.id}`}
                    >
                      {tr("officer.cohort_close_without")}
                    </button>
                  </>
                ) : null}
                {next.includes("cancelled") ? (
                  <button type="button" className="btn btn-secondary" onClick={() => void move(c.id, "cancelled")} data-testid={`cancel-${c.id}`}>
                    {tr("officer.cohort_cancel")}
                  </button>
                ) : null}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
