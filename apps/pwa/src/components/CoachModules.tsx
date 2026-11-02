// The coach's view of a cohort's modules: for each module, how many are at it, have it made and downloaded, what
// they answered (counts only), what is overdue or failed, and a way to move the remaining dates (a holiday).
// No teacher, no name and no child appears: the server sends counts. Dates of modules already made cannot move.
import { useEffect, useState } from "react";
import { coachGenerate, coachModules, coachShift, type CoachModules as Counts } from "../lib/modules";
import { useApp } from "../state";
import { useToast } from "./toast";

export function CoachModules({ cohortId }: { cohortId: string }) {
  const { tr } = useApp();
  const toast = useToast();
  const [data, setData] = useState<Counts | null>(null);
  const [days, setDays] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let live = true;
    coachModules(cohortId).then(
      (d) => live && setData(d),
      () => live && setData(null),
    );
    return () => {
      live = false;
    };
  }, [cohortId]);

  if (!data || data.tracks === 0) {
    return data ? (
      <p className="muted" data-testid={`coach-modules-none-${cohortId}`}>
        {tr("module.coach.none")}
      </p>
    ) : null;
  }

  const shift = async () => {
    const n = Number.parseInt(days, 10);
    if (!Number.isFinite(n) || n === 0 || !reason.trim()) return;
    setBusy(true);
    try {
      const got = await coachShift(cohortId, n, reason.trim());
      setData(got);
      toast(tr("module.coach.moved", { n: got.moved ?? 0 }));
      setDays("");
      setReason("");
    } catch {
      toast(tr("module.err"));
    } finally {
      setBusy(false);
    }
  };
  const generate = async () => {
    setBusy(true);
    try {
      setData(await coachGenerate(cohortId));
    } catch {
      toast(tr("module.err"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="stack coach-modules" data-testid={`coach-modules-${cohortId}`}>
      <h3>{tr("module.coach.title")}</h3>
      <div className="table-scroll">
        <table className="coach-table">
          <thead>
            <tr>
              <th scope="col">#</th>
              <th scope="col">{tr("module.coach.at")}</th>
              <th scope="col">{tr("module.coach.made")}</th>
              <th scope="col">{tr("module.coach.downloaded")}</th>
              <th scope="col">{tr("module.coach.worked")}</th>
              <th scope="col">{tr("module.coach.partly")}</th>
              <th scope="col">{tr("module.coach.not_yet")}</th>
              <th scope="col">{tr("module.coach.not_tried")}</th>
              <th scope="col">{tr("module.coach.overdue")}</th>
              <th scope="col">{tr("module.coach.failed")}</th>
              <th scope="col">{tr("module.coach.flag")}</th>
            </tr>
          </thead>
          <tbody>
            {data.modules.map((m) => (
              <tr key={m.number} data-testid={`coach-module-${m.number}`}>
                <th scope="row">{m.number}</th>
                <td>{m.at}</td>
                <td>{m.generated}</td>
                <td>{m.downloaded}</td>
                <td>{m.feedback.worked}</td>
                <td>{m.feedback.partly}</td>
                <td>{m.feedback.not_yet}</td>
                <td>{m.feedback.not_tried}</td>
                <td>{m.overdue}</td>
                <td>{m.failed}</td>
                <td>{m.not_downloaded_flag}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data.stopped.cap + data.stopped.exhausted > 0 ? <p>{tr("module.coach.stopped", { cap: data.stopped.cap, exhausted: data.stopped.exhausted })}</p> : null}
      <fieldset className="module-shift">
        <legend>{tr("module.coach.shift")}</legend>
        <label className="field">
          <span>{tr("module.coach.days")}</span>
          <input type="number" inputMode="numeric" min={-60} max={60} value={days} onChange={(e) => setDays(e.target.value)} data-testid="coach-shift-days" />
        </label>
        <label className="field">
          <span>{tr("module.coach.reason")}</span>
          <input type="text" maxLength={120} value={reason} onChange={(e) => setReason(e.target.value)} data-testid="coach-shift-reason" />
        </label>
        <p className="muted">{tr("module.coach.fixed")}</p>
        <div className="pack-actions">
          <button type="button" className="btn btn-secondary" disabled={busy || !days || !reason.trim()} onClick={() => void shift()} data-testid="coach-shift-apply">
            {tr("module.coach.apply")}
          </button>
          <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => void generate()} data-testid="coach-generate">
            {tr("module.coach.generate")}
          </button>
        </div>
      </fieldset>
    </div>
  );
}
