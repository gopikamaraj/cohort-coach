// Pieces of the Papers page: who is asking, the paper detail tabs, the assign panel, "Assigned to you",
// and the paper chooser Enter check uses. Counts only; the server enforces every scope.
import { useCallback, useEffect, useState } from "react";
import type { Key } from "../i18n";
import { ASSIGNMENT_ENABLED } from "../lib/flags";
import { HubError, hcall, type Assignable, type Assignment, type HubIdentity, type HubPaper, type PaperDetailData } from "../lib/paperHub";
import { parseQuestion, signOf } from "../lib/paperEdit";
import { href } from "../lib/router";
import { useApp } from "../state";
import { WhyLines } from "./WhyLines";
import { fetchPaperKey } from "../lib/paperKeys";

export function useHubIdentity(): HubIdentity {
  const { role, klass } = useApp();
  return { role: role === "mentor" ? "mentor" : role === "coach" ? "coach" : "teacher", classId: klass?.id ?? null };
}

export function sourceLabel(tr: (k: Key, v?: Record<string, string | number>) => string, p: Pick<HubPaper, "source" | "review">): string {
  if (p.source !== "imported_pdf") return tr("papers.source_generated");
  return p.review === "awaiting_review" ? tr("ph.imported_awaiting") : tr("ph.source_imported");
}

// --- the detail page ------------------------------------------------------------------------------

const TABS = ["overview", "questions", "coverage", "usage", "history", "files"] as const;

export function PaperDetail({
  paperId,
  who,
  startTab = "overview",
  askDelete = false,
  onChanged,
  onClose,
  onDeleted,
}: {
  paperId: string;
  who: HubIdentity;
  startTab?: (typeof TABS)[number];
  askDelete?: boolean;
  onChanged?: () => void;
  onClose?: () => void;
  onDeleted?: () => void;
}) {
  const { tr } = useApp();
  const [data, setData] = useState<PaperDetailData | null>(null);
  const [tab, setTab] = useState<(typeof TABS)[number]>(startTab);
  const [bad, setBad] = useState(false);
  const [confirming, setConfirming] = useState(askDelete);
  const [msg, setMsg] = useState<{ text: string; bad?: boolean } | null>(null);
  const [changes, setChanges] = useState<Record<number, { include?: boolean }>>({});
  // what she has typed per item, and what the server said about it (the rule check is the server's)
  const [drafts, setDrafts] = useState<Record<number, { q: string; ans: string; ansTouched?: boolean }>>({});
  const [checks, setChecks] = useState<Record<number, { ok: boolean; problems: string[]; answer: number | null; rule: string | null }>>({});

  const load = useCallback(() => {
    hcall<PaperDetailData>(`/papers/${encodeURIComponent(paperId)}/detail`, who)
      .then((d) => {
        setData(d);
        setChanges({});
        setDrafts({});
        setChecks({});
      })
      .catch(() => setBad(true));
  }, [paperId]);
  useEffect(load, [load]);

  const ops = new Map((data?.questions ?? []).map((q) => [q.n, q.operation]));
  const typed = JSON.stringify(
    Object.entries(drafts).flatMap(([n, d]) => {
      const p = parseQuestion(ops.get(Number(n)) ?? "add", d.q);
      return p.ok ? [[Number(n), p.a, p.b]] : [];
    }),
  );
  useEffect(() => {
    const list = JSON.parse(typed) as [number, number, number][];
    if (list.length === 0) return;
    const t = setTimeout(() => {
      hcall<{ items: { n: number; ok: boolean; problems: string[]; answer: number | null; rule: string | null }[] }>(`/papers/${encodeURIComponent(paperId)}/items/check`, who, {
        body: { items: list.map(([n, a, b]) => ({ n, a, b })) },
      })
        .then((r) => {
          setChecks((c) => ({ ...c, ...Object.fromEntries(r.items.map((i) => [i.n, i])) }));
          setDrafts((d) => {
            const next = { ...d };
            for (const i of r.items) if (next[i.n] && !next[i.n]!.ansTouched && i.answer !== null) next[i.n] = { ...next[i.n]!, ans: String(i.answer) };
            return next;
          });
        })
        .catch(() => undefined);
    }, 400);
    return () => clearTimeout(t);
  }, [typed, paperId]);

  const why = (e: unknown) => (e instanceof HubError && e.explanation ? e.explanation : tr("ph.err"));
  async function remove() {
    try {
      await hcall(`/papers/${encodeURIComponent(paperId)}`, who, { method: "DELETE" });
      setMsg({ text: tr("ph.deleted") });
      onDeleted?.();
    } catch (e) {
      setConfirming(false);
      setMsg({ text: why(e), bad: true });
    }
  }
  async function save() {
    if (!data) return;
    const edits = [
      ...Object.entries(drafts).flatMap(([n, d]) => {
        const p = parseQuestion(ops.get(Number(n)) ?? "add", d.q);
        const base = data.questions.find((q) => q.n === Number(n));
        if (!p.ok || !base || (p.a === base.a && p.b === base.b)) return [];
        return [{ field: `items.${n}.a`, value: p.a }, ...(base.operation === "dictate" ? [] : [{ field: `items.${n}.b`, value: p.b }])];
      }),
      ...Object.entries(changes).flatMap(([n, c]) => (c.include !== undefined ? [{ field: `items.${n}.include`, value: c.include }] : [])),
    ];
    if (edits.length === 0) return;
    try {
      const out = await hcall<{ findings?: string[] }>(`/papers/${encodeURIComponent(paperId)}/items`, who, { body: { edits } });
      const flagged = out.findings ?? [];
      setMsg(flagged.length ? { text: tr("ph.edit_flagged", { why: flagged[0] ?? "" }), bad: true } : { text: tr("ph.edit_saved") });
      load();
      onChanged?.();
    } catch (e) {
      setMsg({ text: why(e), bad: true });
    }
  }

  if (bad) return <p role="alert">{tr("ph.err")}</p>;
  if (!data) return <p role="status">{tr("papers.loading")}</p>;
  const o = data.overview;
  // save needs something changed, and every changed question must fit its rule with a matching answer
  const bad_ = Object.entries(drafts).some(([n, d]) => {
    const p = parseQuestion(ops.get(Number(n)) ?? "add", d.q);
    const base = data.questions.find((q) => q.n === Number(n));
    if (!p.ok) return true;
    if (base && p.a === base.a && p.b === base.b) return false;
    const c = checks[Number(n)];
    return !c || !c.ok || (c.answer !== null && d.ans.trim() !== String(c.answer));
  });
  const anyChange = Object.keys(changes).length > 0 || Object.entries(drafts).some(([n, d]) => {
    const p = parseQuestion(ops.get(Number(n)) ?? "add", d.q);
    const base = data.questions.find((q) => q.n === Number(n));
    return p.ok && !!base && (p.a !== base.a || p.b !== base.b);
  });
  const canSave = anyChange && !bad_;
  const opSign = (op: string) => (op === "add" ? "+" : op === "subtract" ? "-" : "");
  return (
    <div className="stack" data-testid="paper-detail">
      {confirming && !data.deletable ? (
        <p role="alert" id="delete-why" data-testid="delete-why">
          {tr("ph.delete_locked", { why: data.in_use ?? "" })}
        </p>
      ) : null}
      {confirming && data.deletable ? (
        <div className="card stack" role="alertdialog" aria-label={tr("ph.delete_confirm")} data-testid="delete-confirm">
          <p>{tr("ph.delete_confirm")}</p>
          <div className="row">
            <button type="button" className="btn btn-primary" onClick={() => void remove()} data-testid="delete-yes">
              {tr("ph.delete_yes")}
            </button>
            <button type="button" className="btn btn-secondary" onClick={() => setConfirming(false)} data-testid="delete-no">
              {tr("ph.delete_no")}
            </button>
          </div>
        </div>
      ) : null}
      {msg ? (
        <p role={msg.bad ? "alert" : "status"} data-testid="detail-msg">
          {msg.text}
        </p>
      ) : null}
      <div role="tablist" className="chips" aria-label={tr("ph.details")}>
        {TABS.map((t) => (
          <button key={t} type="button" role="tab" aria-selected={tab === t} className={tab === t ? "chip-btn chip-on" : "chip-btn"} onClick={() => setTab(t)} data-testid={`tab-${t}`}>
            {tr(`ph.tab_${t}` as Key)}
          </button>
        ))}
      </div>
      <div role="tabpanel" className="stack">
        {tab === "overview" ? (
          <div data-testid="tab-panel-overview">
            <p>
              <strong>{o.title}</strong> · {o.check_code}
            </p>
            <p>
              <span className="chip">{tr(`papers.status.${o.status}` as Key)}</span> <span className="chip">{sourceLabel(tr as never, o)}</span>
            </p>
            {o.frozen ? <p data-testid="frozen-reason">{tr("ph.frozen_why", { why: o.frozen_reason ?? "" })}</p> : null}
            {o.source === "generated" && o.rules_version ? <p className="muted" data-testid="rules-line">{tr("ph.rules_line", { version: o.rules_version })}</p> : null}
          </div>
        ) : null}
        {tab === "questions" ? (
          <div className="stack" data-testid="tab-panel-questions">
            <ol className="plain">
              {data.questions.map((q) => (
                <li key={q.n}>
                  {tr("ph.q_row", { n: q.n, a: q.a, op: opSign(q.operation), b: q.operation === "dictate" ? "" : q.b, key: q.correct })}
                  <WhyLines why={q.why} testId={`why-${q.n}`} />
                  {data.editable ? <EditRow q={q} draft={drafts[q.n]} check={checks[q.n]} imported={data.overview.source === "imported_pdf"} include={changes[q.n]?.include ?? true} onDraft={(d) => setDrafts((all) => ({ ...all, [q.n]: d }))} onInclude={(v) => setChanges((c) => ({ ...c, [q.n]: { include: v } }))} /> : null}
                </li>
              ))}
            </ol>
            {data.editable ? (
              <>
                <p className="muted">{tr("ph.edit_note_inplace")}</p>
                <div className="row">
                  <button type="button" className="btn btn-primary" disabled={!canSave} onClick={() => void save()} data-testid="edit-save">
                    {tr("ph.edit_save")}
                  </button>
                  <button type="button" className="btn btn-secondary" onClick={() => onClose?.()} data-testid="edit-close">
                    {tr("ph.edit_cancel")}
                  </button>
                </div>
              </>
            ) : (
              <p className="muted" data-testid="edit-locked">
                {tr("ph.edit_locked", { why: data.locked_reason ?? data.in_use ?? "" })}
              </p>
            )}
          </div>
        ) : null}
        {tab === "coverage" ? (
          <ul className="plain" data-testid="tab-panel-coverage">
            {Object.entries(data.coverage).map(([code, ns]) => (
              <li key={code}>{tr("ph.coverage_items", { code, items: (ns as number[]).length ? (ns as number[]).join(", ") : "-" })}</li>
            ))}
          </ul>
        ) : null}
        {tab === "usage" ? (
          <div data-testid="tab-panel-usage">
            <p>{tr("ph.usage_line", { assigned: o.assignments.assigned, opened: o.assignments.opened, completed: o.assignments.completed })}</p>
            <p>{tr(`papers.cohort.${o.cohorts.reason === "formed" ? "formed_this_term" : o.cohorts.reason}` as Key, { n: o.cohorts.count, entered: 0, expected: 0 })}</p>
          </div>
        ) : null}
        {tab === "history" ? (
          data.history.length === 0 ? (
            <p data-testid="tab-panel-history">{tr("ph.history_none")}</p>
          ) : (
            <ul className="plain" data-testid="tab-panel-history">
              {data.history.map((h, i) => (
                <li key={i}>
                  {h.at.slice(0, 10)} · {h.event} · {h.actor}
                </li>
              ))}
            </ul>
          )
        ) : null}
        {tab === "files" ? (
          <div data-testid="tab-panel-files">{data.files.imported ? <p>{tr("ph.not_printed")}</p> : <p className="muted">{tr("papers.open")}</p>}</div>
        ) : null}
      </div>
    </div>
  );
}

// --- assign -------------------------------------------------------------------------------------------

export function AssignPanel({ paper, who, onDone }: { paper: HubPaper; who: HubIdentity; onDone: () => void }) {
  const { tr } = useApp();
  const [opts, setOpts] = useState<Assignable | null>(null);
  const [target, setTarget] = useState("");
  const [start, setStart] = useState("");
  const [due, setDue] = useState("");
  const [note, setNote] = useState("");
  const [msg, setMsg] = useState<{ text: string; bad?: boolean } | null>(null);

  useEffect(() => {
    hcall<Assignable>("/assignable", who)
      .then((a) => {
        setOpts(a);
        setTarget(a.classes[0] ? `class:${a.classes[0]}` : "");
      })
      .catch(() => setMsg({ text: tr("ph.err"), bad: true }));
  }, []);

  const cohortOk = paper.kind !== "pre";
  async function go() {
    const [type, id] = target.split(":") as [string, string];
    try {
      const out = await hcall<{ assignments: Assignment[]; warnings: string[] }>("/assignments", who, {
        body: { paper_id: paper.id, target_type: type, target_id: id, kind: paper.kind, form: paper.form, start_date: start || null, due_date: due || null, note },
      });
      setMsg({ text: [tr("ph.assign_ok", { n: out.assignments.length }), ...out.warnings].join(" ") });
      onDone();
    } catch (e) {
      setMsg({ text: e instanceof HubError && e.explanation ? e.explanation : tr("ph.err"), bad: true });
    }
  }
  const ready = paper.status === "auto_approved" || paper.status === "approved" || paper.status === "confirmed";
  return (
    <div className="card stack" data-testid="assign-panel">
      <h4>{tr("ph.assign_title")}</h4>
      {!ready ? <p className="muted">{tr("ph.assign_only_approved")}</p> : null}
      {opts && opts.classes.length === 0 && opts.cohorts.length === 0 ? <p>{tr("ph.assign_none")}</p> : null}
      <label className="field">
        <span>{tr("ph.assign_who")}</span>
        <select value={target} onChange={(e) => setTarget(e.target.value)} data-testid="assign-target">
          {(opts?.classes ?? []).map((c) => (
            <option key={c} value={`class:${c}`}>
              {tr("ph.assign_class_opt", { code: c })}
            </option>
          ))}
          {cohortOk
            ? (opts?.cohorts ?? []).map((c) => (
                <option key={c.id} value={`cohort:${c.id}`}>
                  {tr("ph.assign_cohort_opt", { id: c.id, n: c.classes })}
                </option>
              ))
            : null}
        </select>
      </label>
      {!cohortOk ? (
        <p className="muted" data-testid="assign-pre-note">
          {tr("ph.assign_pre_cohort")}
        </p>
      ) : null}
      <div className="row">
        <label className="field">
          <span>{tr("ph.assign_start")}</span>
          <input type="date" value={start} onChange={(e) => setStart(e.target.value)} data-testid="assign-start" />
        </label>
        <label className="field">
          <span>{tr("ph.assign_due")}</span>
          <input type="date" value={due} onChange={(e) => setDue(e.target.value)} data-testid="assign-due" />
        </label>
      </div>
      <label className="field">
        <span>{tr("ph.assign_note")}</span>
        <input value={note} maxLength={200} onChange={(e) => setNote(e.target.value)} data-testid="assign-note" />
      </label>
      <button type="button" className="btn btn-primary" disabled={!ready || !target} onClick={() => void go()} data-testid="assign-go">
        {tr("ph.assign_go")}
      </button>
      {msg ? (
        <p role={msg.bad ? "alert" : "status"} data-testid="assign-msg">
          {msg.text}
        </p>
      ) : null}
    </div>
  );
}

// --- assigned to you (teacher) ---------------------------------------------------------------------------

export function useAssigned(who: HubIdentity): { rows: Assignment[]; papers: Record<string, HubPaper>; reload: () => void } {
  const [rows, setRows] = useState<Assignment[]>([]);
  const [papers, setPapers] = useState<Record<string, HubPaper>>({});
  const reload = useCallback(() => {
    if (!ASSIGNMENT_ENABLED || !who.classId) return;
    hcall<Assignment[]>("/assignments/mine", who)
      .then(async (a) => {
        setRows(a);
        if (a.length) {
          const list = await hcall<HubPaper[]>("/papers", who);
          setPapers(Object.fromEntries(list.map((p) => [p.id, p])));
        }
      })
      .catch(() => setRows([]));
  }, [who.classId, who.role]);
  useEffect(reload, [reload]);
  return { rows, papers, reload };
}

export function AssignedToYou({ who, compact, showEmpty, testId }: { who: HubIdentity; compact?: boolean; showEmpty?: boolean; testId?: string }) {
  const { tr } = useApp();
  const { rows, papers } = useAssigned(who);
  const live = rows.filter((a) => a.status !== "completed");
  if (live.length === 0 && !showEmpty) return null;
  return (
    <section className="card stack" aria-labelledby="assigned-title" data-testid={testId ?? "assigned-to-you"}>
      <h3 id="assigned-title">{tr("ph.assigned_title")}</h3>
      {live.length === 0 ? (
        <p data-testid="assigned-none">
          {tr("home.assigned_none")}{" "}
          <a href={href("/papers")} data-testid="assigned-create">
            {tr("ph.create_title")}
          </a>
        </p>
      ) : null}
      <ul className="plain stack">
        {live.map((a) => (
          <li key={a.id} data-testid={`assigned-${a.id}`}>
            {tr("ph.assigned_row", { kind: tr(`check.kind.${a.kind}` as Key), due: a.due_date ?? tr("ph.no_due") })}
            {papers[a.paper_id] ? ` · ${papers[a.paper_id]!.check_code}` : ""}
            {compact ? null : (
              <>
                {" "}
                <a className="btn btn-secondary" href={href("/check")} data-testid="assigned-start">
                  {tr("ph.assigned_open")}
                </a>
              </>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

// --- the chooser in Enter check ----------------------------------------------------------------------------

/** The usable-for-a-check statuses: a paper is "Checked" once it is approved or confirmed. */
export const CHECKED = ["auto_approved", "approved", "confirmed"];

/** One dropdown of the class's papers, each with its status (Checked or Not checked yet). Papers
 *  assigned to her come first. A paper not checked yet can be chosen too: the approval check is switched off for now
 *  (DECISIONS 2026-11-02); put `disabled={!CHECKED.includes(p.status)}` back on the option to restore it. */
export function PaperSelect({ who, chosen, onChoose, preferKind }: { who: HubIdentity; chosen: string | null; onChoose: (p: HubPaper | null) => void; preferKind?: string }) {
  const { tr } = useApp();
  const [rows, setRows] = useState<HubPaper[] | null>(null);
  const { rows: assigned } = useAssigned(who);

  useEffect(() => {
    if (!who.classId) return setRows([]);
    hcall<HubPaper[]>(`/papers?class_id=${encodeURIComponent(who.classId)}`, who)
      .then((r) => {
        const shown = r.filter((p) => p.status !== "rejected" && p.status !== "withdrawn");
        setRows(shown);
        // keep each checked paper's key on the phone now, so a check can start later with no signal
        for (const p of shown) void fetchPaperKey(p.id, who).catch(() => undefined);
      })
      .catch(() => setRows([]));
  }, [who.classId]);

  const assignedIds = new Set(assigned.filter((a) => a.status !== "withdrawn").map((a) => a.paper_id));
  const ordered = [...(rows ?? [])].sort((x, y) => Number(assignedIds.has(y.id)) - Number(assignedIds.has(x.id)));

  // pre-select once: the checked paper assigned to her, else the only checked paper there is, else the
  // only checked paper of the kind her next check is expected to be (a pre-test's twin post-test is also listed)
  useEffect(() => {
    if (!rows || chosen) return;
    const ready = ordered.filter((p) => CHECKED.includes(p.status));
    const ofKind = ready.filter((p) => p.kind === preferKind);
    const pick = ready.find((p) => assignedIds.has(p.id)) ?? (ready.length === 1 ? ready[0] : ofKind.length === 1 ? ofKind[0] : undefined);
    if (pick) onChoose(pick);
  }, [rows, assigned.length]);

  const label = (p: HubPaper) =>
    [
      assignedIds.has(p.id) ? tr("ph.assigned_title") : null,
      p.check_code,
      tr(`check.kind.${p.kind}` as Key),
      tr("ph.n_items", { n: p.items }),
      CHECKED.includes(p.status) ? tr("ph.checked") : tr("ph.not_checked"),
    ]
      .filter(Boolean)
      .join(" · ");

  return (
    <div className="stack" data-testid="paper-chooser">
      {rows && rows.length === 0 ? (
        <p data-testid="chooser-none">
          {tr("ph.choose_none")}{" "}
          <a href={href("/papers") + "?back=check"} data-testid="chooser-create">
            {tr("ph.choose_create")}
          </a>
        </p>
      ) : (
        <>
          <label className="field">
            <span>{tr("ph.choose_title")}</span>
            <select value={chosen ?? ""} onChange={(e) => onChoose(ordered.find((p) => p.id === e.target.value) ?? null)} data-testid="paper-select">
              <option value="">{tr("ph.choose_pick")}</option>
              {ordered.map((p) => (
                <option key={p.id} value={p.id}>
                  {label(p)}
                </option>
              ))}
            </select>
          </label>
          <p>
            <a href={href("/papers") + "?back=check"} data-testid="chooser-link">
              {tr("ph.choose_create")}
            </a>
          </p>
        </>
      )}
    </div>
  );
}

// One question and its answer, each in a text box. Typing is checked here for shape only; the rule check
// and the answer come from the server, so the rules are never copied into the browser.
type Q = { n: number; operation: string; a: number; b: number; correct: number };
type Check = { ok: boolean; problems: string[]; answer: number | null; rule: string | null };

function EditRow({ q, draft, check, imported, include, onDraft, onInclude }: { q: Q; draft?: { q: string; ans: string; ansTouched?: boolean }; check?: Check; imported: boolean; include: boolean; onDraft: (d: { q: string; ans: string; ansTouched?: boolean }) => void; onInclude: (v: boolean) => void }) {
  const { tr } = useApp();
  const sign = signOf(q.operation);
  const original = q.operation === "dictate" ? String(q.a) : `${q.a} ${sign} ${q.b}`;
  const text = draft?.q ?? original;
  const ans = draft?.ans ?? String(q.correct);
  const p = parseQuestion(q.operation, text);
  const changed = p.ok && (p.a !== q.a || p.b !== q.b);
  const example = q.operation === "dictate" ? "345" : `38 ${sign} 47`;
  let note: { text: string; bad: boolean } | null = null;
  if (!p.ok) note = { text: p.why === "sign" ? tr("ph.q_hint", { example, op: sign, kind: tr(q.operation === "add" ? "ph.kind_add" : "ph.kind_subtract") }) : tr(q.operation === "dictate" ? "ph.chk_parse_one" : "ph.chk_parse", { op: sign, example }), bad: true };
  else if (changed && !check) note = { text: tr("ph.chk_wait"), bad: false };
  else if (changed && check && !check.ok) note = { text: tr("ph.chk_bad", { rule: check.rule ?? "", why: check.problems[0] ?? "" }), bad: true };
  else if (changed && check && check.answer !== null && ans.trim() !== String(check.answer)) note = { text: tr("ph.chk_answer", { key: check.answer, typed: ans.trim() || "-" }), bad: true };
  else if (changed && check) note = { text: tr("ph.chk_ok", { rule: check.rule ?? "" }), bad: false };
  return (
    <div className="stack" data-testid={`edit-row-${q.n}`}>
      <div className="row">
        <label>
          {tr("ph.q_label")}
          <input type="text" inputMode="text" value={text} aria-label={`${tr("ph.q_label")} ${q.n}`} aria-invalid={note?.bad ? true : undefined} onChange={(e) => onDraft({ q: e.target.value, ans, ansTouched: draft?.ansTouched })} data-testid={`edit-q-${q.n}`} />
        </label>
        <label>
          {tr("ph.a_label")}
          <input type="text" inputMode="numeric" value={ans} aria-label={`${tr("ph.a_label")} ${q.n}`} onChange={(e) => onDraft({ q: text, ans: e.target.value, ansTouched: true })} data-testid={`edit-ans-${q.n}`} />
        </label>
        {imported ? (
          <label className="tick">
            <input type="checkbox" checked={include} aria-label={`${tr("ph.col_include")} ${q.n}`} onChange={(e) => onInclude(e.target.checked)} data-testid={`edit-include-${q.n}`} />
          </label>
        ) : null}
      </div>
      {note ? (
        <p className="muted" role={note.bad ? "alert" : "status"} data-testid={`edit-note-${q.n}`}>
          {note.text}
        </p>
      ) : null}
    </div>
  );
}
