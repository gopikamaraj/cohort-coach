// The assistant panel: one component for every role. The title, the scope note, the suggested
// questions and the sources all come from the server, which decides the scope from the signed-in
// role. The judge alone sees View as, the About this product tab and the 10-minute test path.
import { track } from "../lib/tester";
import { useCallback, useEffect, useRef, useState } from "react";
import type { Key } from "../i18n";
import { go, href, useQuery } from "../lib/router";
import { judgeDeployment } from "../lib/roles";
import { Icon } from "../components/icons";
import { askText, getAnswer, getPath, getQuestions, getScope, type Answer, type Ctx, type Question, type ScopeInfo, type TestPath } from "../lib/assistant";
import { useApp } from "../state";

const STATUS_ICON: Record<string, string> = { Built: "✓", "Partly built": "◐", Simulated: "◇", Mock: "◌", Roadmap: "→" };

/** The chat itself. In the drawer it is just questions and answers; the full judge page (`full`) adds
 * View as, About this product and the ten-minute test path. */
export function AssistantPanel({ screen, full, ask }: { screen: string; full: boolean; ask?: string | null }) {
  const { tr, lang, role } = useApp();
  const [viewAs, setViewAs] = useState<string | null>(null);
  const [ready, setReady] = useState(full);
  // In the drawer the assistant speaks as the role she chose on the landing page. Only the judge
  // deployment accepts View as (the server refuses it elsewhere, where the role is always teacher).
  useEffect(() => {
    if (full) return;
    let live = true;
    void judgeDeployment().then((j) => {
      if (!live) return;
      setViewAs(j && ["teacher", "mentor", "coach", "officer"].includes(role) ? role : null);
      setReady(true);
    });
    return () => {
      live = false;
    };
  }, [full, role]);
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
  // A link may open the guide on one question (the demo stepper links each step to its question).
  const asked = useRef(false);
  useEffect(() => {
    if (!ask || asked.current || !scope) return;
    asked.current = true;
    void run(getAnswer(ctx, ask));
  }, [ask, scope]);
  useEffect(() => {
    if (ready) load();
  }, [ready, load]);
  useEffect(() => {
    if (full && scope?.can_view_as && !path) getPath().then(setPath, () => undefined);
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
    <section aria-labelledby={full ? "as-title" : "as-title-drawer"} data-testid="assistant">
      {full ? <h1 id="as-title">{scope?.title ?? tr("assistant.title")}</h1> : <h2 id="as-title-drawer" className="sr">{scope?.title ?? tr("assistant.title")}</h2>}
      {scope ? (
        <p className="muted" data-testid="as-scope">
          <strong>{tr("assistant.can")}</strong> {scope.can} <strong>{tr("assistant.cannot")}</strong> {scope.cannot}
        </p>
      ) : null}
      {full && scope?.can_view_as ? (
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
      <div className="chips" data-testid="as-chips">
        {qs.map((q) => (
          <button key={q.id} type="button" className="chip-btn chip-q" disabled={busy} data-testid={`as-q-${q.id}`} onClick={() => {
              track("feature_used", { feature_id: `guide_q:${q.id}`.slice(0, 48) });
              void run(getAnswer(ctx, q.id));
            }}>
            {q.text}
            {q.criteria?.length ? <span className="chip-note"> {q.criteria.join(" · ")}</span> : null}
          </button>
        ))}
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (text.trim()) {
            track("feature_used", { feature_id: "chat_question_sent" });
            void run(askText(ctx, text.trim()));
          }
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
          {ans.follow_ups && ans.follow_ups.length > 0 ? (
            <>
              <h3>{tr("assistant.follow_up")}</h3>
              <div className="chips" data-testid="as-follow-ups">
                {ans.follow_ups.map((f, i) => (
                  <button key={`${f.id ?? f.text}-${i}`} type="button" className="chip-btn chip-q" disabled={busy} data-testid={`as-fu-${i}`} onClick={() => {
                    track("feature_used", { feature_id: "assistant_follow_up" });
                    void run(f.id ? getAnswer(ctx, f.id) : askText(ctx, f.text));
                  }}>
                    {f.text}
                  </button>
                ))}
              </div>
            </>
          ) : null}
        </div>
      ) : null}
      {full && scope?.can_view_as && path && surface === "about" ? (
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

/** The full judge guide at #/assistant. Everyone else gets the drawer instead. */
export default function Assistant() {
  const query = useQuery();
  const [judge, setJudge] = useState<boolean | null>(null);
  useEffect(() => {
    let live = true;
    void judgeDeployment().then((j) => live && setJudge(j));
    return () => {
      live = false;
    };
  }, []);
  useEffect(() => {
    if (judge === false) {
      go("/home");
      document.dispatchEvent(new CustomEvent("cc:assistant-open"));
    }
  }, [judge]);
  if (!judge) return null;
  return <AssistantPanel screen={query.get("from") ?? "any"} full ask={query.get("ask")} />;
}

/** The button in the title bar. */
export function AssistantButton({ onOpen }: { onOpen: () => void }) {
  const { tr } = useApp();
  return (
    <button type="button" className="top-btn" onClick={onOpen} data-testid="assistant-open">
      <Icon name="bulb" size={20} />
      <span>{tr("assistant.short")}</span>
    </button>
  );
}

/** A bottom sheet on a phone and a right-hand panel on a wide screen, so a question never takes the
 * person off the screen she is on. The conversation is kept while the app is open. */
export function AssistantDrawer({ open, onClose, screen }: { open: boolean; onClose: () => void; screen: string }) {
  const { tr } = useApp();
  const ref = useRef<HTMLDialogElement>(null);
  const [seen, setSeen] = useState(false);
  const [judge, setJudge] = useState(false);
  useEffect(() => {
    void judgeDeployment().then(setJudge);
  }, []);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) {
      d.showModal();
      setSeen(true);
      track("feature_used", { feature_id: "assistant_open" });
    }
    if (!open && d.open) d.close();
  }, [open]);
  return (
    <dialog ref={ref} className="drawer" aria-label={tr("assistant.title")} onClose={onClose} onClick={(e) => e.target === ref.current && onClose()} data-testid="assistant-drawer">
      <div className="drawer-body">
        <div className="drawer-head">
          <strong>{tr("assistant.title")}</strong>
          <button type="button" className="chip-btn" onClick={onClose} data-testid="assistant-close">
            {tr("common.close")}
          </button>
        </div>
        {seen ? <AssistantPanel screen={screen} full={false} /> : null}
        {judge ? (
          <p>
            <a href={`${href("/assistant")}?from=${screen}`} onClick={onClose} data-testid="assistant-full">
              {tr("assistant.full")}
            </a>
          </p>
        ) : null}
      </div>
    </dialog>
  );
}
