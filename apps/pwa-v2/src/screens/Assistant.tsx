// The assistant panel: one component for every role. The title, the scope note, the suggested
// questions and the sources all come from the server, which decides the scope from the signed-in
// role. The judge alone sees View as, the About this product tab and the 10-minute test path.
import { useCallback, useEffect, useState } from "react";
import type { Key } from "../i18n";
import { href, useQuery } from "../lib/router";
import { askText, getAnswer, getPath, getQuestions, getScope, type Answer, type Ctx, type Question, type ScopeInfo, type TestPath } from "../lib/assistant";
import { useApp } from "../state";

const STATUS_ICON: Record<string, string> = { Built: "✓", "Partly built": "◐", Simulated: "◇", Mock: "◌", Roadmap: "→" };

export default function Assistant() {
  const { tr, lang } = useApp();
  const query = useQuery();
  const screen = query.get("from") ?? "any";
  const [viewAs, setViewAs] = useState<string | null>(null);
  const [surface, setSurface] = useState<"main" | "about">("main");
  const [scope, setScope] = useState<ScopeInfo | null>(null);
  const [qs, setQs] = useState<Question[]>([]);
  const [path, setPath] = useState<TestPath | null>(null);
  const [text, setText] = useState("");
  const [ans, setAns] = useState<Answer | null>(null);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const ctx: Ctx = { viewAs, surface, lang };

  const load = useCallback(() => {
    setFailed(false);
    setAns(null);
    const c: Ctx = { viewAs, surface, lang };
    Promise.all([getScope(c), getQuestions(c, screen)]).then(
      ([s, q]) => {
        setScope(s);
        setQs(q);
      },
      () => setFailed(true),
    );
  }, [viewAs, surface, lang, screen]);
  useEffect(load, [load]);
  useEffect(() => {
    if (scope?.can_view_as && !path) getPath().then(setPath, () => undefined);
  }, [scope, path]);

  async function run(p: Promise<Answer>) {
    setBusy(true);
    setFailed(false);
    try {
      setAns(await p);
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="as-title" data-testid="assistant">
      <h1 id="as-title">{scope?.title ?? tr("assistant.title")}</h1>
      {scope ? (
        <p className="muted" data-testid="as-scope">
          <strong>{tr("assistant.can")}</strong> {scope.can} <strong>{tr("assistant.cannot")}</strong> {scope.cannot}
        </p>
      ) : null}
      {scope?.can_view_as ? (
        <div className="panel" data-testid="as-judge">
          <div role="tablist" aria-label={tr("assistant.title")}>
            {(["main", "about"] as const).map((s) => (
              <button key={s} type="button" role="tab" aria-selected={surface === s} className="btn btn-secondary" data-testid={`as-tab-${s}`} onClick={() => setSurface(s)}>
                {tr(`assistant.tab_${s}` as Key)}
              </button>
            ))}
          </div>
          {surface === "main" ? (
            <label className="field">
              <span>{tr("assistant.view_as")}</span>
              <select value={viewAs ?? ""} data-testid="as-viewas" onChange={(e) => setViewAs(e.target.value || null)}>
                <option value="">{tr("role.judge")}</option>
                {scope.view_as_roles.map((r) => (
                  <option key={r} value={r}>
                    {tr(`role.${r}` as Key)}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
        </div>
      ) : null}
      {failed ? (
        <p role="alert" data-testid="as-failed">
          {tr("assistant.failed")}{" "}
          <button type="button" className="btn btn-secondary" onClick={load}>
            {tr("flow.retry")}
          </button>
        </p>
      ) : null}
      <div className="stack" data-testid="as-chips">
        {qs.map((q) => (
          <button key={q.id} type="button" className="btn btn-secondary" disabled={busy} data-testid={`as-q-${q.id}`} onClick={() => void run(getAnswer(ctx, q.id))}>
            {q.text}
            {q.criteria?.length ? <span className="chip"> {q.criteria.join(" · ")}</span> : null}
          </button>
        ))}
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (text.trim()) void run(askText(ctx, text.trim()));
        }}
      >
        <label className="field">
          <span>{tr("assistant.ask")}</span>
          <input value={text} maxLength={400} data-testid="as-text" onChange={(e) => setText(e.target.value)} />
        </label>
        <button type="submit" className="btn btn-primary" disabled={busy || !text.trim()} data-testid="as-send">
          {tr("assistant.send")}
        </button>
      </form>
      {ans ? (
        <div className="panel" role="region" aria-live="polite" aria-label={tr("assistant.answer")} data-testid="as-answer">
          {ans.label ? <span className="chip">{ans.label}</span> : null}
          <p data-testid="as-answer-text">{ans.answer}</p>
          {ans.status_labels.length > 0 ? (
            <ul className="plain" data-testid="as-status">
              {ans.status_labels.map((s, i) => (
                <li key={i}>
                  <span aria-hidden="true">{STATUS_ICON[s.status] ?? "•"}</span> {s.status}
                  {s.claim ? `: ${s.claim}` : ""}
                </li>
              ))}
            </ul>
          ) : null}
          {ans.sources.length > 0 ? (
            <>
              <h3>{tr("assistant.sources")}</h3>
              <ul className="plain" data-testid="as-sources">
                {ans.sources.map((s, i) => (
                  <li key={i}>{s.url ? <a href={s.url}>{s.label}</a> : s.label}</li>
                ))}
              </ul>
            </>
          ) : null}
          {ans.how_to_check ? (
            <p>
              <strong>{tr("assistant.how_to_check")}</strong> {ans.how_to_check}
            </p>
          ) : null}
          {ans.limits ? (
            <p className="muted">
              <strong>{tr("assistant.limits")}</strong> {ans.limits}
            </p>
          ) : null}
          {ans.provisional ? <p className="banner">{tr("assistant.provisional")}</p> : null}
        </div>
      ) : null}
      {scope?.can_view_as && path && surface === "about" ? (
        <div className="panel" data-testid="as-path">
          <h2>{tr("assistant.path", { n: path.minutes ?? 10 })}</h2>
          {path.credentials ? <p className="muted">{path.credentials}</p> : null}
          <ol>
            {path.steps.map((st) => (
              <li key={st.n}>
                <strong>{st.title}</strong> · <a href={st.route.split(",")[0]?.trim()}>{st.route}</a> · {st.role}
                <div className="muted">{st.sample_input}</div>
                {st.questions.map((id) => (
                  <button key={id} type="button" className="btn btn-secondary" onClick={() => void run(getAnswer(ctx, id))}>
                    {id}
                  </button>
                ))}
              </li>
            ))}
          </ol>
        </div>
      ) : null}
      {scope ? (
        <p className="muted" data-testid="as-footer">
          {tr("assistant.answers_from", { src: scope.answers_from })} · {tr("assistant.commit")} {scope.commit?.slice(0, 7) ?? "-"}
        </p>
      ) : null}
    </section>
  );
}

export function AssistantLink({ from }: { from: string }) {
  const { tr } = useApp();
  return (
    <a className="btn btn-secondary" href={`${href("/assistant")}?from=${from}`} data-testid="assistant-link">
      {tr("assistant.open")}
    </a>
  );
}
