// The audit trail: the last 50 AI calls as metadata (never prompt text, teacher text or output).
import { useEffect, useState } from "react";
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
    fetch("/api/judge/audit?limit=50")
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
        <div className="scroll">
          <table className="grid" data-testid="audit-table">
            <thead>
              <tr>
                <th scope="col">#</th>
                <th scope="col">call</th>
                <th scope="col">model</th>
                <th scope="col">ms</th>
                <th scope="col">tokens</th>
                <th scope="col">USD</th>
                <th scope="col">checks</th>
                <th scope="col">{tr("audit.checker")}</th>
                <th scope="col">{tr("audit.fallback")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td>{r.id}</td>
                  <td>
                    {r.call} v{r.prompt_version}
                    <br />
                    <span className="muted">{r.mode}</span>
                  </td>
                  <td>{r.model}</td>
                  <td>{r.latency_ms}</td>
                  <td>
                    {r.tokens.in}/{r.tokens.out} (c {r.tokens.cache_read})
                  </td>
                  <td>{r.cost_usd.toFixed(4)}</td>
                  <td>
                    {r.validators.filter((v) => v.ok).length}/{r.validators.length}
                  </td>
                  <td>{r.checker.verdict ?? "–"}</td>
                  <td>{r.fallback_used ?? "–"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
