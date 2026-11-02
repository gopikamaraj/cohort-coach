// Intervention content for a cohort: for each of its errors (most common first), sections built from
// the class's own results and approved content, text first: a bold title and plain text for each, all open,
// and it prints. Nothing plays by itself: one "Download audio" button per error makes a single file, only
// when pressed. Sections with no content are left out, never invented.
import { useEffect, useMemo, useState } from "react";
import { LANG_NAMES, type Key } from "../i18n";
import type { ClassCohort } from "../lib/classCohort";
import { buildPack } from "../lib/pack";
import { previewScript, type SpokenPreview } from "../lib/packAudio";
import { buildAnswerMap, inThisClass, rollsFor } from "../lib/results";
import { useApp } from "../state";
import { AudioDownload } from "./AudioDownload";
import { exportStem } from "../lib/packAudio";
import { runAction } from "../lib/action";
import { ModuleTrack } from "./ModuleTrack";
import { PackSectionView } from "./PackSection";
import { PrintPack } from "./PrintPack";
import { loadSheets, type PrintSheet } from "../lib/printPack";

export function InterventionPack({ cohort }: { cohort: ClassCohort }) {
  const { tr, lang, check, online, role, klass } = useApp();
  const [active, setActive] = useState(cohort.errors[0] ?? "");
  const [review, setReview] = useState(false);
  const [printing, setPrinting] = useState(false);
  const [sheets, setSheets] = useState<PrintSheet[]>([]);
  const [edit, setEdit] = useState<{ key: string; text: string } | null>(null);
  const map = useMemo(() => (check && check.id === cohort.checkId ? buildAnswerMap(check.formKey, check.children, check.absent ?? [], check.approved) : null), [check, cohort.checkId]);
  const code = cohort.errors.includes(active) ? active : (cohort.errors[0] ?? "");
  const pack = useMemo(
    () =>
      buildPack({ code, lang, children: cohort.counts[code] ?? 0, total: cohort.childrenChecked, here: map ? inThisClass(map, code) : null, rolls: map ? rollsFor(map, code) : null }, (id, c) => {
        console.info(`pack: no content for section "${id}" of ${c}; left out`);
      }),
    [code, lang, cohort, map],
  );
  // What is voiced is not the screen text: the server writes a spoken script from the content and these
  // counts (no titles, no Source or Draft tags, numbers as words). She can read it and change it.
  const here = map ? inThisClass(map, code) : null;
  const request = useMemo(
    () => ({
      code,
      children: cohort.counts[code] ?? 0,
      total: cohort.childrenChecked,
      rolls: map ? rollsFor(map, code) : null,
      example: here?.example ? { question: String(here.example.question), wrote: String(here.example.wrote), correct: String(here.example.correct) } : null,
    }),
    [code, cohort, map, here],
  );
  const [preview, setPreview] = useState<SpokenPreview | null>(null);
  useEffect(() => {
    if (!review || !online || !code) return;
    let live = true;
    previewScript({ ...request, language: lang, name: "preview" })
      .then((p) => live && setPreview(p))
      .catch(() => live && setPreview(null));
    return () => {
      live = false;
    };
  }, [review, online, request, lang, code]);
  if (!code) return null;
  // One button prints the whole pack: contents, summary, the pack and the answer sheets with boxes. The
  // browser names the PDF after the page title, so the title is set while it prints (the same name as the
  // audio): Cohort-Coach-Improvement-Track-PV-HEARD-en-2026-11-02.
  const rollList = map ? rollsFor(map, code) : { confirmed: [], possible: [] };
  // the note under the button names the roll numbers whose sheets are printed (a long list is cut short)
  const shortList = (xs: number[]) => (xs.length > 10 ? `${xs.slice(0, 10).join(", ")} ${tr("pack.print_more", { n: xs.length - 10 })}` : xs.join(", "));
  const rollsNote = [rollList.confirmed.length ? tr("pack.print_rolls", { list: shortList(rollList.confirmed) }) : "", rollList.possible.length ? tr("pack.print_rolls_possible", { list: shortList(rollList.possible) }) : ""].filter(Boolean).join(" · ");
  const printPack = async () => {
    setPrinting(true);
    const before = document.title;
    const done = () => {
      document.title = before;
      document.body.classList.remove("print-pack");
      window.removeEventListener("afterprint", done);
    };
    try {
      // one action: the click to the print dialog opening (the sheets fetched, boxed and drawn)
      await runAction("print_pack", async () => {
        setSheets(map && check && klass ? await loadSheets({ role, classId: klass.id, checkId: cohort.checkId, paperId: check.paperId, map, code, rolls: rollList }) : []);
        // let the block draw, and the photos load, before the page is hidden and printed
        await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
        await Promise.all(Array.from(document.querySelectorAll<HTMLImageElement>(".print-pack-only img")).map((i) => i.decode().catch(() => undefined)));
      });
      document.title = exportStem(code, speakLang, "Improvement-Track");
      document.body.classList.add("print-pack"); // the page is hidden while the pack prints
      window.addEventListener("afterprint", done);
      window.print();
    } finally {
      setPrinting(false);
    }
  };
  const draft = pack.sections.some((s) => s.draft);
  const editKey = `${code}|${lang}|${preview?.text ?? ""}`; // a change to the pack or the language drops her edit
  const edited = edit && edit.key === editKey ? edit.text : null;
  const whole = edited ?? preview?.text ?? "";
  const speakLang = edited !== null ? (preview?.language ?? lang) : lang;
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
      <div className="no-print">
        <ModuleTrack cohort={cohort} code={code} />
      </div>
      <PrintPack pack={pack} lang={lang} draft={draft} audioName={exportStem(code, speakLang)} rolls={rollList} sheets={sheets} />
      <div className="pack-actions no-print">
        <div className="pack-action">
          <button type="button" className="btn btn-secondary" disabled={printing} onClick={() => void printPack()} data-testid="pack-print">
            {printing ? tr("pack.print_preparing") : tr("pack.print")}
          </button>
          <span className="muted pack-note" data-testid="pack-print-note">
            {rollsNote ? tr("pack.print_note_rolls", { rolls: rollsNote }) : tr("pack.print_note")}
          </span>
        </div>
        <AudioDownload request={edited !== null ? { text: edited } : request} language={speakLang} code={code} label="audio.download" note={tr("audio.note")} testId={`audio-${code}-all`} />
      </div>
      <div className="pack-review no-print">
        <button type="button" className="btn pack-review-toggle" aria-expanded={review} onClick={() => setReview((v) => !v)} data-testid="pack-audio-review">
          {tr(review ? "pack.audio_hide" : "pack.audio_review")}
        </button>
        {review ? (
          <>
            {!online ? <p className="muted">{tr("pack.audio_offline")}</p> : null}
            <label className="field">
              <span>{tr("pack.audio_label")}</span>
              <textarea rows={10} maxLength={8000} value={whole} disabled={!preview} onChange={(e) => setEdit({ key: editKey, text: e.target.value })} data-testid="pack-audio-text" />
            </label>
            {edited !== null ? (
              <p className="muted">
                {tr("pack.audio_edited")}{" "}
                <button type="button" className="btn btn-secondary" onClick={() => setEdit(null)} data-testid="pack-audio-reset">
                  {tr("pack.audio_reset")}
                </button>
              </p>
            ) : null}
          </>
        ) : null}
      </div>
      <div className="stack">
        {pack.sections.map((s) => (
          <PackSectionView key={s.id} s={s} code={code} />
        ))}
      </div>
    </section>
  );
}
