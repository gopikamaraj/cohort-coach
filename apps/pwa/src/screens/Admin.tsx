// Admin: everything people have told us. App, content and card feedback, and the simulation observations from
// teachers, all stored on the server and reviewed here. Anonymous: no name, class or device id exists to show.
import { useCallback, useEffect, useState } from "react";
import { Icon, IconButton } from "../components/icons";
import { API_BASE } from "../lib/api";
import { useApp } from "../state";

interface Item {
  id: number;
  kind: string;
  rating: number | null;
  text: string | null;
  language: string;
  role: string;
  context: string | null;
  status: "new" | "reviewed";
  note: string | null;
  created_at: string;
}
interface Observation {
  id: number;
  scenario: string;
  language: string;
  likeness: string;
  differences: string[];
  created_at: string;
}
interface TesterView {
  devices: number;
  events: number;
  feedback: { rating: number; tags: string[]; comment: string | null; role: string | null; screen: string | null; at: string }[];
}
interface DataView {
  scopes: Record<string, { rows: number }>;
}
const SCOPES = ["feedback", "observations", "testers", "demo", "all"] as const;

interface Summary {
  feedback: { new: number; reviewed: number };
  by_kind: Record<string, number>;
  observations: number;
  open_admin: boolean;
}

const KINDS = ["", "app", "content", "simulation", "card_flag"] as const;

export default function Admin() {
  const { tr } = useApp();
  const [key, setKey] = useState(() => sessionStorage.getItem("cc.adminKey") ?? "");
  const [kind, setKind] = useState<string>("");
  const [status, setStatus] = useState<string>("");
  const [items, setItems] = useState<Item[]>([]);
  const [obs, setObs] = useState<Observation[]>([]);
  const [sum, setSum] = useState<Summary | null>(null);
  const [error, setError] = useState("");
  const [testers, setTesters] = useState<TesterView | null>(null);
  const [data, setData] = useState<DataView | null>(null);
  const [confirmText, setConfirmText] = useState<Record<string, string>>({});
  const [deleted, setDeleted] = useState("");

  const headers = useCallback((): HeadersInit => (key ? { "X-Admin-Key": key } : {}), [key]);
  const load = useCallback(async () => {
    setError("");
    try {
      const q = new URLSearchParams();
      if (kind) q.set("kind", kind);
      if (status) q.set("status", status);
      const [f, o, s, t, d] = await Promise.all([
        fetch(`${API_BASE}/api/admin/feedback?${q}`, { headers: headers() }),
        fetch(`${API_BASE}/api/admin/observations`, { headers: headers() }),
        fetch(`${API_BASE}/api/admin/summary`, { headers: headers() }),
        fetch(`${API_BASE}/api/admin/testers`, { headers: headers() }),
        fetch(`${API_BASE}/api/admin/data`, { headers: headers() }),
      ]);
      if (f.status === 401) {
        setError("auth");
        return;
      }
      if (f.status === 503) {
        setError("closed");
        return;
      }
      setItems(((await f.json()) as { items: Item[] }).items);
      setObs(((await o.json()) as { items: Observation[] }).items);
      setSum((await s.json()) as Summary);
      if (t.ok) setTesters((await t.json()) as TesterView);
      if (d.ok) setData((await d.json()) as DataView);
    } catch {
      setError("offline");
    }
  }, [kind, status, headers]);

  useEffect(() => {
    void load();
  }, [load]);

  const wipe = async (scope: string) => {
    const r = await fetch(`${API_BASE}/api/admin/data/${scope}`, { method: "DELETE", headers: { "Content-Type": "application/json", ...headers() }, body: JSON.stringify({ confirm: confirmText[scope] ?? "" }) });
    if (!r.ok) {
      setDeleted("");
      return;
    }
    const out = (await r.json()) as { deleted: Record<string, number> };
    setDeleted(tr("admin.deleted", { n: Object.values(out.deleted).reduce((a, b) => a + b, 0) }));
    setConfirmText({});
    await load();
  };

  const review = async (it: Item, next: "new" | "reviewed") => {
    const note = next === "reviewed" ? (window.prompt(tr("admin.note"), it.note ?? "") ?? it.note ?? "") : "";
    await fetch(`${API_BASE}/api/admin/feedback/${it.id}`, { method: "PATCH", headers: { "Content-Type": "application/json", ...headers() }, body: JSON.stringify({ status: next, note: note || null }) });
    await load();
  };

  return (
    <section aria-labelledby="ad-title" data-testid="admin">
      <h1 id="ad-title">
        <Icon name="admin" /> {tr("admin.title")}
      </h1>
      {sum?.open_admin ? (
        <p className="banner" data-testid="admin-open">
          {tr("admin.open")}
        </p>
      ) : null}
      <label className="field">
        <span>{tr("admin.key")}</span>
        <input
          type="password"
          value={key}
          data-testid="admin-key"
          onChange={(e) => {
            setKey(e.target.value);
            sessionStorage.setItem("cc.adminKey", e.target.value);
          }}
        />
      </label>
      {error === "auth" ? <p role="alert">{tr("admin.auth")}</p> : null}
      {error === "closed" ? <p role="alert" data-testid="admin-closed">{tr("admin.closed")}</p> : null}
      {error === "offline" ? <p role="alert">{tr("prog.offline")}</p> : null}
      {sum ? (
        <dl className="stats" data-testid="admin-summary">
          <div>
            <dt>{tr("admin.new")}</dt>
            <dd data-testid="admin-new">{sum.feedback.new}</dd>
          </div>
          <div>
            <dt>{tr("admin.reviewed")}</dt>
            <dd>{sum.feedback.reviewed}</dd>
          </div>
          <div>
            <dt>{tr("admin.observations")}</dt>
            <dd data-testid="admin-obs-count">{sum.observations}</dd>
          </div>
        </dl>
      ) : null}

      <h2>
        <Icon name="chat" /> {tr("admin.feedback")}
      </h2>
      <div className="row">
        <label className="field">
          <span>{tr("admin.kind")}</span>
          <select value={kind} onChange={(e) => setKind(e.target.value)} data-testid="admin-kind">
            {KINDS.map((k) => (
              <option key={k} value={k}>
                {k ? tr(`admin.kind_${k}` as "admin.kind_app") : tr("admin.all")}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>{tr("admin.status")}</span>
          <select value={status} onChange={(e) => setStatus(e.target.value)} data-testid="admin-status">
            <option value="">{tr("admin.all")}</option>
            <option value="new">{tr("admin.new")}</option>
            <option value="reviewed">{tr("admin.reviewed")}</option>
          </select>
        </label>
      </div>
      {items.length === 0 ? <p data-testid="admin-empty">{tr("admin.empty")}</p> : null}
      <ul className="plain">
        {items.map((it) => (
          <li key={it.id} className="card" data-testid="admin-item" data-status={it.status}>
            <p>
              <span className="chip">{tr(`admin.kind_${it.kind}` as "admin.kind_app")}</span> <span className="chip">{it.role}</span> <span className="chip">{it.language}</span>
              {it.rating ? <span className="chip chip-positive">{"★".repeat(it.rating)}</span> : null}
              {it.context ? <span className="chip">{it.context}</span> : null}
            </p>
            {it.text ? <p>{it.text}</p> : null}
            {it.note ? <p className="muted">{tr("admin.note_line", { note: it.note })}</p> : null}
            <p className="muted">{new Date(it.created_at).toLocaleString()}</p>
            <IconButton
              icon={it.status === "new" ? "ok" : "history"}
              label={it.status === "new" ? tr("admin.mark_reviewed") : tr("admin.reopen")}
              testId="admin-review"
              onClick={() => void review(it, it.status === "new" ? "reviewed" : "new")}
            />
          </li>
        ))}
      </ul>

      <h2>
        <Icon name="practice" /> {tr("admin.simulation")}
      </h2>
      {obs.length === 0 ? <p>{tr("admin.empty")}</p> : null}
      <div className="table-scroll">
        <table data-testid="admin-obs">
          <thead>
            <tr>
              <th>{tr("admin.scenario")}</th>
              <th>{tr("admin.likeness")}</th>
              <th>{tr("admin.differences")}</th>
              <th>{tr("admin.lang")}</th>
            </tr>
          </thead>
          <tbody>
            {obs.map((o) => (
              <tr key={o.id}>
                <td>{o.scenario}</td>
                <td>{tr(`obs.${o.likeness}` as "obs.like")}</td>
                <td>{o.differences.map((d) => tr(`obs.${d}` as "obs.quieter")).join(", ") || "–"}</td>
                <td>{o.language}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2>
        <Icon name="profile" /> {tr("admin.testers_title")}
      </h2>
      {testers ? (
        <div className="stack" data-testid="admin-testers">
          <p>{tr("admin.testers_counts", { d: testers.devices, e: testers.events })}</p>
          {testers.feedback.length === 0 ? <p data-testid="admin-testers-none">{tr("admin.testers_none")}</p> : null}
          <ul className="plain stack">
            {testers.feedback.map((f, i) => (
              <li key={i} className="card" data-testid="admin-tester-fb">
                <p>
                  <span className="chip chip-positive">{"★".repeat(f.rating)}</span> {f.role ? <span className="chip">{f.role}</span> : null} {f.screen ? <span className="chip">{f.screen}</span> : null}
                  {f.tags.map((t) => (
                    <span key={t} className="chip">
                      {t}
                    </span>
                  ))}
                </p>
                {f.comment ? <p>{f.comment}</p> : null}
                <p className="muted">{new Date(f.at).toLocaleString()}</p>
              </li>
            ))}
          </ul>
          <a className="btn btn-secondary" href="#/testing" data-testid="admin-testing-link">
            {tr("admin.testers_link")}
          </a>
        </div>
      ) : null}

      <h2>
        <Icon name="admin" /> {tr("admin.data_title")}
      </h2>
      <p>{tr("admin.data_intro")}</p>
      {deleted ? (
        <p role="status" data-testid="admin-deleted">
          {deleted}
        </p>
      ) : null}
      <ul className="plain stack" data-testid="admin-data">
        {SCOPES.map((sc) => {
          const rows = sc === "all" ? Object.values(data?.scopes ?? {}).reduce((a, b) => a + b.rows, 0) : (data?.scopes[sc]?.rows ?? 0);
          const ok = (confirmText[sc] ?? "") === "DELETE";
          return (
            <li key={sc} className="card stack" data-testid={`admin-scope-${sc}`}>
              <p>
                <strong>{tr(`admin.scope.${sc}` as "admin.scope.all")}</strong> · <span data-testid={`admin-rows-${sc}`}>{tr("admin.data_rows", { n: rows })}</span>
              </p>
              <label className="field">
                <span>{tr("admin.delete_label")}</span>
                <input value={confirmText[sc] ?? ""} onChange={(e) => setConfirmText({ ...confirmText, [sc]: e.target.value })} autoComplete="off" data-testid={`admin-confirm-${sc}`} />
              </label>
              <button type="button" className="btn btn-secondary" disabled={!ok || rows === 0} onClick={() => void wipe(sc)} data-testid={`admin-delete-${sc}`}>
                {tr("admin.delete")}
              </button>
            </li>
          );
        })}
      </ul>
      <p className="muted">{tr("admin.kept_audit")}</p>
      <p className="muted">{tr("admin.kept_cache")}</p>
    </section>
  );
}
