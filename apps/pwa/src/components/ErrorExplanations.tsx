// "What each error means": for every error found in this class, in plain words: what the child is
// doing, why, how to spot it, what to do first, and this class's own numbers and worked example.
// The text is content (draft until a coach approves it); the example is read from the answer key of
// the class's own question, so no number is typed in the text.
import { LANG_NAMES, type Key } from "../i18n";
import { content, explanationFor, pick } from "../lib/errorContent";
import { inThisClass, type AnswerMap } from "../lib/results";
import { useApp } from "../state";

const FIELDS = ["what", "why", "spot", "first"] as const;

export function ErrorExplanations({
  map,
  untracked,
  openCodes,
  onToggle,
}: {
  map: AnswerMap;
  untracked: number;
  openCodes: ReadonlySet<string>;
  onToggle: (code: string, open: boolean) => void;
}) {
  const { tr, lang } = useApp();
  const codes = [...map.legend.map((l) => l.code), ...(untracked > 0 ? ["ADD-WHOLE-ONES"] : [])];
  if (codes.length === 0) return <p className="muted">{tr("cards.not_shown")}</p>;
  const total = map.rolls.length;
  const draft = content.status !== "approved";
  return (
    <div className="stack" data-testid="explanations">
      <p className="muted">{tr("results.explain.intro")}</p>
      {codes.map((code) => {
        const ex = explanationFor(code);
        if (!ex) return null;
        const here = code === "ADD-WHOLE-ONES" ? null : inThisClass(map, code);
        const title = code === "ADD-WHOLE-ONES" ? tr("results.explain.name.ADD-WHOLE-ONES") : tr(`err.${code}` as Key);
        const fields = FIELDS.map((f) => ({ f, text: pick(ex[f], lang) }));
        return (
          <details key={code} id={`explain-${code}`} className="card explain" open={openCodes.has(code)} onToggle={(e) => onToggle(code, e.currentTarget.open)} data-testid={`explain-${code}`}>
            <summary>
              <strong>{title}</strong>{code === "ADD-WHOLE-ONES" ? null : <span className="chip"> {code}</span>}
              {draft ? <span className="chip chip-draft"> {tr("results.explain.draft")}</span> : null}
            </summary>
            {fields.map(({ f, text }) =>
              text ? (
                <div key={f}>
                  <h4>{tr(`results.explain.${f}` as Key)}</h4>
                  <p data-testid={`explain-${code}-${f}`}>{text.value}</p>
                </div>
              ) : null,
            )}
            {here ? (
              <div data-testid={`explain-${code}-class`}>
                <h4>{tr("results.explain.in_class")}</h4>
                <p>{tr("results.explain.children_line", { n: here.children, total })}</p>
                {here.possible > 0 ? <p>{tr("results.explain.possible_line", { n: here.possible })}</p> : null}
                {here.questions.length > 0 ? <p>{tr("results.explain.questions_line", { list: here.questions.join(", ") })}</p> : null}
                {here.common ? <p>{tr("results.explain.common_line", { answer: here.common.answer, n: here.common.n })}</p> : null}
                {here.example ? (
                  <p className="example" data-testid={`explain-${code}-example`}>
                    {tr(map.items.find((i) => i.n === here.example?.n)?.type === "dictation" ? "results.explain.example_say" : "results.explain.example", {
                      question: here.example.question,
                      wrote: here.example.wrote,
                      correct: here.example.correct,
                    })}
                  </p>
                ) : null}
              </div>
            ) : (
              <p className="muted">{tr("results.explain.untracked_note")}</p>
            )}
            {draft ? <p className="muted">{tr("results.explain.draft_note")}</p> : null}
            {fields.some((x) => x.text?.fallback) ? <p className="muted">{tr("results.explain.lang_missing", { language: LANG_NAMES[lang] })}</p> : null}
          </details>
        );
      })}
    </div>
  );
}
