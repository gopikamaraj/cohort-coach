// Page 1: Upload sheets. A coordinator adds the pre-test photos teachers sent her. Nothing is sent
// until school consent is confirmed and a reference entered; photos queue on the phone when there
// is no signal and go when it returns.
import { useCallback, useEffect, useRef, useState } from "react";
import { Icon } from "../components/icons";
import type { Key } from "../i18n";
import { canDo, jsonInit, pilotJson, PilotApiError, type Config, type Summary } from "./api";
import { usePilot } from "./context";
import { kvGet, kvSet, pilotDb, type UploadRow } from "./db";
import {
  ACCEPT,
  addFiles,
  clearFinished,
  flushUploads,
  gate,
  removeUpload,
  retryUpload,
  tally,
  type Meta,
} from "./uploads";

const EMPTY: Meta = { schoolCode: "", classCode: "", teacherRef: "", consentRef: "" };
const STATUS_KEY = {
  queued: "pilot.up.st.queued",
  uploading: "pilot.up.st.uploading",
  stored: "pilot.up.st.stored",
  failed: "pilot.up.st.failed",
} as const satisfies Record<UploadRow["status"], Key>;
const STATUS_ICON = { queued: "history", uploading: "upload", stored: "ok", failed: "close" } as const;

export default function UploadSheets() {
  const { tr, session, online } = usePilot();
  const allowed = canDo(session, "coordinator");
  const [meta, setMeta] = useState<Meta>(EMPTY);
  const [consent, setConsent] = useState(false);
  const [rows, setRows] = useState<UploadRow[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const cameraRef = useRef<HTMLInputElement>(null);
  const pickRef = useRef<HTMLInputElement>(null);

  const reloadRows = useCallback(async () => setRows(await pilotDb.uploads.orderBy("id").toArray()), []);
  const refreshSummary = useCallback(async () => {
    if (!allowed) return;
    try {
      setSummary(await pilotJson<Summary>("/api/pilot/sheets/summary", {}, session));
    } catch {
      /* offline: keep the last numbers */
    }
  }, [allowed, session]);
  const flush = useCallback(async () => {
    if (!allowed || !online) return;
    await flushUploads(session, pilotDb, undefined, () => void reloadRows());
    await reloadRows();
    await refreshSummary();
  }, [allowed, online, session, reloadRows, refreshSummary]);

  useEffect(() => {
    void (async () => {
      setMeta(await kvGet<Meta>("upload.meta", EMPTY));
      await reloadRows();
    })();
  }, [reloadRows]);
  useEffect(() => {
    void refreshSummary();
  }, [refreshSummary]);
  useEffect(() => {
    void flush();
  }, [flush, online]);
  const waiting = rows.some((r) => r.status === "queued" || r.status === "uploading");
  useEffect(() => {
    if (!waiting && !summary?.waiting) return;
    const id = setInterval(() => void flush(), 8000);
    return () => clearInterval(id);
  }, [waiting, summary?.waiting, flush]);

  const set = (field: keyof Meta) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const next = { ...meta, [field]: e.target.value };
    setMeta(next);
    void kvSet("upload.meta", next);
  };
  const gateState = gate(meta, consent);
  const ready = gateState === "ok" && allowed;

  async function onFiles(e: React.ChangeEvent<HTMLInputElement>) {
    const files = [...(e.target.files ?? [])];
    e.target.value = "";
    if (!files.length || !ready) return;
    const out = await addFiles(files, meta);
    const parts: string[] = [];
    if (out.skipped) parts.push(tr("pilot.up.skipped", { n: out.skipped }));
    if (out.rejected) parts.push(tr("pilot.up.bad_file"));
    setNote(parts.join(" ") || null);
    await reloadRows();
    void flush();
  }

  const counts = tally(rows);
  const queuedNow = counts.queued + counts.uploading;

  if (!allowed) {
    return (
      <>
        <h1>{tr("pilot.up.title")}</h1>
        <p className="p-msg p-bad" role="alert">
          <Icon name="lock" size={18} />
          {tr("pilot.err.forbidden")}
        </p>
      </>
    );
  }

  return (
    <>
      <h1>{tr("pilot.up.title")}</h1>
      <p className="p-muted">{tr("pilot.up.intro")}</p>

      <section className="p-card p-watch" aria-labelledby="names-h">
        <div className="p-note">
          <Icon name="info" />
          <div>
            <h2 id="names-h">{tr("pilot.up.names.title")}</h2>
            <p>{tr("pilot.up.names.body")}</p>
          </div>
        </div>
      </section>

      <section className="p-card" aria-labelledby="consent-h">
        <h2 id="consent-h">
          <Icon name="shield" size={20} />
          {tr("pilot.up.consent.title")}
        </h2>
        <label className="p-check">
          <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} data-testid="consent-confirm" />
          <span>{tr("pilot.up.consent.confirm")}</span>
        </label>
        <label className="p-field">
          <span>{tr("pilot.up.consent.ref")}</span>
          <input type="text" value={meta.consentRef} onChange={set("consentRef")} maxLength={60} data-testid="consent-ref" />
          <small>{tr("pilot.up.consent.hint")}</small>
        </label>
        <div className="p-grid2">
          <label className="p-field">
            <span>{tr("pilot.up.school")}</span>
            <input type="text" value={meta.schoolCode} onChange={set("schoolCode")} maxLength={24} autoCapitalize="characters" list="school-codes" data-testid="school-code" />
            <datalist id="school-codes">
              {(summary?.schools ?? []).map((s) => (
                <option key={s} value={s} />
              ))}
            </datalist>
          </label>
          <label className="p-field">
            <span>{tr("pilot.up.class")}</span>
            <input type="text" value={meta.classCode} onChange={set("classCode")} maxLength={12} data-testid="class-code" />
          </label>
        </div>
        <label className="p-field">
          <span>{tr("pilot.up.teacher")}</span>
          <input type="text" value={meta.teacherRef} onChange={set("teacherRef")} maxLength={24} list="teacher-codes" data-testid="teacher-code" />
          <datalist id="teacher-codes">
            {(summary?.teachers ?? []).map((s) => (
              <option key={s} value={s} />
            ))}
          </datalist>
          <small>{tr("pilot.up.codes_hint")}</small>
        </label>
        <p className="p-small">
          <span className="p-chip">
            <Icon name="check" size={16} />
            {tr("pilot.up.phase")}: {tr("pilot.up.pre")}
          </span>
        </p>
      </section>

      <section className="p-card" aria-labelledby="add-h">
        <h2 id="add-h">
          <Icon name="camera" size={20} />
          {tr("pilot.up.take")} / {tr("pilot.up.choose")}
        </h2>
        <div className="p-filebtns">
          <button type="button" className="p-btn" disabled={!ready} aria-disabled={!ready} onClick={() => cameraRef.current?.click()} data-testid="take-photo">
            <Icon name="camera" size={20} />
            {tr("pilot.up.take")}
          </button>
          <button type="button" className="p-btn p-secondary" disabled={!ready} aria-disabled={!ready} onClick={() => pickRef.current?.click()} data-testid="choose-files">
            <Icon name="upload" size={20} />
            {tr("pilot.up.choose")}
          </button>
          <input ref={cameraRef} type="file" accept="image/*" capture="environment" onChange={onFiles} tabIndex={-1} aria-hidden="true" />
          <input ref={pickRef} type="file" accept={ACCEPT} multiple onChange={onFiles} tabIndex={-1} aria-hidden="true" data-testid="file-input" />
        </div>
        {!ready ? (
          <p className="p-msg" role="status" style={{ marginTop: 12 }}>
            <Icon name="info" size={18} />
            {tr("pilot.up.blocked")}
          </p>
        ) : null}
        {note ? (
          <p className="p-msg" role="status" style={{ marginTop: 12 }}>
            <Icon name="info" size={18} />
            {note}
          </p>
        ) : null}
        <p className="p-small p-muted" style={{ marginTop: 12, marginBottom: 0 }}>
          <Icon name="lock" size={16} /> {tr("pilot.up.privacy")}
        </p>
      </section>

      <section className="p-card" aria-labelledby="queue-h">
        <h2 id="queue-h">{tr("pilot.up.queue")}</h2>
        {!online && queuedNow > 0 ? (
          <p className="p-msg" role="status">
            <Icon name="wifi" size={18} />
            {tr("pilot.up.offline_queue", { n: queuedNow })}
          </p>
        ) : null}
        {rows.length === 0 ? (
          <p className="p-muted">{tr("pilot.up.queue_empty")}</p>
        ) : (
          <ul className="p-list" data-testid="upload-list">
            {rows.map((r, i) => (
              <li key={r.id} data-status={r.status}>
                <span className="p-grow">{tr("pilot.up.sheet", { n: i + 1 })}</span>
                <span className={`p-chip ${r.status === "stored" ? "p-ok" : r.status === "failed" ? "p-bad" : r.status === "uploading" ? "p-live" : ""}`}>
                  <Icon name={STATUS_ICON[r.status]} size={16} />
                  {r.duplicate && r.status === "stored" ? tr("pilot.up.already") : tr(STATUS_KEY[r.status])}
                </span>
                {r.status === "failed" ? (
                  <button type="button" className="p-pillbtn p-go" onClick={() => void retryUpload(r.id!).then(reloadRows).then(flush)}>
                    <Icon name="refresh" size={18} />
                    {tr("pilot.up.retry")}
                  </button>
                ) : null}
                {r.status !== "uploading" && r.status !== "stored" ? (
                  <button type="button" className="p-pillbtn" aria-label={tr("pilot.up.remove")} onClick={() => void removeUpload(r.id!).then(reloadRows)}>
                    <Icon name="trash" size={18} />
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
        )}
        {counts.stored > 0 ? (
          <div className="p-actions">
            <button type="button" className="p-pillbtn" onClick={() => void clearFinished().then(reloadRows)}>
              {tr("pilot.up.clear_done")}
            </button>
          </div>
        ) : null}
      </section>

      <section className="p-card p-focus" aria-labelledby="counts-h">
        <h2 id="counts-h">{tr("pilot.up.counts")}</h2>
        <dl className="p-stats" data-testid="sheet-counts">
          <div>
            <dt>{tr("pilot.up.uploaded")}</dt>
            <dd>{summary?.uploaded ?? 0}</dd>
          </div>
          <div>
            <dt>{tr("pilot.up.read")}</dt>
            <dd>{summary?.read ?? 0}</dd>
          </div>
          <div>
            <dt>{tr("pilot.up.needs_look")}</dt>
            <dd>{summary?.needs_look ?? 0}</dd>
          </div>
        </dl>
        {summary && summary.needs_look > 0 ? <p className="p-small">{tr("pilot.up.needs_look_help")}</p> : null}
        <button type="button" className="p-pillbtn" disabled={!online} onClick={() => void refreshSummary()}>
          <Icon name="refresh" size={18} />
          {tr("pilot.up.refresh")}
        </button>
      </section>

      <KeepingSheets summary={summary} onChanged={refreshSummary} />
    </>
  );
}

function KeepingSheets({ summary, onChanged }: { summary: Summary | null; onChanged: () => Promise<void> }) {
  const { tr, session, online } = usePilot();
  const [config, setConfig] = useState<Config | null>(null);
  const [days, setDays] = useState("");
  const [school, setSchool] = useState("");
  const [typed, setTyped] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    void pilotJson<Config>("/api/pilot/config", {}, session)
      .then((c) => {
        setConfig(c);
        setDays(String(c.retention_days));
      })
      .catch(() => undefined);
  }, [session]);

  async function saveDays() {
    try {
      await pilotJson("/api/pilot/config/retention", jsonInit("PUT", { retention_days: Number(days) }), session);
      setMsg(tr("pilot.up.retention_saved"));
    } catch (e) {
      setMsg(e instanceof PilotApiError && e.offline ? tr("pilot.err.offline") : tr("pilot.err.generic"));
    }
  }

  async function wipe() {
    try {
      const out = await pilotJson<{ sheets: number }>(
        `/api/pilot/sheets/school/${encodeURIComponent(school)}?confirm=${encodeURIComponent(typed)}`,
        { method: "DELETE" },
        session,
      );
      setMsg(tr("pilot.up.delete.done", { n: out.sheets }));
      setSchool("");
      setTyped("");
      await onChanged();
    } catch (e) {
      setMsg(e instanceof PilotApiError && e.offline ? tr("pilot.err.offline") : tr("pilot.err.generic"));
    }
  }

  return (
    <section className="p-card" aria-labelledby="keep-h">
      <details>
        <summary style={{ minHeight: 44, display: "flex", alignItems: "center", cursor: "pointer" }}>
          <h2 id="keep-h" style={{ margin: 0 }}>
            {tr("pilot.up.data.title")}
          </h2>
        </summary>
        <label className="p-field" style={{ marginTop: 12 }}>
          <span>{tr("pilot.up.retention")}</span>
          <input
            type="number"
            inputMode="numeric"
            value={days}
            min={config?.retention_range[0] ?? 7}
            max={config?.retention_range[1] ?? 365}
            onChange={(e) => setDays(e.target.value)}
            data-testid="retention-days"
          />
        </label>
        <button type="button" className="p-btn p-secondary" disabled={!online || !days} onClick={() => void saveDays()}>
          {tr("pilot.up.retention_save")}
        </button>
        <div className="p-sub">
          <h2>{tr("pilot.up.delete.title")}</h2>
          <p className="p-small p-muted">{tr("pilot.up.delete.help")}</p>
          <label className="p-field">
            <span>{tr("pilot.up.delete.school")}</span>
            <select value={school} onChange={(e) => setSchool(e.target.value)} data-testid="delete-school">
              <option value="" />
              {(summary?.schools ?? []).map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
          <label className="p-field">
            <span>{tr("pilot.up.delete.confirm")}</span>
            <input type="text" value={typed} onChange={(e) => setTyped(e.target.value)} autoCapitalize="characters" />
          </label>
          <button type="button" className="p-btn p-danger" disabled={!online || !school || typed !== school} onClick={() => void wipe()} data-testid="delete-go">
            <Icon name="trash" size={20} />
            {tr("pilot.up.delete.go")}
          </button>
        </div>
        {msg ? (
          <p className="p-msg" role="status" style={{ marginTop: 12 }}>
            <Icon name="info" size={18} />
            {msg}
          </p>
        ) : null}
      </details>
    </section>
  );
}
