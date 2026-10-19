// T2: manual check entry. Roll-ordered rows, our own keypad, blank and "can't read" marks,
// autosave after every key, and on-device diagnosis when she finishes. Per-child answers are
// saved on this phone only; only class counts are queued to send.
import { useCallback, useEffect, useRef, useState } from "react";
import { BLANK, enteredChildren, finishCheck, hasAnswers, UNREADABLE } from "../lib/check";
import { activeClass, db, getSetting } from "../lib/db";
import { keys } from "../lib/diagnosis";
import { flush } from "../lib/sync";
import { isOnline } from "../lib/net";
import { go } from "../lib/router";
import { Keypad, SimulatedBanner } from "../components/parts";
import { applyReads, downscale, readSheet, SheetError } from "../lib/sheets";
import { useApp } from "../state";

const MAX_DIGITS = 9;

export default function Check() {
  const { tr, term, klass, check, reload } = useApp();
  const formKeys = Object.keys(keys.forms);
  const [formKey, setFormKey] = useState<string | null>(check?.formKey ?? null);
  const [rows, setRows] = useState<string[][]>(check?.children ?? []);
  const [child, setChild] = useState(0);
  const [q, setQ] = useState(0);
  const [message, setMessage] = useState("");
  const [reading, setReading] = useState(false);
  const [photoNote, setPhotoNote] = useState("");
  const [flags, setFlags] = useState<Record<number, number[]>>({}); // boxes to check, per child; not saved
  const items = formKey ? (keys.forms[formKey]?.items.length ?? 10) : 10;
  // Writes go one after another, so the last key typed is always the last thing saved.
  const writes = useRef<Promise<void>>(Promise.resolve());
  const inFlight = useRef(0);

  useEffect(() => {
    if (check) {
      setFormKey(check.formKey);
      setRows(check.children);
    }
  }, [check]);

  const save = useCallback(
    (next: string[][], form: string) => {
      setRows(next);
      setMessage("");
      inFlight.current += 1;
      writes.current = writes.current.then(async () => {
        const cls = klass ?? (await activeClass(false));
        const termNow = await getSetting("term", term);
        await db.checks.put({ id: `${cls.id}:${termNow}`, classId: cls.id, term: termNow, formKey: form, children: next, updatedAt: Date.now() });
        inFlight.current -= 1;
        if (inFlight.current === 0) setMessage(tr("check.saved"));
      });
    },
    [klass, term, tr],
  );

  const start = (form: string) => {
    setFormKey(form);
    const first = [Array.from({ length: keys.forms[form]?.items.length ?? 10 }, () => "")];
    setChild(0);
    setQ(0);
    save(first, form);
  };

  const edit = (fn: (cell: string) => string) => {
    if (!formKey) return;
    const next = rows.map((r) => [...r]);
    const row = next[child] ?? Array.from({ length: items }, () => "");
    row[q] = fn(row[q] ?? "");
    next[child] = row;
    if (flags[child]?.includes(q)) setFlags({ ...flags, [child]: (flags[child] ?? []).filter((i) => i !== q) });
    save(next, formKey);
  };

  const digit = (d: string) =>
    edit((cell) => {
      const base = cell === BLANK || cell === UNREADABLE ? "" : cell;
      return base.length >= MAX_DIGITS ? base : base + d;
    });
  const back = () => edit((cell) => (cell === BLANK || cell === UNREADABLE ? "" : cell.slice(0, -1)));

  const nextChild = () => {
    if (!formKey) return;
    if (child + 1 >= rows.length) save([...rows, Array.from({ length: items }, () => "")], formKey);
    setChild(child + 1);
    setQ(0);
    setPhotoNote("");
  };

  // Photo of this child's sheet: the server reads it blind, the boxes fill in, and she checks them.
  const onPhoto = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = ""; // the same photo can be chosen again
    if (!file || !formKey) return;
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
    await finishCheck(cls.id, termNow, formKey, rows, cls.simulated);
    await reload();
    void flush(isOnline()).then(reload);
    go("/cards");
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
      </section>
    );
  }

  const row = rows[child] ?? [];
  const shown = (cell: string) => (cell === "" ? "–" : cell === BLANK ? tr("check.value_blank") : cell === UNREADABLE ? tr("check.value_unreadable") : cell);
  return (
    <section aria-labelledby="check-title">
      <h1 id="check-title">{tr("check.title")}</h1>
      {klass?.simulated ? <SimulatedBanner /> : null}
      <p className="muted">{tr("check.order_note")}</p>
      <h2 data-testid="child-title">{tr("check.child", { n: child + 1 })}</h2>
      <div className="boxes" role="group" aria-label={tr("check.child", { n: child + 1 })}>
        {Array.from({ length: items }, (_, i) => (
          <button
            key={i}
            type="button"
            className={`${i === q ? "box box-on" : "box"}${flags[child]?.includes(i) ? " box-check" : ""}`}
            aria-pressed={i === q}
            data-check={flags[child]?.includes(i) ? "true" : undefined}
            onClick={() => setQ(i)}
            data-testid={`box-${i + 1}`}
          >
            <span className="box-q">{tr("check.q", { n: i + 1 })}</span>
            <span className="box-v">{shown(row[i] ?? "")}</span>
            {flags[child]?.includes(i) ? <span className="box-flag">{tr("check.photo_flag")}</span> : null}
          </button>
        ))}
      </div>
      <label className={reading ? "btn btn-secondary photo-btn is-busy" : "btn btn-secondary photo-btn"} data-testid="photo-label">
        {reading ? tr("check.photo_reading") : tr("check.photo")}
        <input type="file" accept="image/*" capture="environment" className="sr" onChange={(e) => void onPhoto(e)} disabled={reading} data-testid="photo-input" />
      </label>
      {photoNote ? (
        <p role="status" data-testid="photo-note">
          {tr(photoNote as "check.photo_done")}
        </p>
      ) : null}
      <Keypad
        onDigit={digit}
        onBack={back}
        onBlank={() => edit(() => BLANK)}
        onUnreadable={() => edit(() => UNREADABLE)}
        onNextQuestion={() => setQ(Math.min(items - 1, q + 1))}
      />
      <div className="row">
        <button type="button" className="btn btn-secondary" onClick={() => { setChild(Math.max(0, child - 1)); setQ(0); }} disabled={child === 0}>
          {tr("check.prev")}
        </button>
        <button type="button" className="btn btn-secondary" onClick={nextChild} data-testid="next-child">
          {tr("check.next")}
        </button>
      </div>
      <p className="muted" role="status" data-testid="check-count">
        {tr("check.count", { n: enteredChildren(rows).length })}
        {message ? ` · ${message}` : ""}
      </p>
      <button type="button" className="btn btn-primary" onClick={() => void finish()} data-testid="finish">
        {tr("check.finish")}
      </button>
    </section>
  );
}
