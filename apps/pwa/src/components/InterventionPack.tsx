// Intervention content for a cohort: for each of its errors (most common first), sections built from
// the class's own results and approved content, text first. Sections open and close, the whole pack
// prints, and nothing plays by itself: each section and the whole pack have a "Download audio" button
// that makes a file only when pressed. Sections with no content are left out, never invented.
import { useMemo, useState } from "react";
import { LANG_NAMES, t, type Key, type Lang } from "../i18n";
import type { ClassCohort } from "../lib/classCohort";
import { buildPack, packText, SECTION_TITLE, sectionLines, type Pack, type PackSection } from "../lib/pack";
import { buildAnswerMap, inThisClass } from "../lib/results";
import { useApp } from "../state";
import { AudioDownload } from "./AudioDownload";

function audioLanguage(pack: Pack, lang: Lang): Lang {
  const any = pack.sections.some((s) => s.fallback || s.strategies?.some((x) => x.fallback));
  return any ? "en" : lang;
}

function Section({ s, code, lang }: { s: PackSection; code: string; lang: Lang }) {
  const { tr } = useApp();
  const lines = sectionLines(s, tr);
  const audioLang = s.fallback || s.strategies?.some((x) => x.fallback) ? "en" : lang;
  const text = [t(audioLang, SECTION_TITLE[s.id]), ...sectionLines(s, (k, p) => t(audioLang, k, p))].join("\n");
  return (
    <details className="pack-section" data-testid={`pack-${code}-${s.id}`}>
      <summary>
        <h4 className="inline-h">{tr(SECTION_TITLE[s.id])}</h4>
        {s.draft ? <span className="chip chip-draft"> {tr("results.explain.draft")}</span> : null}
      </summary>
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
      <AudioDownload text={text} language={audioLang} code={code} section={s.id} label="audio.download" testId={`audio-${code}-${s.id}`} />
    </details>
  );
}

export function InterventionPack({ cohort }: { cohort: ClassCohort }) {
  const { tr, lang, check } = useApp();
  const [active, setActive] = useState(cohort.errors[0] ?? "");
  const map = useMemo(() => (check && check.id === cohort.checkId ? buildAnswerMap(check.formKey, check.children, check.absent ?? [], check.approved) : null), [check, cohort.checkId]);
  const code = cohort.errors.includes(active) ? active : (cohort.errors[0] ?? "");
  const pack = useMemo(
    () =>
      buildPack({ code, lang, children: cohort.counts[code] ?? 0, total: cohort.childrenChecked, here: map ? inThisClass(map, code) : null }, (id, c) => {
        console.info(`pack: no content for section "${id}" of ${c}; left out`);
      }),
    [code, lang, cohort, map],
  );
  if (!code) return null;
  const draft = pack.sections.some((s) => s.draft);
  const aLang = audioLanguage(pack, lang);
  const whole = packText(pack, (k, p) => t(aLang, k, p));
  const missingLang = lang !== "en" && pack.sections.some((s) => s.fallback);
  return (
    <section className="stack pack" aria-labelledby="pack-title" data-testid="pack">
      <h2 id="pack-title">{tr("pack.title")}</h2>
      <p className="muted">{tr("pack.intro")}</p>
      <p>
        <span className="chip" data-testid="pack-label">
          {tr("cohort.mine.label")}
        </span>
        {draft ? (
          <span className="chip chip-draft" data-testid="pack-draft">
            {" "}
            {tr("pack.draft")}
          </span>
        ) : null}
      </p>
      {missingLang ? (
        <p className="muted" data-testid="pack-lang-missing">
          {tr("pack.lang_missing", { language: LANG_NAMES[lang] })}
        </p>
      ) : null}
      {cohort.errors.length > 1 ? (
        <div className="subtabs no-print" role="group" aria-label={tr("cohort.mine.pick")}>
          {cohort.errors.map((c) => (
            <button key={c} type="button" className={c === code ? "subtab subtab-on" : "subtab"} aria-pressed={c === code} onClick={() => setActive(c)} data-testid={`pack-tab-${c}`}>
              {tr(`err.${c}` as Key)}
            </button>
          ))}
        </div>
      ) : null}
      <h3>{tr(`err.${code}` as Key)}</h3>
      <div className="row no-print">
        <button
          type="button"
          className="btn btn-secondary"
          onClick={() => {
            document.querySelectorAll<HTMLDetailsElement>(".pack details").forEach((d) => (d.open = true));
            window.print();
          }}
          data-testid="pack-print"
        >
          {tr("pack.print")}
        </button>
      </div>
      <AudioDownload text={whole} language={aLang} code={code} label="audio.download_all" testId={`audio-${code}-all`} />
      <div className="stack">
        {pack.sections.map((s) => (
          <Section key={s.id} s={s} code={code} lang={lang} />
        ))}
      </div>
    </section>
  );
}
