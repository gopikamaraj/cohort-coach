// Papers: the check papers of this class with their status and a Print button (teacher), and, for the
// coach who is the reviewer, the papers waiting for review and the paper rules. Papers are made by
// code from approved rules; the server decides who may do what, and this screen shows it.
import { useCallback, useEffect, useState } from "react";
import { Busy } from "../components/Busy";
import { PaperView } from "../components/PaperView";
import { PaperMaker } from "../components/PaperMaker";
import { PaperImport } from "../components/PaperImport";
import { ASSIGNMENT_ENABLED } from "../lib/flags";
import { AssignedToYou, AssignPanel, PaperDetail, sourceLabel, useHubIdentity } from "../components/PaperHubParts";
import { hcall, HubError, type HubPaper } from "../lib/paperHub";
import { suggestForm } from "../lib/checks";
import type { CheckKind } from "../lib/db";
import type { Key } from "../i18n";
import { API_BASE } from "../lib/api";
import { activeClass, db, type CheckRow, type ProfileRow } from "../lib/db";
import { cohortStatus, type Placement } from "../lib/paperStatus";
import { layoutName, pcall, PaperError, type Paper, type PaperRole, type QueueRow, type RuleVersion } from "../lib/papers";
import { href } from "../lib/router";
import { useApp } from "../state";
import { SimulatedBanner } from "../components/parts";

function CreatePaper({ onMade }: { onMade: () => void }) {
  const { tr, klass, slot, reload } = useApp();
  const who = useHubIdentity();
  const [open, setOpen] = useState(false);
  const [route, setRoute] = useState<"rules" | "pdf" | null>(null);
  const [kind, setKind] = useState<CheckKind>("pre");
  const [latest, setLatest] = useState<ProfileRow | null>(null);
  useEffect(() => {
    if (!klass?.id) return;
    void db.profiles.where("classId").equals(klass.id).toArray().then((l) => setLatest([...l].sort((a, b) => b.createdAt - a.createdAt)[0] ?? null));
  }, [klass?.id]);
  const form = suggestForm(kind, []);
  // a fresh phone has no class until she makes something: make it now, as making a paper does
  async function choosePdf() {
    setRoute("pdf");
    if (!klass?.id) {
      await activeClass(false);
      await reload();
    }
  }
  return (
    <section className="stack" aria-labelledby="create-title" data-testid="create-paper">
      <button type="button" className="btn btn-primary" aria-expanded={open} onClick={() => setOpen(!open)} data-testid="papers-create">
        {tr("ph.create_title")}
      </button>
      {open ? (
        <div className="card stack" id="create-title">
          <label className="field">
            <span>{tr("ph.kind_for_paper")}</span>
            <select value={kind} onChange={(e) => setKind(e.target.value as CheckKind)} data-testid="create-kind">
              {(["pre", "post", "termly"] as const).map((k) => (
                <option key={k} value={k}>
                  {tr(`check.kind.${k}` as Key)}
                </option>
              ))}
            </select>
          </label>
          <div className="row">
            <button type="button" className={route === "rules" ? "btn btn-primary" : "btn btn-secondary"} aria-pressed={route === "rules"} onClick={() => setRoute("rules")} data-testid="route-rules">
              {tr("ph.route_rules")}
            </button>
            <button type="button" className={route === "pdf" ? "btn btn-primary" : "btn btn-secondary"} aria-pressed={route === "pdf"} onClick={() => void choosePdf()} data-testid="route-pdf">
              {tr("ph.route_pdf")}
            </button>
          </div>
          <p className="muted">{route === "pdf" ? tr("ph.route_pdf_note") : tr("ph.route_rules_note")}</p>
          {route === "rules" ? (
            <details className="card" open data-testid="paper-details">
              <summary>{tr("papers.make_title")}</summary>
              <PaperMaker checkId={klass?.id ? `${klass.id}:${slot}` : null} className={klass?.name ?? ""} slot={slot} kind={kind} form={form} latest={latest} onMade={onMade} />
            </details>
          ) : null}
          {route === "pdf" && who.classId ? <PaperImport who={who} kind={kind} onConfirmed={() => { onMade(); setRoute(null); }} /> : null}
        </div>
      ) : null}
    </section>
  );
}

function TeacherPapers() {
  const { tr, klass, online, reload } = useApp();
  const [rows, setRows] = useState<Paper[] | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [msg, setMsg] = useState("");
  const [checks, setChecks] = useState<CheckRow[]>([]);
  const [placement, setPlacement] = useState<Placement>(null);
  const [cohortSize, setCohortSize] = useState<number | undefined>();
  const [kind, setKind] = useState("");
  const [status, setStatus] = useState("");
  const who = useHubIdentity();
  const [hub, setHub] = useState<Record<string, HubPaper>>({});
  const [detail, setDetail] = useState<string | null>(null);
  const [detailTab, setDetailTab] = useState<"overview" | "questions">("overview");
  const [askDelete, setAskDelete] = useState(false);
  const [nonce, setNonce] = useState(0); // every click on Details, Edit or Delete opens the panel afresh
  const [assigning, setAssigning] = useState<string | null>(null);
  const [bump, setBump] = useState(0); // a paper was just made: load the lists again
  const [twinning, setTwinning] = useState<string | null>(null);
  // The post-test twin of an imported pre-test: new numbers, the same skills and level, made by code.
  async function makeTwin(id: string) {
    setTwinning(id);
    setMsg("");
    try {
      await hcall<HubPaper>(`/papers/${encodeURIComponent(id)}/twin`, who, { method: "POST" });
      setBump((b) => b + 1);
      setMsg(tr("ph.twin_made"));
    } catch (e) {
      setMsg(e instanceof HubError && e.explanation ? e.explanation : tr("ph.err"));
    } finally {
      setTwinning(null);
    }
  }
  const reloadHub = useCallback(() => {
    if (!klass?.id) return;
    hcall<HubPaper[]>(`/papers?class_id=${encodeURIComponent(klass.id)}`, who)
      .then((l) => setHub(Object.fromEntries(l.map((x) => [x.id, x]))))
      .catch(() => undefined);
  }, [klass?.id, who.role, bump]);
  useEffect(reloadHub, [reloadHub]);

  useEffect(() => {
    if (!klass?.id) {
      // a fresh phone has no class yet: make one now (papers are listed per class), then this runs again
      void activeClass(false).then(() => reload());
      return;
    }
    pcall<Paper[]>(`/api/papers?class_id=${encodeURIComponent(klass.id)}`, "teacher")
      .then(setRows)
      .catch(() => setMsg(tr("papers.error")));
    void db.checks.where("classId").equals(klass.id).toArray().then(setChecks);
  }, [klass?.id, tr, bump, reload]);

  useEffect(() => {
    if (!klass?.id || !online) return;
    fetch(`${API_BASE}/api/programme/${klass.id}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((d: { placement: { status: Placement }; cohort: { size: number } | null }) => {
        setPlacement(d.placement.status);
        setCohortSize(d.cohort?.size);
      })
      .catch(() => setPlacement(null));
  }, [klass?.id, online]);

  const shown = (rows ?? []).filter((p) => (!kind || p.kind === kind) && (!status || p.status === status));
  const kinds = [...new Set((rows ?? []).map((p) => p.kind))];
  const statuses = [...new Set((rows ?? []).map((p) => p.status))];
  const select = (label: string, value: string, set: (v: string) => void, options: string[], name: (o: string) => string, id: string) => (
    <label className="field">
      <span>{label}</span>
      <select value={value} onChange={(e) => set(e.target.value)} data-testid={id}>
        <option value="">{tr("papers.filter_all")}</option>
        {options.map((o) => (
          <option key={o} value={o}>
            {name(o)}
          </option>
        ))}
      </select>
    </label>
  );

  return (
    <section className="stack" aria-labelledby="papers-mine" data-testid="papers-mine">
      <h2 id="papers-mine">{tr("papers.mine_title")}</h2>
      <CreatePaper onMade={() => setBump((b) => b + 1)} />
      {msg ? <p role="alert">{msg}</p> : null}
      {rows === null && !msg ? <Busy text={tr("papers.loading")} testId="papers-busy" /> : null}
      {rows && rows.length === 0 ? (
        <p data-testid="papers-none">
          {tr("papers.none")} {tr("papers.none_hint")}
        </p>
      ) : null}
      {rows && rows.length > 1 ? (
        <div className="row" data-testid="papers-filters">
          {select(tr("papers.filter_kind"), kind, setKind, kinds, (o) => tr(`check.kind.${o}` as Key), "papers-filter-kind")}
          {select(tr("papers.filter_status"), status, setStatus, statuses, (o) => tr(`papers.status.${o}` as Key), "papers-filter-status")}
        </div>
      ) : null}
      {rows && rows.length > 0 && shown.length === 0 ? <p data-testid="papers-none-filtered">{tr("papers.none_filtered")}</p> : null}
      <ul className="plain stack">
        {shown.map((p) => {
          const st = cohortStatus(p.id, checks, placement, cohortSize);
          return (
            <li key={p.id} className="card" data-testid={`paper-row-${p.form}`}>
              <p>
                <strong>{p.check_code}</strong> · {layoutName(tr as never, p.language)}
              </p>
              <p>
                <span className="chip">{p.check_code}</span> <span className="chip">{tr(`check.kind.${p.kind}` as Key)}</span>{" "}
                <span className="chip">{tr(`papers.status.${p.status}` as Key)}</span>
                {p.frozen ? <span className="chip"> {tr("papers.frozen")}</span> : null} <span className="chip" data-testid={`paper-source-${p.form}`}>{hub[p.id] ? sourceLabel(tr as never, hub[p.id]!) : tr("papers.source_generated")}</span>
              </p>
              <p data-testid={`paper-cohort-${p.form}`} data-reason={st.reason}>
                <span className={st.formed ? "chip chip-positive" : "chip"}>{tr(st.formed ? "papers.cohort_yes" : "papers.cohort_no")}</span>{" "}
                {tr(`papers.cohort.${st.reason}` as Key, { n: st.cohortSize ?? 0, entered: st.entered ?? 0, expected: st.expected ?? 0 })}
              </p>
              <div className="row card-actions">
                {st.action !== "none" ? (
                  <a className="btn btn-secondary" href={href("/check")} data-testid={`paper-next-${p.form}`}>
                    {tr(st.action === "enter_check" ? "papers.next_enter" : "papers.next_continue")}
                  </a>
                ) : null}
                <button type="button" className="btn btn-secondary" aria-expanded={open === p.id} onClick={() => setOpen(open === p.id ? null : p.id)}>
                  {open === p.id ? tr("common.close") : tr("papers.open")}
                </button>
                <button type="button" className="btn btn-secondary" aria-expanded={detail === p.id} onClick={() => { setNonce((n) => n + 1); setDetailTab("overview"); setAskDelete(false); setDetail(detail === p.id ? null : p.id); }} data-testid={`paper-details-${p.form}`}>
                  {tr("ph.details")}
                </button>
                <button type="button" className="btn btn-secondary" onClick={() => { setNonce((n) => n + 1); setDetailTab("questions"); setAskDelete(false); setDetail(p.id); }} data-testid={`paper-edit-${p.form}`}>
                  {tr("ph.edit")}
                </button>
                <button type="button" className="btn btn-secondary" onClick={() => { setNonce((n) => n + 1); setDetailTab("overview"); setAskDelete(true); setDetail(p.id); }} data-testid={`paper-delete-${p.form}`}>
                  {tr("ph.delete")}
                </button>
                {ASSIGNMENT_ENABLED ? (
                  <button type="button" className="btn btn-secondary" aria-expanded={assigning === p.id} onClick={() => setAssigning(assigning === p.id ? null : p.id)} data-testid={`paper-assign-${p.form}`}>
                    {tr("ph.assign")}
                  </button>
                ) : null}
                {hub[p.id]?.source === "imported_pdf" && p.kind === "pre" && !Object.values(hub).some((h) => h.twin_of === p.id) ? (
                  <button type="button" className="btn btn-secondary" disabled={twinning === p.id} onClick={() => void makeTwin(p.id)} data-testid={`paper-twin-${p.form}`}>
                    {tr("ph.make_twin")}
                  </button>
                ) : null}
              </div>
              {open === p.id && hub[p.id]?.source === "imported_pdf" ? <p className="muted">{tr("ph.not_printed")}</p> : null}
              {open === p.id ? <PaperView paper={p} role="teacher" /> : null}
              {detail === p.id ? <PaperDetail key={`${p.id}-${nonce}`} paperId={p.id} who={who} startTab={detailTab} askDelete={askDelete} onChanged={() => setBump((b) => b + 1)} onClose={() => setDetail(null)} onDeleted={() => { setDetail(null); setBump((b) => b + 1); }} /> : null}
              {ASSIGNMENT_ENABLED && assigning === p.id ? <AssignPanel paper={hub[p.id] ?? ({ id: p.id, kind: p.kind, form: p.form, status: p.status } as HubPaper)} who={who} onDone={reloadHub} /> : null}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function ScopedPapers() {
  const { tr } = useApp();
  const who = useHubIdentity();
  const [rows, setRows] = useState<HubPaper[] | null>(null);
  const [detail, setDetail] = useState<string | null>(null);
  const [detailTab, setDetailTab] = useState<"overview" | "questions">("overview");
  const [askDelete, setAskDelete] = useState(false);
  const [nonce, setNonce] = useState(0); // every click on Details, Edit or Delete opens the panel afresh
  const [assigning, setAssigning] = useState<string | null>(null);
  const load = useCallback(() => {
    hcall<HubPaper[]>("/papers", who)
      .then(setRows)
      .catch(() => setRows([]));
  }, [who.role]);
  useEffect(load, [load]);
  async function archive(id: string) {
    await hcall(`/papers/${id}/archive`, who, { method: "POST" }).catch(() => undefined);
    load();
  }
  return (
    <section className="stack" aria-labelledby="scoped-title" data-testid="papers-scoped">
      <h2 id="scoped-title">{tr("ph.coach_all")}</h2>
      {rows && rows.length === 0 ? <p data-testid="scoped-none">{tr("papers.none")}</p> : null}
      <ul className="plain stack">
        {(rows ?? []).map((p) => (
          <li key={p.id} className="card" data-testid={`scoped-row-${p.form}`}>
            <p>
              <strong>{p.check_code}</strong> · {p.class_id}
            </p>
            <p>
              <span className="chip">{p.check_code}</span> <span className="chip">{tr(`check.kind.${p.kind}` as Key)}</span> <span className="chip">{tr(`papers.status.${p.status}` as Key)}</span>{" "}
              <span className="chip">{sourceLabel(tr as never, p)}</span> <span className={p.cohorts.formed ? "chip chip-positive" : "chip"}>{tr(p.cohorts.formed ? "papers.cohort_yes" : "papers.cohort_no")}</span>
            </p>
            <div className="row card-actions">
              <button type="button" className="btn btn-secondary" aria-expanded={detail === p.id} onClick={() => { setNonce((n) => n + 1); setDetailTab("overview"); setAskDelete(false); setDetail(detail === p.id ? null : p.id); }}>
                {tr("ph.details")}
              </button>
              <button type="button" className="btn btn-secondary" onClick={() => { setNonce((n) => n + 1); setDetailTab("questions"); setAskDelete(false); setDetail(p.id); }} data-testid={`scoped-edit-${p.form}`}>
                {tr("ph.edit")}
              </button>
              <button type="button" className="btn btn-secondary" onClick={() => { setNonce((n) => n + 1); setDetailTab("overview"); setAskDelete(true); setDetail(p.id); }} data-testid={`scoped-delete-${p.form}`}>
                {tr("ph.delete")}
              </button>
              {ASSIGNMENT_ENABLED ? (
                <button type="button" className="btn btn-secondary" aria-expanded={assigning === p.id} onClick={() => setAssigning(assigning === p.id ? null : p.id)}>
                  {tr("ph.assign")}
                </button>
              ) : null}
              <button type="button" className="btn btn-secondary" onClick={() => void archive(p.id)} data-testid={`scoped-archive-${p.form}`}>
                {tr("ph.archive")}
              </button>
            </div>
            {detail === p.id ? <PaperDetail key={`${p.id}-${nonce}`} paperId={p.id} who={who} startTab={detailTab} askDelete={askDelete} onChanged={load} onClose={() => setDetail(null)} onDeleted={() => { setDetail(null); load(); }} /> : null}
            {ASSIGNMENT_ENABLED && assigning === p.id ? <AssignPanel paper={p} who={who} onDone={load} /> : null}
          </li>
        ))}
      </ul>
    </section>
  );
}

function ReviewQueue() {
  const { tr } = useApp();
  const [rows, setRows] = useState<QueueRow[]>([]);
  const [open, setOpen] = useState<number | null>(null);
  const [reason, setReason] = useState("");
  const [msg, setMsg] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    pcall<QueueRow[]>("/api/papers/queue", "coach")
      .then(setRows)
      .catch((e) => setMsg(tr(e instanceof PaperError && e.status === 403 ? "papers.forbidden" : "papers.error")));
  }, [tr]);
  useEffect(load, [load]);

  async function decide(paperId: string, ok: boolean) {
    setMsg("");
    setSaving(true);
    try {
      if (ok) await pcall(`/api/papers/${paperId}/approve`, "coach", { method: "POST" });
      else await pcall(`/api/papers/${paperId}/reject`, "coach", { method: "POST", body: { reason } });
      setReason("");
      setOpen(null);
      setMsg(tr(ok ? "papers.approved_msg" : "papers.rejected_msg"));
      load();
    } catch (e) {
      setMsg(e instanceof PaperError && e.status === 409 ? tr("papers.conflict", { why: e.explanation }) : tr("papers.error"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="stack" aria-labelledby="papers-queue" data-testid="papers-queue">
      <h2 id="papers-queue">{tr("papers.queue_title")}</h2>
      {saving ? <Busy text={tr("papers.saving")} testId="papers-busy" /> : null}
      {msg ? <p role="status">{msg}</p> : null}
      {rows.length === 0 ? <p data-testid="papers-queue-none">{tr("papers.queue_none")}</p> : null}
      <ul className="plain stack">
        {rows.map((q) => (
          <li key={q.queue_id} className="card" data-testid="queue-row">
            <p>
              <strong>{q.paper.check_code}</strong> · {layoutName(tr as never, q.paper.language)} · <span className="chip">{tr(`papers.reason.${q.reason}` as Key)}</span>
            </p>
            <button type="button" className="btn btn-secondary" aria-expanded={open === q.queue_id} onClick={() => setOpen(open === q.queue_id ? null : q.queue_id)} data-testid="queue-open">
              {open === q.queue_id ? tr("common.close") : tr("papers.open")}
            </button>
            {open === q.queue_id ? (
              <div className="stack">
                <PaperView paper={q.paper} role="coach" showKey />
                <div className="row">
                  <button type="button" className="btn btn-primary" disabled={q.paper.findings.length > 0} onClick={() => void decide(q.paper.id, true)} data-testid="queue-approve">
                    {q.reason === "spot_check" ? tr("papers.spot_ok") : tr("papers.approve")}
                  </button>
                </div>
                {q.reason !== "spot_check" ? (
                  <>
                    <label className="field">
                      <span>{tr("papers.reject_reason")}</span>
                      <input value={reason} maxLength={500} onChange={(e) => setReason(e.target.value)} data-testid="queue-reason" />
                    </label>
                    <button type="button" className="btn btn-secondary" disabled={reason.trim().length < 3} onClick={() => void decide(q.paper.id, false)} data-testid="queue-reject">
                      {tr("papers.reject")}
                    </button>
                  </>
                ) : null}
              </div>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}

function Rules({ role }: { role: PaperRole }) {
  const { tr } = useApp();
  const [data, setData] = useState<{ published: number; versions: RuleVersion[] } | null>(null);
  const [current, setCurrent] = useState<RuleVersion | null>(null);
  const [test, setTest] = useState<string>("");
  const [msg, setMsg] = useState("");

  useEffect(() => {
    pcall<{ published: number; versions: RuleVersion[] }>("/api/paper-rules", role)
      .then(async (d) => {
        setData(d);
        setCurrent(await pcall<RuleVersion>(`/api/paper-rules/${d.published}`, role));
      })
      .catch(() => setMsg(tr("papers.error")));
  }, [tr, role]);

  async function exportYaml(n: number) {
    try {
      const res = await fetch(`${API_BASE}/api/paper-rules/${n}/export.yaml`, { headers: { "X-Role": role } });
      if (!res.ok) throw new PaperError(res.status);
      const url = URL.createObjectURL(await res.blob());
      const a = document.createElement("a");
      a.href = url;
      a.download = `paper-rules-v${n}.yaml`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setMsg(tr("papers.error"));
    }
  }

  async function runTest(n: number) {
    setTest(tr("papers.testing"));
    try {
      const r = await pcall<{ blueprints: Record<string, { findings?: unknown[]; error?: unknown }> }>(`/api/paper-rules/${n}/test`, "coach", { method: "POST" });
      const ok = Object.values(r.blueprints).filter((b) => !b.error && (b.findings ?? []).length === 0).length;
      setTest(tr("papers.rules_test_result", { ok, n: Object.keys(r.blueprints).length }));
    } catch {
      setTest(tr("papers.error"));
    }
  }

  return (
    <section className="stack" aria-labelledby="papers-rules" data-testid="papers-rules">
      <h2 id="papers-rules">{tr("papers.rules_title")}</h2>
      <p>{tr("papers.rules_intro")}</p>
      {msg ? <p role="alert">{msg}</p> : null}
      {data ? (
        <p data-testid="rules-published">
          <strong>{tr("papers.rules_published", { n: data.published })}</strong>
        </p>
      ) : null}
      {/* Rule data is written in English: for a teacher it stays folded, with a translated summary */}
      <details open={role === "coach"} data-testid="rules-details">
        <summary>{tr("papers.rules_details")}</summary>
      {current?.body ? (
        <div className="table-scroll" role="region" tabIndex={0} aria-label={tr("papers.rules_templates")}>
          <table data-testid="rules-templates">
            <caption>{tr("papers.rules_templates")}</caption>
            <thead>
              <tr>
                <th scope="col">{tr("papers.rules_col_skill")}</th>
                <th scope="col">{tr("papers.rules_col_pattern")}</th>
                <th scope="col">{tr("papers.rules_col_errors")}</th>
              </tr>
            </thead>
            <tbody>
              {current.body.templates.map((t) => (
                <tr key={t.id}>
                  <th scope="row">
                    {t.skill} <span className="muted">({t.id})</span>
                  </th>
                  <td>{t.digit_pattern}</td>
                  <td>{t.bugs.join(", ") || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {data ? (
        <>
          <h3>{tr("papers.rules_history")}</h3>
          <ul className="plain stack" data-testid="rules-history">
            {data.versions.map((v) => (
              <li key={v.number} className="card">
                <p>
                  <strong>{tr("papers.rules_v", { n: v.number })}</strong> · <span className="chip">{tr(`papers.rules_status.${v.status}` as Key)}</span>
                </p>
                <p className="muted">{tr("papers.rules_by", { a: v.author, b: v.approver ?? "—" })}</p>
                <ul>
                  {v.diff.slice(0, 8).map((d, i) => (
                    <li key={i}>{d}</li>
                  ))}
                </ul>
                <div className="row">
                  <button type="button" className="btn btn-secondary" onClick={() => void exportYaml(v.number)} data-testid={`rules-export-${v.number}`}>
                    {tr("papers.rules_export")}
                  </button>
                  {role === "coach" ? (
                    <button type="button" className="btn btn-secondary" onClick={() => void runTest(v.number)} data-testid={`rules-test-${v.number}`}>
                      {tr("papers.rules_test")}
                    </button>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
          {test === tr("papers.testing") ? <Busy text={test} testId="rules-busy" /> : null}
          {test && test !== tr("papers.testing") ? (
            <p role="status" data-testid="rules-test-result">
              {test}
            </p>
          ) : null}
          <p className="muted">{tr("papers.rules_change_note")}</p>
        </>
      ) : null}
      </details>
    </section>
  );
}

export default function Papers() {
  const { tr, role, klass } = useApp();
  const teacher = role === "teacher" || role === "judge" || role === "mentor";
  const coach = role === "coach" || role === "judge";
  const who = useHubIdentity();
  return (
    <section className="stack" aria-label={tr("papers.title")} data-testid="papers">
      {klass?.simulated || !teacher ? <SimulatedBanner /> : null}
      {ASSIGNMENT_ENABLED && teacher && who.classId ? <AssignedToYou who={who} compact /> : null}
      {teacher ? <TeacherPapers /> : null}
      {coach || role === "mentor" ? <ScopedPapers /> : null}
      {coach ? <ReviewQueue /> : null}
      {coach ? <Rules role="coach" /> : teacher ? <Rules role="teacher" /> : null}
      {!teacher && !coach ? <p>{tr("papers.forbidden")}</p> : null}
    </section>
  );
}
