// T2: manual check entry. Roll-ordered rows, the phone's own number keyboard in each box, blank and
// "can't read" marks, a sheet picker, absent children skipped, autosave after every key, and on-device diagnosis when she finishes. Per-child answers are
// saved on this phone only; only class counts are queued to send.
import { useCallback, useEffect, useRef, useState } from "react";
import { BLANK, enteredChildren, finishCheck, hasAnswers, UNREADABLE } from "../lib/check";
import { activeClass, db, getSetting, type CheckRow } from "../lib/db";
import { keys } from "../lib/diagnosis";
import { flushAllowed } from "../lib/sendnow";
import { hasConsent } from "../lib/consent";
import { isOnline } from "../lib/net";
import { go } from "../lib/router";
import { SimulatedBanner } from "../components/parts";
import { Icon } from "../components/icons";
import { applyReads, downscale, readSheet, SheetError } from "../lib/sheets";
import { stagesFor } from "../lib/stages";
import { CONCEPTS } from "../lib/stagecalc";
import { fetchSample } from "../lib/sample";
import { useJudge } from "../lib/roles";
import { useApp } from "../state";

const MAX_DIGITS = 9;

/** Per child, the concepts she tagged "missed the teaching on this". Stays on this phone. */
type Missed = Map<number, Set<string>>;

function missedFrom(check: CheckRow | null | undefined): Missed {
  const out: Missed = new Map();
  for (const [child, names] of Object.entries(check?.missedConcepts ?? {})) out.set(Number(child), new Set(names));
  for (const child of check?.missed ?? []) out.set(child, new Set(Object.keys(CONCEPTS))); // older whole-sheet tag
  return out;
}

function missedToStore(missed: Missed): Record<number, string[]> {
  return Object.fromEntries([...missed].filter(([, names]) => names.size > 0).map(([child, names]) => [child, [...names].sort()]));
}

/** Digits only, in any script the phone's keyboard offers (Devanagari and Tamil digits become 0-9). */
export function digitsOnly(raw: string): string {
  let out = "";
  for (const ch of raw) {
    const cp = ch.codePointAt(0) as number;
    if (cp >= 0x966 && cp <= 0x96f) out += String(cp - 0x966);
    else if (cp >= 0xbe6 && cp <= 0xbef) out += String(cp - 0xbe6);
    else if (ch >= "0" && ch <= "9") out += ch;
  }
  return out.slice(0, MAX_DIGITS);
}

/** "1-2", "3-5", "7-10": the questions a concept rests on, from the engine's rules. */
function questionsOf(items: number[]): string {
  const lo = Math.min(...items);
  const hi = Math.max(...items);
  return lo === hi ? String(lo) : `${lo}–${hi}`;
}

export default function Check({ onDone }: { onDone?: () => void } = {}) {
  const { tr, term, klass, check, reload } = useApp();
  const formKeys = Object.keys(keys.forms);
  const [formKey, setFormKey] = useState<string | null>(check?.formKey ?? null);
  const [rows, setRows] = useState<string[][]>(check?.children ?? []);
  const [child, setChild] = useState(0);
  const [q, setQ] = useState(0);
  const inputs = useRef<(HTMLInputElement | null)[]>([]);
  const [message, setMessage] = useState("");
  const [reading, setReading] = useState(false);
  const [photoNote, setPhotoNote] = useState("");
  const [flags, setFlags] = useState<Record<number, number[]>>({}); // boxes to check, per child; not saved
  const judge = useJudge();
  const [missed, setMissed] = useState<Missed>(missedFrom(check)); // tags, on this phone only
  const [absent, setAbsent] = useState<Set<number>>(new Set(check?.absent ?? [])); // skipped roll numbers
  const items = formKey ? (keys.forms[formKey]?.items.length ?? 10) : 10;
  // Writes go one after another, so the last key typed is always the last thing saved.
  const writes = useRef<Promise<void>>(Promise.resolve());
  const inFlight = useRef(0);
  const photoKids = useRef<Set<number>>(new Set(check?.viaPhoto ?? []));

  useEffect(() => {
    if (check) {
      setFormKey(check.formKey);
      setRows(check.children);
      photoKids.current = new Set(check.viaPhoto ?? []);
      setMissed(missedFrom(check));
      setAbsent(new Set(check.absent ?? []));
    }
  }, [check]);

  const save = useCallback(
    (next: string[][], form: string, tags: { missed?: Missed; absent?: Set<number> } = {}) => {
      setRows(next);
      setMessage("");
      inFlight.current += 1;
      writes.current = writes.current.then(async () => {
        const cls = klass ?? (await activeClass(false));
        const termNow = await getSetting("term", term);
        await db.checks.put({ id: `${cls.id}:${termNow}`, classId: cls.id, term: termNow, formKey: form, children: next, updatedAt: Date.now(), missedConcepts: missedToStore(tags.missed ?? missed), absent: [...(tags.absent ?? absent)], viaPhoto: [...photoKids.current] });
        inFlight.current -= 1;
        if (inFlight.current === 0) setMessage(tr("check.saved"));
      });
    },
    [klass, term, tr, missed, absent],
  );

  // Judge mode: fill the class from recorded reads of made-up sheets; the unsure boxes are marked.
  const useSample = async () => {
    try {
      const sample = await fetchSample();
      setFormKey(sample.form);
      photoKids.current = new Set();
      setMissed(new Map());
      setAbsent(new Set());
      save(sample.children, sample.form, { missed: new Map(), absent: new Set() });
      setFlags(Object.fromEntries(Object.entries(sample.unsure).map(([i, b]) => [Number(i), b])));
      setChild(Number(Object.keys(sample.unsure)[0] ?? 0));
      setQ(Object.values(sample.unsure)[0]?.[0] ?? 0);
      setPhotoNote("check.sample_done");
    } catch {
      setPhotoNote("check.photo_failed");
    }
  };

  const start = (form: string) => {
    setFormKey(form);
    const first = [Array.from({ length: keys.forms[form]?.items.length ?? 10 }, () => "")];
    setChild(0);
    setQ(0);
    save(first, form);
  };

  const setCell = (index: number, value: string) => {
    if (!formKey) return;
    const next = rows.map((r) => [...r]);
    const row = next[child] ?? Array.from({ length: items }, () => "");
    row[index] = value;
    next[child] = row;
    if (flags[child]?.includes(index)) setFlags({ ...flags, [child]: (flags[child] ?? []).filter((i) => i !== index) });
    save(next, formKey);
  };

  const goTo = (index: number) => {
    setChild(index);
    setQ(0);
    setPhotoNote("");
  };

  const toggleAbsent = (on: boolean) => {
    if (!formKey) return;
    if (on && hasAnswers(rows[child] ?? []) && !window.confirm(tr("check.absent_confirm"))) return;
    const nextAbsent = new Set(absent);
    const nextMissed = new Map(missed);
    const next = rows.map((r) => [...r]);
    if (on) {
      nextAbsent.add(child);
      nextMissed.delete(child);
      next[child] = Array.from({ length: items }, () => "");
      photoKids.current.delete(child);
    } else nextAbsent.delete(child);
    setAbsent(nextAbsent);
    setMissed(nextMissed);
    save(next, formKey, { absent: nextAbsent, missed: nextMissed });
  };

  const toggleMissed = (concept: string, on: boolean) => {
    const names = new Set(missed.get(child) ?? []);
    if (on) names.add(concept);
    else names.delete(concept);
    const next = new Map(missed).set(child, names);
    setMissed(next);
    if (formKey) save(rows, formKey, { missed: next });
  };

  const nextChild = () => {
    if (!formKey) return;
    if (child + 1 >= rows.length) save([...rows, Array.from({ length: items }, () => "")], formKey);
    goTo(child + 1);
  };

  // Photo of this child's sheet: the server reads it blind, the boxes fill in, and she checks them.
  const onPhoto = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = ""; // the same photo can be chosen again
    if (!file || !formKey) return;
    if (!hasConsent("core")) {
      setPhotoNote("check.photo_need_notice");
      return;
    }
    if (!isOnline()) {
      setPhotoNote("check.photo_offline");
      return;
    }
    if (hasAnswers(rows[child] ?? []) && !window.confirm(tr("check.photo_replace"))) return;
    setReading(true);
    setPhotoNote("");
    try {
      const cells = await readSheet(await downscale(file), formKey);
      const { row, flagged } = applyReads(cells, items);
      const next = rows.map((r) => [...r]);
      next[child] = row;
      photoKids.current.add(child);
      save(next, formKey);
      setFlags({ ...flags, [child]: flagged });
      setQ(flagged[0] ?? 0);
      setPhotoNote("check.photo_done");
    } catch (e) {
      const kind = e instanceof SheetError ? e.kind : "other";
      setPhotoNote(kind === "offline" ? "check.photo_offline" : kind === "typing" ? "check.photo_typing" : kind === "bad_photo" ? "check.photo_bad" : "check.photo_failed");
    } finally {
      setReading(false);
    }
  };

  const finish = async () => {
    if (!formKey) return;
    if (enteredChildren(rows).length === 0) {
      setMessage(tr("check.need_one"));
      return;
    }
    const cls = klass ?? (await activeClass(false));
    const termNow = await getSetting("term", term);
    const stages = stagesFor(formKey, rows, missed);
    await finishCheck(cls.id, termNow, formKey, rows, cls.simulated, undefined, stages);
    await reload();
    void flushAllowed(isOnline()).then(reload);
    if (onDone) onDone();
    else go("/cards");
  };

  if (!formKey) {
    return (
      <section aria-labelledby="check-title">
        <h1 id="check-title">{tr("check.title")}</h1>
        {klass?.simulated ? <SimulatedBanner /> : null}
        <p>{tr("check.order_note")}</p>
        <fieldset className="stack">
          <legend>{tr("check.form")}</legend>
          {formKeys.map((f) => (
            <button key={f} type="button" className="btn btn-secondary" onClick={() => start(f)} data-testid={`form-${f}`}>
              {tr(`check.form.${f}` as "check.form.A")}
            </button>
          ))}
        </fieldset>
        {judge ? (
          <button type="button" className="btn btn-primary" onClick={() => void useSample()} data-testid="use-sample">
            {tr("check.sample")}
          </button>
        ) : null}
        {photoNote ? <p role="status">{tr(photoNote as "check.sample_done")}</p> : null}
      </section>
    );
  }

  const row = rows[child] ?? [];
  const isAbsent = absent.has(child);
  const childState = (i: number): "check.state_absent" | "check.state_entered" | "check.state_empty" =>
    absent.has(i) ? "check.state_absent" : (rows[i] ?? []).some((c) => c !== "") ? "check.state_entered" : "check.state_empty";
  const focusNext = (i: number) => inputs.current[Math.min(items - 1, i + 1)]?.focus();
  const mine = missed.get(child) ?? new Set<string>();
  return (
    <section aria-labelledby="check-title">
      <h1 id="check-title">{tr("check.title")}</h1>
      {klass?.simulated ? <SimulatedBanner /> : null}
      <p className="muted">{tr("check.order_note")}</p>
      <h2 data-testid="child-title">{tr("check.child", { n: child + 1 })}</h2>
      <label className="field">
        <span>{tr("check.pick")}</span>
        <select value={child} onChange={(e) => goTo(Number(e.target.value))} data-testid="child-select">
          {rows.map((_, i) => (
            <option key={i} value={i}>
              {tr("check.child_option", { n: i + 1, state: tr(childState(i)) })}
            </option>
          ))}
        </select>
      </label>
      <label className="check">
        <input type="checkbox" checked={isAbsent} onChange={(e) => toggleAbsent(e.target.checked)} data-testid="absent" />
        <span>{tr("check.absent")}</span>
      </label>
      {isAbsent ? (
        <p className="muted" role="status" data-testid="absent-note">
          {tr("check.absent_note")}
        </p>
      ) : (
        <>
          <div className="boxes" role="group" aria-label={tr("check.child", { n: child + 1 })}>
            {Array.from({ length: items }, (_, i) => {
              const cell = row[i] ?? "";
              const special = cell === BLANK ? "blank" : cell === UNREADABLE ? "unreadable" : "";
              const flagged = flags[child]?.includes(i) ?? false;
              return (
                <div key={i} className={`${i === q ? "box box-on" : "box"}${flagged ? " box-check" : ""}`} data-check={flagged ? "true" : undefined} data-testid={`box-${i + 1}`}>
                  <label className="box-q" htmlFor={`cell-${i}`}>
                    {tr("check.q", { n: i + 1 })}
                  </label>
                  <input
                    id={`cell-${i}`}
                    ref={(el) => {
                      inputs.current[i] = el;
                    }}
                    className="box-input"
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    autoComplete="off"
                    enterKeyHint={i === items - 1 ? "done" : "next"}
                    value={special ? "" : cell}
                    placeholder={special === "blank" ? tr("check.value_blank") : special === "unreadable" ? tr("check.value_unreadable") : "–"}
                    data-state={special || undefined}
                    data-testid={`input-${i + 1}`}
                    onFocus={() => setQ(i)}
                    onChange={(e) => setCell(i, digitsOnly(e.target.value))}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        focusNext(i);
                      }
                    }}
                  />
                  <span className="box-marks">
                    <button type="button" className={special === "blank" ? "mark mark-on" : "mark"} aria-pressed={special === "blank"} aria-label={tr("check.mark_blank", { n: i + 1 })} onClick={() => setCell(i, special === "blank" ? "" : BLANK)} data-testid={`blank-${i + 1}`}>
                      {tr("check.blank")}
                    </button>
                    <button type="button" className={special === "unreadable" ? "mark mark-on" : "mark"} aria-pressed={special === "unreadable"} aria-label={tr("check.mark_unreadable", { n: i + 1 })} onClick={() => setCell(i, special === "unreadable" ? "" : UNREADABLE)} data-testid={`unreadable-${i + 1}`}>
                      ?
                    </button>
                  </span>
                  {flagged ? <span className="box-flag">{tr("check.photo_flag")}</span> : null}
                </div>
              );
            })}
          </div>
          <fieldset className="stack" data-testid="missed-group">
            <legend>{tr("check.missed_title")}</legend>
            {Object.entries(CONCEPTS).map(([concept, qs]) => (
              <label key={concept} className="check">
                <input type="checkbox" checked={mine.has(concept)} onChange={(e) => toggleMissed(concept, e.target.checked)} data-testid={`missed-${concept}`} />
                <span>{tr("check.missed_on", { concept: tr(`concept.${concept}` as "concept.addition"), qs: questionsOf(qs) })}</span>
              </label>
            ))}
          </fieldset>
          <label className={reading ? "btn btn-secondary photo-btn is-busy" : "btn btn-secondary photo-btn"} data-testid="photo-label">
            <Icon name="camera" /> <span>{reading ? tr("check.photo_reading") : tr("check.photo")}</span>
            <input type="file" accept="image/*" capture="environment" className="sr" onChange={(e) => void onPhoto(e)} disabled={reading} data-testid="photo-input" />
          </label>
        </>
      )}
      {photoNote ? (
        <p role="status" data-testid="photo-note">
          {tr(photoNote as "check.photo_done")}
        </p>
      ) : null}
      <div className="row">
        <button type="button" className="btn btn-secondary" onClick={() => goTo(Math.max(0, child - 1))} disabled={child === 0}>
          {tr("check.prev")}
        </button>
        <button type="button" className="btn btn-secondary" onClick={nextChild} data-testid="next-child">
          {tr("check.next")}
        </button>
      </div>
      <p className="muted" role="status" data-testid="check-count">
        {tr("check.count", { n: enteredChildren(rows).length })}
        {absent.size > 0 ? ` · ${tr("check.absent_count", { n: absent.size })}` : ""}
        {message ? ` · ${message}` : ""}
      </p>
      <button type="button" className="btn btn-primary" onClick={() => void finish()} data-testid="finish">
        {tr("check.finish")}
      </button>
    </section>
  );
}
