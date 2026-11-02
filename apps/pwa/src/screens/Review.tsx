// P3: the review queue and the two keys. A coach reads a draft with its automatic checks, may edit it
// (an edit is checked again before it is saved), approves it or returns it with a reason. A coach's
// approval alone publishes nothing: the programme officer switches the track version on, and the audit
// shows both keys. The server decides who may do what; this screen only shows it.
import { useCallback, useEffect, useMemo, useState } from "react";
import { Icon } from "../components/icons";
import type { Key } from "../i18n";
import {
  ageParts,
  canActivate,
  canApprove,
  oldestFirst,
  qcall,
  QueueError,
  REASONS,
  type AuditRow,
  type ItemDetail,
  type ItemSummary,
  type QueueRole,
  type Reason,
  type Version,
} from "../lib/queue";
import { useApp } from "../state";
import { SimulatedBanner } from "../components/parts";
import { LessonAudioReview } from "../components/LessonAudioReview";

const FILTERS = ["pending", "awaiting_mentor", "approved", "rejected", "all"] as const;
type Filter = (typeof FILTERS)[number];
const LANG_NAME: Record<string, string> = { en: "English", hi: "हिन्दी", ta: "தமிழ்" };

export default function Review() {
  const { tr, role } = useApp();
  // a coach or an officer acts as itself; in the judge deployment the judge may use either key
  const asCoach = role === "coach" || role === "judge";
  const asOfficer = role === "officer" || role === "judge";
  const reader: QueueRole = role === "officer" ? "officer" : "coach";

  const [filter, setFilter] = useState<Filter>("pending");
  const [rows, setRows] = useState<ItemSummary[]>([]);
  const [open, setOpen] = useState<ItemDetail | null>(null);
  const [versions, setVersions] = useState<Version[]>([]);
  const [audit, setAudit] = useState<AuditRow[]>([]);
  const [msg, setMsg] = useState<{ text: string; bad?: boolean } | null>(null);

  const fail = useCallback(
    (e: unknown) => {
      const status = e instanceof QueueError ? e.status : 0;
      const key: Key = status === 403 ? "queue.forbidden" : status === 409 ? "queue.conflict" : "queue.error";
      setMsg({ text: tr(key), bad: true });
    },
    [tr],
  );

  const load = useCallback(async () => {
    try {
      const [items, vs, log] = await Promise.all([
        qcall<ItemSummary[]>(filter === "all" ? "/items" : `/items?status=${filter}`, reader),
        qcall<Version[]>("/versions", reader),
        qcall<AuditRow[]>("/audit?limit=30", reader),
      ]);
      setRows(oldestFirst(items));
      setVersions(vs);
      setAudit(log);
    } catch (e) {
      fail(e);
    }
  }, [filter, reader, fail]);

  useEffect(() => {
    void load();
  }, [load]);

  async function openItem(id: string) {
    setMsg(null);
    try {
      setOpen(await qcall<ItemDetail>(`/items/${id}`, reader));
    } catch (e) {
      fail(e);
    }
  }

  async function act<T>(fn: () => Promise<T>, after?: (r: T) => void) {
    setMsg(null);
    try {
      const out = await fn();
      after?.(out);
      setMsg({ text: tr("queue.done") });
      await load();
    } catch (e) {
      fail(e);
    }
  }

  return (
    <section aria-labelledby="q-title" data-testid="review-queue">
      <h1 id="q-title">
        <Icon name="check" /> {tr("queue.title")}
      </h1>
      <SimulatedBanner />
      <p>{tr("queue.intro")}</p>
      <p className="note" data-testid="queue-rule">
        <Icon name="lock" size={18} /> {tr("queue.rule")}
      </p>
      <p className="muted">{tr("queue.acting", { role: tr(role === "officer" ? "role.officer" : role === "judge" ? "role.judge" : "role.coach") })}</p>

      {msg ? (
        <p role={msg.bad ? "alert" : "status"} className={msg.bad ? "banner" : "note"}>
          {msg.text}
        </p>
      ) : null}

      <div className="subtabs" role="group" aria-label={tr("queue.filter")}>
        {FILTERS.map((f) => (
          <button key={f} type="button" className={f === filter ? "subtab subtab-on" : "subtab"} aria-pressed={f === filter} onClick={() => setFilter(f)} data-testid={`filter-${f}`}>
            {tr(`queue.st.${f}` as Key)}
          </button>
        ))}
      </div>

      <div className="panel">
        {rows.length === 0 ? <p className="muted">{tr("queue.empty")}</p> : null}
        <ul className="plain" data-testid="queue-list">
          {rows.map((r) => {
            const age = ageParts(r.age_hours);
            return (
              <li key={r.item_id} className="class-row" data-status={r.status}>
                <span className="class-name">
                  {tr("queue.row", {
                    day: r.day,
                    kind: r.kind.replaceAll("_", " "),
                    lang: LANG_NAME[r.language] ?? r.language,
                    status: tr(`queue.st.${r.status}` as Key),
                    age: tr(age.unit === "hours" ? "queue.age.hours" : "queue.age.days", { n: age.n }),
                  })}
                </span>
                <button type="button" className="btn btn-secondary" onClick={() => void openItem(r.item_id)} data-testid={`open-${r.item_id}`}>
                  {tr("queue.open")}
                </button>
              </li>
            );
          })}
        </ul>
      </div>

      {open ? (
        <ItemPanel
          key={open.item_id}
          item={open}
          canAct={asCoach}
          onApprove={() => act(() => qcall<ItemDetail>(`/items/${open.item_id}/approve`, "coach", { method: "POST" }), setOpen)}
          onReject={(reason, note) => act(() => qcall<ItemDetail>(`/items/${open.item_id}/reject`, "coach", { method: "POST", body: { reason, note } }), setOpen)}
          onEdit={async (script) => {
            setMsg(null);
            try {
              setOpen(await qcall<ItemDetail>(`/items/${open.item_id}/edit`, "coach", { method: "POST", body: { script } }));
              setMsg({ text: tr("queue.edit_saved") });
              await load();
            } catch (e) {
              if (e instanceof QueueError && e.status === 422) setMsg({ text: tr("queue.edit_blocked", { why: e.explanation }), bad: true });
              else fail(e);
            }
          }}
        />
      ) : null}

      <Versions
        versions={versions}
        asCoach={asCoach}
        asOfficer={asOfficer}
        onApprove={(v) => act(() => qcall(`/versions/${v.id}/approve`, "coach", { method: "POST" }))}
        onActivate={(v) => act(() => qcall(`/versions/${v.id}/activate`, "officer", { method: "POST" }))}
      />

      <LessonAudioReview reader={reader} asCoach={asCoach} />

      <div className="panel" data-testid="audit">
        <h2>{tr("queue.audit")}</h2>
        {audit.length === 0 ? <p className="muted">{tr("queue.audit.none")}</p> : null}
        <ul className="plain">
          {audit.map((a, i) => (
            <li key={i} data-testid="audit-row" className="muted">
              {tr("queue.audit.line", { action: a.action.replaceAll("_", " "), role: a.role, n: a.version, at: a.at.slice(0, 16).replace("T", " ") })}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function ItemPanel(props: {
  item: ItemDetail;
  canAct: boolean;
  onApprove: () => void;
  onReject: (reason: Reason, note: string) => void;
  onEdit: (script: string) => void;
}) {
  const { tr } = useApp();
  const { item } = props;
  const [script, setScript] = useState(item.script);
  const [reason, setReason] = useState<Reason | "">("");
  const [note, setNote] = useState("");
  const [needReason, setNeedReason] = useState(false);
  const open = item.status === "pending" || item.status === "awaiting_mentor";
  const held = item.content_status === "held_by_checker";
  const changed = useMemo(() => script !== item.script, [script, item.script]);

  return (
    <div className="panel" data-testid="item-panel">
      <h2>{tr("queue.script")}</h2>
      <p className="muted">{item.explanation}</p>
      {held ? (
        <p className="banner" role="status" data-testid="held-note">
          {tr("queue.held_by_checker")}
        </p>
      ) : null}
      <h3>{tr("queue.checks")}</h3>
      <ul className="plain" data-testid="checks">
        {item.results.map((r) => (
          <li key={r.name} data-ok={r.ok}>
            <Icon name={r.ok ? "ok" : "close"} size={18} /> {r.name.replaceAll("_", " ")}: {tr(r.ok ? "queue.check.ok" : "queue.check.held")}
            {!r.ok && r.codes.length ? ` (${r.codes.join(", ")})` : ""}
          </li>
        ))}
      </ul>
      {props.canAct && open ? (
        <>
          <label className="field">
            <span>{tr("queue.edit")}</span>
            <textarea rows={10} value={script} onChange={(e) => setScript(e.target.value)} data-testid="edit-script" />
          </label>
          <button type="button" className="btn btn-secondary" disabled={!changed} onClick={() => props.onEdit(script)} data-testid="save-edit">
            {tr("queue.save_edit")}
          </button>
          <div className="row" style={{ marginTop: 12 }}>
            <button type="button" className="btn btn-primary" onClick={props.onApprove} data-testid="approve-item">
              <Icon name="ok" size={18} /> {tr("queue.approve")}
            </button>
          </div>
          <label className="field" style={{ marginTop: 12 }}>
            <span>{tr("queue.reason")}</span>
            <select
              value={reason}
              onChange={(e) => {
                setReason(e.target.value as Reason | "");
                setNeedReason(false);
              }}
              data-testid="reject-reason"
            >
              <option value="">{tr("queue.reason.choose")}</option>
              {REASONS.map((r) => (
                <option key={r} value={r}>
                  {tr(`queue.reason.${r}` as Key)}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>{tr("queue.note")}</span>
            <input type="text" value={note} maxLength={300} onChange={(e) => setNote(e.target.value)} />
          </label>
          {needReason ? (
            <p role="alert" className="banner" data-testid="need-reason">
              {tr("queue.reason.need")}
            </p>
          ) : null}
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => {
              if (!reason) setNeedReason(true);
              else props.onReject(reason, note);
            }}
            data-testid="reject-item"
          >
            {tr("queue.reject")}
          </button>
        </>
      ) : (
        <pre style={{ whiteSpace: "pre-wrap" }}>{item.script}</pre>
      )}
    </div>
  );
}

function Versions(props: {
  versions: Version[];
  asCoach: boolean;
  asOfficer: boolean;
  onApprove: (v: Version) => void;
  onActivate: (v: Version) => void;
}) {
  const { tr } = useApp();
  return (
    <div className="panel" data-testid="versions">
      <h2>{tr("queue.versions")}</h2>
      {props.versions.length === 0 ? <p className="muted">{tr("queue.versions_none")}</p> : null}
      <ul className="plain">
        {props.versions.map((v) => (
          <li key={v.id} className="class-row" data-testid={`version-${v.version}`} data-status={v.status}>
            <span className="class-name">
              {tr("queue.version", { n: v.version })} · <span data-testid="version-status">{tr(`queue.vst.${v.status}` as Key)}</span>
            </span>
            {canApprove(v) && props.asCoach ? (
              <button type="button" className="btn btn-primary" onClick={() => props.onApprove(v)} data-testid="key-coach">
                {tr("queue.key.coach")}
              </button>
            ) : null}
            {canApprove(v) && !props.asCoach ? <span className="muted">{tr("queue.key.wait_coach")}</span> : null}
            {canActivate(v) && props.asOfficer ? (
              <button type="button" className="btn btn-primary" onClick={() => props.onActivate(v)} data-testid="key-officer">
                {tr("queue.key.officer")}
              </button>
            ) : null}
            {canActivate(v) && !props.asOfficer ? <span className="muted">{tr("queue.key.wait_officer")}</span> : null}
          </li>
        ))}
      </ul>
    </div>
  );
}
