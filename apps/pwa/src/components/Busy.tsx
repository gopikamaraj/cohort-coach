// A loader that says what is happening: a small spinner (still when reduced motion is on) and one
// plain sentence, announced politely to screen readers. For an AI operation `ai` adds the line
// "AI is working on it", so nobody wonders whether the app has stopped.
import { useApp } from "../state";

export function Busy({ text, testId = "busy", ai = false }: { text: string; testId?: string; ai?: boolean }) {
  const { tr } = useApp();
  return (
    <p className="busy" role="status" aria-live="polite" data-testid={testId}>
      <span className="spinner" aria-hidden="true" />
      <span>
        {ai ? <strong className="busy-ai">{tr("ai.working")} </strong> : null}
        {text}
      </span>
    </p>
  );
}
