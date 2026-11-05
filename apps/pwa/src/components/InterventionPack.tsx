// Intervention content for a cohort: for each of its errors (most common first), sections built from
// the class's own results and approved content, text first: a bold title and plain text for each, all open,
// and it prints. Nothing plays by itself: one "Download audio" button per error makes a single file, only
// when pressed. Sections with no content are left out, never invented.
import { useEffect, useMemo, useState } from "react";
import { LANG_NAMES, type Key } from "../i18n";
import type { ClassCohort } from "../lib/classCohort";
import { buildPack } from "../lib/pack";
import { buildAnswerMap, inThisClass, rollsFor } from "../lib/results";
import { useApp } from "../state";
import { exportStem } from "../lib/packAudio";
import { runAction } from "../lib/action";
import { useDevTesting } from "../lib/aiMode";
import type { TrackView } from "../lib/modules";
import { DevAudioAll } from "./DevAudioAll";
import { ModuleTrack } from "./ModuleTrack";
import { PackSectionView } from "./PackSection";
import { PrintPack } from "./PrintPack";
import { loadSheets, type PrintSheet } from "../lib/printPack";
import { db, type CheckRow } from "../lib/db";

export function InterventionPack({ cohort }: { cohort: ClassCohort }) {
  const { tr, lang, check: current, role, klass } = useApp();
  // The cohort's own check, not whichever check is current: once another check is entered the current one is a different
  // check, and the answer map and the printed sheets would be empty.
  const [own, setOwn] = useState<CheckRow | null>(null);
  useEffect(() => {
    let live = true;
    if (current && current.id === cohort.checkId) setOwn(null);
    else void db.checks.get(cohort.checkId).then((c) => live && setOwn(c ?? null));
    return () => {
      live = false;
    };
  }, [cohort.checkId, current]);
  const check = current && current.id === cohort.checkId ? current : own;
  const [active, setActive] = useState(cohort.errors[0] ?? "");
  const [printing, setPrinting] = useState(false);
  const [sheets, setSheets] = useState<PrintSheet[]>([]);
  const [modTrack, setModTrack] = useState<TrackView | null>(null);
  const devTesting = useDevTesting();
  const map = useMemo(() => (check && check.id === cohort.checkId ? buildAnswerMap(check.formKey, check.children, check.absent ?? [], check.approved) : null), [check, cohort.checkId]);
  const code = cohort.errors.includes(active) ? active : (cohort.errors[0] ?? "");
  const pack = useMemo(
    () =>
      buildPack({ code, lang, children: cohort.counts[code] ?? 0, total: cohort.childrenChecked, here: map ? inThisClass(map, code) : null, rolls: map ? rollsFor(map, code) : null, rule: cohort.rule }, (id, c) => {
        console.info(`pack: no content for section "${id}" of ${c}; left out`);
      }),
    [code, lang, cohort, map],
  );
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
      document.title = exportStem(code, lang, "Improvement-Track");
      document.body.classList.add("print-pack"); // the page is hidden while the pack prints
      window.addEventListener("afterprint", done);
      window.print();
    } finally {
      setPrinting(false);
    }
  };
  const draft = pack.sections.some((s) => s.draft);
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
        <ModuleTrack cohort={cohort} code={code} onTrackChange={setModTrack} />
      </div>
      <PrintPack pack={pack} lang={lang} draft={draft} rolls={rollList} sheets={sheets} track={modTrack} />
      <div className="pack-actions no-print">
        <div className="pack-action">
          <button type="button" className="btn btn-secondary" disabled={printing} onClick={() => void printPack()} data-testid="pack-print">
            {printing ? tr("pack.print_preparing") : tr("pack.print")}
          </button>
          <span className="muted pack-note" data-testid="pack-print-note">
            {rollsNote ? tr("pack.print_note_rolls", { rolls: rollsNote }) : tr("pack.print_note")}
          </span>
        </div>
        {devTesting ? <DevAudioAll track={modTrack} code={code} /> : null}
      </div>
      <div className="stack">
        {pack.sections.map((s) => (
          <PackSectionView key={s.id} s={s} code={code} />
        ))}
      </div>
    </section>
  );
}
