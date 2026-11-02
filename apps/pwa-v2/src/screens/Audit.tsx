// The audit trail: the last 50 AI calls as metadata (never prompt text, teacher text or output).
import { useEffect, useState } from "react";
import { API_BASE } from "../lib/api";
import { useApp } from "../state";

interface Row {
  id: number;
  at: string | null;
  call: string;
  model: string;
  prompt_version: number;
  mode: string;
  latency_ms: number;
  tokens: { in: number; out: number; cache_read: number };
  cost_usd: number;
  validators: { name: string; ok: boolean }[];
  checker: { verdict: string | null };
  fallback_used: string | null;
}

export default function Audit() {
  const { tr, online } = useApp();
  const [rows, setRows] = useState<Row[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!online) return;
    fetch(`${API_BASE}/api/judge/audit?limit=50`)
      .then((r) => (r.ok ? (r.json() as Promise<{ calls: Row[] }>) : Promise.reject(new Error("bad"))))
      .then((d) => setRows(d.calls))
      .catch(() => setFailed(true));
  }, [online]);

  return (
    <section aria-labelledby="audit-title">
      <h1 id="audit-title">{tr("audit.title")}</h1>
      <p>{tr("audit.intro")}</p>
      <p className="muted">{tr("layers.judge_only")}</p>
      {!online || failed ? <p role="alert">{tr("aimap.offline")}</p> : null}
      {online && !rows && !failed ? <p>{tr("aimap.loading")}</p> : null}
      {rows && rows.length === 0 ? <p data-testid="audit-empty">{tr("audit.empty")}</p> : null}
      {rows && rows.length > 0 ? (
        <ul className="plain audit" data-testid="audit-table">
          {rows.map((r) => (
            <li key={r.id} className="card" data-testid={`audit-${r.id}`}>
              <p className="audit-head">
                <strong>
                  #{r.id} {r.call} v{r.prompt_version}
                </strong>{" "}
                <span className="muted">
                  {r.model} · {r.mode}
                </span>
              </p>
              <dl className="audit-facts">
                <div>
                  <dt>{tr("audit.checker")}</dt>
                  <dd>{r.checker.verdict ?? "–"}</dd>
                </div>
                <div>
                  <dt>{tr("audit.checks")}</dt>
                  <dd>
                    {r.validators.filter((v) => v.ok).length}/{r.validators.length}
                  </dd>
                </div>
                <div>
                  <dt>{tr("audit.fallback")}</dt>
                  <dd>{r.fallback_used ?? "–"}</dd>
                </div>
                <div>
                  <dt>ms</dt>
                  <dd>{r.latency_ms}</dd>
                </div>
                <div>
                  <dt>tokens</dt>
                  <dd>
                    {r.tokens.in}/{r.tokens.out} (c {r.tokens.cache_read})
                  </dd>
                </div>
                <div>
                  <dt>USD</dt>
                  <dd>{r.cost_usd.toFixed(4)}</dd>
                </div>
              </dl>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
