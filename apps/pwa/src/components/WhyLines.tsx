// "Why this question": the reasons a question is on a paper. The server builds each line from facts the
// paper already holds (rule template and version, anchor or adaptive, skill, the class profile, the errors
// the item can show); this only puts them in the reader's language. No model wrote them.
import type { Key } from "../i18n";
import { useApp } from "../state";

export interface WhyLine {
  key: string;
  skill?: string;
  codes?: string[];
  params: Record<string, string | number>;
}

// The skill is the point of the line, so it is bold wherever it appears.
const MARK = "";

export function WhyLines({ why, testId }: { why: WhyLine[] | undefined; testId: string }) {
  const { tr } = useApp();
  if (!why || why.length === 0) return null;
  const line = (w: WhyLine) => {
    const text = tr(w.key as Key, {
      ...w.params,
      ...(w.skill ? { skill: MARK } : {}),
      ...(w.codes ? { errors: w.codes.map((c) => tr(`err.${c}` as Key)).join("; ") } : {}),
    });
    if (!w.skill) return text;
    const [before = "", after = ""] = text.split(MARK);
    return (
      <>
        {before}
        <strong className="why-skill" data-testid="why-skill">{tr(w.skill as Key)}</strong>
        {after}
      </>
    );
  };
  return (
    <details className="why" data-testid={testId}>
      <summary>{tr("ph.why_title")}</summary>
      <div className="stack">
        {why.map((w, i) => (
          <p key={i} data-why={w.key}>
            {line(w)}
          </p>
        ))}
      </div>
    </details>
  );
}
