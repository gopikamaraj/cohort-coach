// The printed pack, in one document. Page 1 is the list of contents; then the summary, the pack as it is on
// the page, and the answer sheets of the roll numbers that showed the mistake, each with a box round the
// question and the answer. It is drawn in a block that is never on the screen and is shown only while the
// pack prints (the page itself is hidden then). It carries roll numbers and photos of children's sheets, so
// it is for the teacher's own use.
import { createPortal } from "react-dom";
import type { Key, Lang } from "../i18n";
import type { TrackView } from "../lib/modules";
import type { Pack } from "../lib/pack";
import type { PrintSheet } from "../lib/printPack";
import { useApp } from "../state";
import { PackSectionView } from "./PackSection";
import { PackSummary } from "./PackSummary";

export function PrintPack({ pack, lang, draft, rolls, sheets, track }: { pack: Pack; lang: Lang; draft: boolean; rolls: { confirmed: number[]; possible: number[] }; sheets: PrintSheet[]; track: TrackView | null }) {
  const { tr } = useApp();
  const name = tr(`err.${pack.code}` as Key);
  const made = (track?.modules ?? []).filter((m) => m.status !== "planned" && m.status !== "skipped" && m.text);
  return createPortal(
    <div className="print-pack-only" data-testid="print-pack">
      <section className="pp-contents">
        <p className="pp-brand">{tr("app.title")}</p>
        <h1>{name}</h1>
        <p className="pp-sub">{draft ? `${tr("pack.print_title")} · ${tr("pack.draft")}` : tr("pack.print_title")}</p>
        <h2>{tr("pack.print_contents")}</h2>
        <ol className="pp-toc">
          <li>
            <span>{tr("pack.print_part1")}</span>
          </li>
          <li>
            <span>{tr("pack.print_part2")}</span>
          </li>
          <li>
            <span>{tr("pack.print_modules")}</span>
          </li>
          <li>
            <span>
              {tr("pack.print_part3")}
              <small>{rolls.confirmed.length + rolls.possible.length > 0 ? [rolls.confirmed.length ? tr("pack.print_rolls", { list: rolls.confirmed.join(", ") }) : "", rolls.possible.length ? tr("pack.print_rolls_possible", { list: rolls.possible.join(", ") }) : ""].filter(Boolean).join(" · ") : tr("pack.print_none")}</small>
            </span>
          </li>
        </ol>
        <p className="pp-note">{tr("pack.print_private")}</p>
      </section>
      <section className="pp-page">
        <h2>{tr("pack.print_part1")}</h2>
        <PackSummary pack={pack} lang={lang} draft={draft} />
      </section>
      <section className="pp-page">
        <h2>{tr("pack.print_part2")}</h2>
        {pack.sections.map((s) => (
          <PackSectionView key={s.id} s={s} code={pack.code} />
        ))}
      </section>
      <section className="pp-page" data-testid="print-modules">
        <h2>{tr("pack.print_modules")}</h2>
        {made.length === 0 ? <p>{tr("pack.print_modules_none")}</p> : null}
        {made.map((m) => (
          <article key={m.number} className="pack-section">
            <h3>{tr("module.n_of", { n: m.number, total: track?.total ?? made.length })}: {m.title}</h3>
            {(m.text?.parts ?? []).map((p) => (
              <div key={p.id}>
                <h4>{tr(`module.part.${p.id}` as Key)}</h4>
                {p.text ? <p>{p.text}</p> : null}
                {p.list ? (p.id === "steps" ? <ol>{p.list.map((x) => <li key={x}>{x}</li>)}</ol> : <ul>{p.list.map((x) => <li key={x}>{x}</li>)}</ul>) : null}
              </div>
            ))}
          </article>
        ))}
      </section>
      <section className="pp-page">
        <h2>{tr("pack.print_part3")}</h2>
        {sheets.length > 0 ? <p>{tr("pack.print_boxes_key")}</p> : <p>{tr("pack.print_none")}</p>}
        {sheets.map((sh) => (
          <figure key={sh.roll} className="pp-sheet">
            <figcaption>
              <strong>{tr("pack.print_roll", { n: sh.roll })}</strong>
              {sh.possible ? <span className="chip"> {tr("pack.print_possible_tag")}</span> : null}
              <ul>
                {sh.questions.map((q) => (
                  <li key={q.n}>{tr("pack.print_q", { n: q.n, question: q.question, expected: q.expected, wrote: q.wrote, diagnosis: q.codes.map((c) => tr(`err.${c}` as Key)).join("; ") })}</li>
                ))}
              </ul>
            </figcaption>
            {sh.url ? <img src={sh.url} alt={tr("pack.print_roll", { n: sh.roll })} /> : <p>{tr("pack.print_no_photo")}</p>}
            {sh.url && !sh.placed ? <p>{tr("pack.print_no_boxes")}</p> : null}
          </figure>
        ))}
      </section>
    </div>,
    document.body,
  );
}
