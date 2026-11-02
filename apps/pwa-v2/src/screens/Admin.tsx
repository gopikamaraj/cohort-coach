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

  const headers = useCallback((): HeadersInit => (key ? { "X-Admin-Key": key } : {}), [key]);
  const load = useCallback(async () => {
    setError("");
    try {
      const q = new URLSearchParams();
      if (kind) q.set("kind", kind);
      if (status) q.set("status", status);
      const [f, o, s] = await Promise.all([
        fetch(`${API_BASE}/api/admin/feedback?${q}`, { headers: headers() }),
        fetch(`${API_BASE}/api/admin/observations`, { headers: headers() }),
        fetch(`${API_BASE}/api/admin/summary`, { headers: headers() }),
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
    } catch {
      setError("offline");
    }
  }, [kind, status, headers]);

  useEffect(() => {
    void load();
  }, [load]);

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
      <div className="table-scroll" tabIndex={0}>
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
    </section>
  );
}
