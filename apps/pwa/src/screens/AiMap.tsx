// The AI map: every Claude call, what it does, and its five layers (input, processing,
// guardrails, evaluation, output), from the server's registry. Judge view.
import { useEffect, useState } from "react";
import { API_BASE } from "../lib/api";
import { useApp } from "../state";

interface Call {
  id: number;
  name: string;
  model: string;
  when: string;
  prompt_version: number;
  layers: Record<string, string>;
}
interface MapData {
  layers: string[];
  calls: Call[];
}

export default function AiMap() {
  const { tr, online } = useApp();
  const [data, setData] = useState<MapData | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!online) return;
    fetch(`${API_BASE}/api/judge/ai-map`)
      .then((r) => (r.ok ? (r.json() as Promise<MapData>) : Promise.reject(new Error("bad"))))
      .then(setData)
      .catch(() => setFailed(true));
  }, [online]);

  return (
    <section aria-labelledby="map-title">
      <h1 id="map-title">{tr("aimap.title")}</h1>
      <p>{tr("aimap.intro")}</p>
      <p className="muted">{tr("layers.judge_only")}</p>
      {!online || failed ? <p role="alert">{tr("aimap.offline")}</p> : null}
      {online && !data && !failed ? <p>{tr("aimap.loading")}</p> : null}
      {data ? (
        <div className="scroll">
          <table className="grid" data-testid="ai-map">
            <thead>
              <tr>
                <th scope="col">#</th>
                {data.layers.map((l) => (
                  <th key={l} scope="col">
                    {tr(`layers.${l}` as "layers.input")}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.calls.map((c) => (
                <tr key={c.id}>
                  <th scope="row">
                    {c.id}. {c.name}
                    <br />
                    <span className="muted">
                      {c.model} · v{c.prompt_version}
                    </span>
                  </th>
                  {data.layers.map((l) => (
                    <td key={l}>{c.layers[l]}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
