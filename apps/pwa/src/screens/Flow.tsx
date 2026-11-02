// The step-by-step screen: renders the steps the server sends (message, choice, link) and posts
// answers back. Every word and number comes from the server, the same as in the Telegram bot.
import { LessonAudio } from "../components/LessonAudio";
import { SceneView } from "../components/SceneView";
import { useCallback, useEffect, useState } from "react";
import { useApp } from "../state";
import { consentFromServer, currentTurn, sendAnswer, type FlowTurn } from "../lib/flow";
import { getConsent, setConsent, type Choices } from "../lib/consent";

export default function Flow() {
  const { tr, role, setLang } = useApp();
  const [turn, setTurn] = useState<FlowTurn | null>(null);
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState(false);

  const show = useCallback(
    (t: FlowTurn) => {
      setTurn(t);
      setFailed(false);
      setLang(t.lang);
      const server = consentFromServer(t.consent);
      if (server && !getConsent()?.core) setConsent(server as unknown as Choices);
    },
    [setLang],
  );

  const load = useCallback(() => {
    setFailed(false);
    currentTurn(role === "judge").then(show, () => setFailed(true));
  }, [role, show]);

  useEffect(load, [load]);

  const answer = (stepId: string, value: string) => {
    if (busy) return;
    setBusy(true);
    const key = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`;
    sendAnswer(stepId, value, key)
      .then(show, () => setFailed(true))
      .finally(() => setBusy(false));
  };

  const last = turn?.messages[turn.messages.length - 1];
  return (
    <section aria-labelledby="flow-title">
      <h1 id="flow-title">{tr("flow.title")}</h1>
      {failed ? (
        <div role="alert" data-testid="flow-error">
          <p>{tr("flow.error")}</p>
          <button type="button" className="btn btn-primary" onClick={load}>
            {tr("flow.retry")}
          </button>
        </div>
      ) : null}
      {!turn && !failed ? <p className="muted">{tr("flow.loading")}</p> : null}
      {turn?.messages.map((m, i) => (
        <div key={`${m.step_id}-${i}`} className="panel" data-testid={`flow-${m.step_id}`}>
          {m.scene ? <SceneView scene={m.scene} label={m.alt ?? ""} /> : null}
          {/* a lesson with timing shows its script under the player, highlighted as it plays */}
          <p style={{ whiteSpace: "pre-line" }}>{m.audio && m.audio_info?.sentences.length ? m.text.split("\n\n")[0] : m.text}</p>
          {m.audio ? <LessonAudio url={m.audio} info={m.audio_info} /> : null}
          {m.url ? (
            <a className="btn btn-secondary" href={m.url} data-testid="flow-link">
              {m.url_label}
            </a>
          ) : null}
        </div>
      ))}
      {last && last.buttons.length > 0 ? (
        <div className="choices">
          {last.buttons.map((b) => (
            <button
              key={b.id}
              type="button"
              className="btn btn-primary"
              disabled={busy}
              data-testid={`flow-opt-${b.id}`}
              onClick={() => answer(last.step_id, b.id)}
            >
              {b.label}
            </button>
          ))}
        </div>
      ) : null}
    </section>
  );
}
