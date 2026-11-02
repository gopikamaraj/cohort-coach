// One section of the pack: a bold title and plain text, nothing collapsed. Used on the page and in the printout.
import { SECTION_TITLE, sectionLines, type PackSection } from "../lib/pack";
import { useApp } from "../state";

export function PackSectionView({ s, code }: { s: PackSection; code: string }) {
  const { tr } = useApp();
  const lines = sectionLines(s, tr);
  return (
    <section className="pack-section" data-testid={`pack-${code}-${s.id}`}>
      <h4>
        {tr(SECTION_TITLE[s.id])}
        {s.draft ? <span className="chip chip-draft"> {tr("results.explain.draft")}</span> : null}
      </h4>
      {s.strategies ? (
        <ol className="pack-strategies">
          {s.strategies.map((st) => (
            <li key={st.id} data-testid={`pack-strategy-${st.id}`}>
              <strong>{st.label}</strong>
              <p>{st.description}</p>
              {st.materials && st.materials !== "None" ? <p>{tr("pack.materials", { list: st.materials })}</p> : null}
              <p className="muted">{tr("pack.steps")}</p>
              <ol>
                {st.steps.map((x) => (
                  <li key={x}>{x}</li>
                ))}
              </ol>
              {st.worked.map((w) => (
                <p key={w} className="example">
                  {tr("pack.worked", { text: w })}
                </p>
              ))}
              <p className="muted">
                {tr("pack.source", { source: st.source })}
                {st.draft ? ` · ${tr("results.explain.draft")}` : ""}
              </p>
            </li>
          ))}
        </ol>
      ) : s.list ? (
        <ul>
          {s.list.map((x) => (
            <li key={x}>{x}</li>
          ))}
        </ul>
      ) : (
        lines.map((l) => <p key={l}>{l}</p>)
      )}
      {!s.strategies ? <p className="muted">{tr("pack.source", { source: s.source })}</p> : null}
    </section>
  );
}
