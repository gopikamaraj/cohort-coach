// "Create a cohort": a coach or the programme officer groups the entered classes that show the same mistake.
// The server adds the counts up (nothing here computes them) and needs at least two classes. The officer sees
// no class or teacher names, only how many classes show each mistake.
import { ErrorRuleControl, RuleLine } from "./ErrorRuleControl";
import { ruleQuery, useErrorRule } from "../lib/errorRule";
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
  rule?: { min_hits: number };
}
interface Cand {
  ref: string;
  label: string;
  children: number;
  children_checked: number;
}
interface Caps {
  off: boolean;
  label: string | null;
  min_cohort_classes: number;
}
interface Seen {
  class?: string;
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
  const [rule] = useErrorRule();
  const [cands, setCands] = useState<Cand[]>([]); // the officer's list: anonymous labels and counts only
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [caps, setCaps] = useState<Caps | null>(null);
  const [done, setDone] = useState<Row | null>(null);
  const load = () => {
    fetch(`${API_BASE}/api/store/coach-summary?${ruleQuery(rule)}`, { headers: { "X-Role": who } })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((d) => setSeen((d as { classes: Seen[] }).classes))
      .catch(() => setSeen([]));
    ccall<Row[]>(`/class-only/${who}`, who)
      .then((rows) => setMade(rows.filter((r) => r.scope === "coach")))
      .catch(() => setMade([]));
  };
  useEffect(load, [who, rule]);
  const byError = (e: string) => seen.filter((c) => c.errors.includes(e)); // each class by its most recent check
  const loadCands = (e: string) => {
    ccall<{ classes: Cand[]; caps: Caps }>(`/class-only/officer/candidates?error=${encodeURIComponent(e)}&${ruleQuery(rule)}`, who)
      .then((d) => {
        setCands(d.classes);
        setCaps(d.caps);
        setPicked(new Set(d.classes.map((c) => c.ref)));
      })
      .catch(() => setCands([]));
  };
  useEffect(() => {
    if (who === "officer" && code) loadCands(code);
  }, [rule]);
  const need = who === "officer" ? (caps?.min_cohort_classes ?? 2) : 2;
  const enough = code !== "" && (who === "officer" ? picked.size >= need : byError(code).length >= 2);
  const pick = (e: string) => {
    setCode(e);
    setName(tr(`err.${e}` as Key));
    setMsg("");
    setDone(null);
    if (who === "officer") loadCands(e);
  };
  async function create() {
    setBusy(true);
    try {
      const made = await ccall<Row>(`/class-only/${who}`, who, { method: "POST", body: { name, error: code, language: lang, min_hits: rule, ...(who === "officer" ? { class_refs: [...picked] } : {}) } });
      if (who === "officer") setDone(made);
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
      <ErrorRuleControl name={`rule-${who}-make`} />
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
          {who === "officer" ? (
            <fieldset className="stack" data-testid="officer-classes">
              <legend>{tr("officer.make.classes")}</legend>
              {caps?.off ? <p className="note" data-testid="demo-caps">{caps.label}</p> : null}
              <label className="check-line">
                <input type="checkbox" checked={cands.length > 0 && picked.size === cands.length} onChange={(e) => setPicked(e.target.checked ? new Set(cands.map((c) => c.ref)) : new Set())} data-testid="officer-select-all" /> <span>{tr("officer.make.select_all")}</span>
              </label>
              {cands.map((c) => (
                <label key={c.ref} className="check-line">
                  <input type="checkbox" checked={picked.has(c.ref)} onChange={(e) => setPicked((p) => { const n = new Set(p); if (e.target.checked) n.add(c.ref); else n.delete(c.ref); return n; })} data-testid={`officer-class-${c.label.replace("Class ", "")}`} />{" "}
                  <span>{tr("officer.make.class_row", { label: c.label, n: c.children })}</span>
                </label>
              ))}
            </fieldset>
          ) : null}
          <label>
            {tr("coach.make.name")}
            <input type="text" value={name} maxLength={80} onChange={(e) => setName(e.target.value)} data-testid="coach-cohort-name" />
          </label>
          {!enough ? <p className="muted">{tr(need > 1 ? "coach.make.need_two" : "officer.make.need_one")}</p> : null}
          {msg ? <p role="alert">{msg}</p> : null}
          <button type="button" className="btn btn-primary" disabled={busy || !enough || name.trim() === ""} onClick={() => void create()} data-testid="coach-cohort-create">
            {tr("coach.make.create")}
          </button>
        </>
      ) : null}
      {done ? <p role="status" data-testid="officer-made">{tr("officer.make.done", { n: done.classes })}</p> : null}
      {made.length > 0 ? (
        <>
          <h3>{tr("coach.make.list")}</h3>
          <ul className="plain" data-testid="coach-cohorts">
            {made.map((m) => (
              <li key={m.id}>
                {tr("coach.make.row", { name: m.name, classes: m.classes, n: m.counts[m.errors[0] ?? ""] ?? 0, total: m.children_checked })}
                <RuleLine minHits={m.rule?.min_hits} />
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}
