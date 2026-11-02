// "Create a cohort": a coach or the programme officer groups the entered classes that show the same mistake.
// The server adds the counts up (nothing here computes them) and needs at least two classes. The officer sees
// no class or teacher names, only how many classes show each mistake.
import { useEffect, useState } from "react";
import type { Key } from "../i18n";
import { API_BASE } from "../lib/api";
import { ccall } from "../lib/cohort";
import { useApp } from "../state";

const ERRORS = ["PV-HEARD", "PV-REVERSE", "ADD-NOCARRY", "SUB-SFL", "SUB-NODEC"] as const;

interface Row {
  id: string;
  name: string;
  scope: string;
  errors: string[];
  counts: Record<string, number>;
  children_checked: number;
  classes: number;
}
interface Seen {
  class?: string;
  term: number;
  errors: string[];
}

export function CohortMaker({ who }: { who: "coach" | "officer" }) {
  const { tr, lang } = useApp();
  const [seen, setSeen] = useState<Seen[]>([]);
  const [made, setMade] = useState<Row[]>([]);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const load = () => {
    fetch(`${API_BASE}/api/store/coach-summary`, { headers: { "X-Role": who } })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((d) => setSeen((d as { classes: Seen[] }).classes))
      .catch(() => setSeen([]));
    ccall<Row[]>(`/class-only/${who}`, who)
      .then((rows) => setMade(rows.filter((r) => r.scope === "coach")))
      .catch(() => setMade([]));
  };
  useEffect(load, [who]);
  const latest = Math.max(0, ...seen.map((c) => c.term));
  const byError = (e: string) => seen.filter((c) => c.term === latest && c.errors.includes(e));
  const enough = code !== "" && byError(code).length >= 2;
  const pick = (e: string) => {
    setCode(e);
    setName(tr(`err.${e}` as Key));
    setMsg("");
  };
  async function create() {
    setBusy(true);
    try {
      await ccall(`/class-only/${who}`, who, { method: "POST", body: { name, error: code, language: lang } });
      setCode("");
      load();
    } catch {
      setMsg(tr("coach.make.error"));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel stack" data-testid="coach-make">
      <h2>{tr("coach.make.title")}</h2>
      <p className="muted">{tr("coach.make.note")}</p>
      <fieldset className="stack">
        <legend>{tr("coach.make.pick")}</legend>
        {ERRORS.map((e) => (
          <label key={e} className="check-line">
            <input type="radio" name={`${who}-err`} checked={code === e} onChange={() => pick(e)} data-testid={`coach-pick-${e}`} />{" "}
            {tr("coach.make.pick_line", { name: tr(`err.${e}` as Key), classes: byError(e).length, who: who === "coach" ? byError(e).map((c) => c.class || "?").join(", ") || "-" : "-" })}
          </label>
        ))}
      </fieldset>
      {code ? (
        <>
          <label>
            {tr("coach.make.name")}
            <input type="text" value={name} maxLength={80} onChange={(e) => setName(e.target.value)} data-testid="coach-cohort-name" />
          </label>
          {!enough ? <p className="muted">{tr("coach.make.need_two")}</p> : null}
          {msg ? <p role="alert">{msg}</p> : null}
          <button type="button" className="btn btn-primary" disabled={busy || !enough || name.trim() === ""} onClick={() => void create()} data-testid="coach-cohort-create">
            {tr("coach.make.create")}
          </button>
        </>
      ) : null}
      {made.length > 0 ? (
        <>
          <h3>{tr("coach.make.list")}</h3>
          <ul className="plain" data-testid="coach-cohorts">
            {made.map((m) => (
              <li key={m.id}>{tr("coach.make.row", { name: m.name, classes: m.classes, n: m.counts[m.errors[0] ?? ""] ?? 0, total: m.children_checked })}</li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}
