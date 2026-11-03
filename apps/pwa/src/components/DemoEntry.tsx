// Steps 4 and 5 of the demo: enter the check from the demo sheets, then review each one.
// Sheet 1 is read by the AI (a real call, cached by the image's hash). Auto-fill loads the other
// demo sheets from the demo answer file with no AI call, and says so. Each roll number shows its
// status; the drawer shows the sheet beside what was read, and only approved sheets go on to the
// error finder (the same finishCheck the check screen uses). Made-up sheets only.
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { finishCheck } from "../lib/check";
import { activeClass, db, type CheckKind } from "../lib/db";
import { slotForNew } from "../lib/checks";
import { DemoError, dcall, demoBlob, demoSession, demoSource, loadReads, matchSheet, pilotAutofill, pilotProbe, pilotRead, pilotSheet, pngText, rowFrom, saveReads, setDemoSource, type DemoSource, type PilotClassInfo, type PilotProbe, type ReadCell, type ReadsFile, type RollStatus } from "../lib/demoStudio";
import { formOf, keys } from "../lib/diagnosis";
import { fetchPaperKey } from "../lib/paperKeys";
import { stagesFor } from "../lib/stages";
import { useApp } from "../state";
import { isAiOff, useAiMode } from "../lib/aiMode";
import { Busy } from "./Busy";
import { AiOffNote, RecordedChip } from "./parts";

interface Read {
  cells: ReadCell[];
  source: "ai" | "file";
  name: string;
  url?: string; // the image, in memory only
  codeMismatch?: boolean;
  pilot?: boolean; // a real pilot sheet: kept in memory only, never in storage
  verified?: boolean;
  hasImage?: boolean;
}

/** The banner every screen that shows pilot data carries. */
export function PilotBanner() {
  const { tr } = useApp();
  return (
    <p className="chip chip-negative" role="note" data-testid="pilot-banner">
      {tr("pilot.banner")}
    </p>
  );
}

const ITEMS = keys.forms.A?.items.length ?? 10;
const ENTRY_KEY = "cc.demo.entry";

function saved(production: boolean): { status: Record<number, RollStatus>; reads: Record<number, Omit<Read, "url">> } {
  if (production || demoSource() === "pilot") return { status: {}, reads: {} }; // pilot answers are never stored
  try {
    const raw = localStorage.getItem(ENTRY_KEY);
    if (raw) return JSON.parse(raw) as { status: Record<number, RollStatus>; reads: Record<number, Omit<Read, "url">> };
  } catch {
    /* fresh */
  }
  return { status: {}, reads: {} };
}

/** `production` is Enter check on a machine with the pilot folder: the class's own sheets, the first read
 *  by call 8 and the rest filled from the answer file, for the paper attached to that check. Without it
 *  this is the demo's step 4, which offers made-up sheets only. */
export type PilotEntryFor = { paperId: string | null; paperCode: string | null; kind: CheckKind; formKey: string };

export function DemoEntry({ strength: synthStrength, classCode: synthCode, onFinished, production }: { strength: number; classCode: string; onFinished: () => void; production?: PilotEntryFor }) {
  const { tr, klass, reload } = useApp();
  const aiOff = isAiOff(useAiMode());
  const sid = demoSession();
  const [status, setStatus] = useState<Record<number, RollStatus>>(() => saved(!!production).status);
  const [reads, setReads] = useState<Record<number, Read>>(() => saved(!!production).reads as Record<number, Read>);
  const [answerFile, setAnswerFile] = useState<ReadsFile | null>(() => loadReads());
  const [open, setOpen] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [busyText, setBusyText] = useState("");
  const [msg, setMsg] = useState<{ text: string; bad?: boolean } | null>(null);
  const opener = useRef<HTMLButtonElement | null>(null);
  const lastJump = useRef<number | null>(null);
  const [source, setSource] = useState<DemoSource>(() => (production ? "pilot" : "synthetic"));
  const [probe, setProbe] = useState<PilotProbe>({ state: "hidden" });
  const [pilotCode, setPilotCode] = useState<string>("");
  const [firstRoll, setFirstRoll] = useState<number | null>(null);
  const [gallery, setGallery] = useState(false);
  const pilot = source === "pilot" && probe.state === "ready";
  const pilotInfo: PilotClassInfo | null = probe.state === "ready" ? (probe.manifest.classes.find((c) => c.class_code === pilotCode) ?? null) : null;
  const strength = pilot && pilotInfo ? pilotInfo.strength : synthStrength;
  const classCode = pilot && pilotInfo ? pilotInfo.class_code : synthCode;
  const rolls = Array.from({ length: strength }, (_, i) => i + 1);
  const openCode = pilot ? null : localStorage.getItem("cc.demo.paper.code");
  const pilotRoll = (r: number) => pilotInfo?.rolls.find((x) => x.roll === r);

  useEffect(() => {
    if (!production) {
      // the demo offers made-up sheets only; the pilot's real ones are for Enter check
      if (demoSource() === "pilot") setDemoSource("synthetic");
      return;
    }
    void pilotProbe().then((p) => {
      setProbe(p);
      if (p.state === "ready") {
        const ok = p.manifest.classes.find((c) => !c.dictation_override) ?? p.manifest.classes[0];
        setPilotCode((c) => c || (ok?.class_code ?? ""));
      }
    });
  }, [production]);

  useEffect(() => {
    if (source === "pilot") return; // pilot answers stay in memory only
    try {
      const plain = Object.fromEntries(Object.entries(reads).map(([k, v]) => [k, { ...v, url: undefined }]));
      localStorage.setItem(ENTRY_KEY, JSON.stringify({ status, reads: plain }));
    } catch {
      /* in memory only */
    }
  }, [status, reads, source]);

  useEffect(() => {
    if (answerFile || !sid) return;
    void dcall<ReadsFile>(`/${sid}/reads.json`)
      .then((r) => {
        saveReads(r);
        setAnswerFile(r);
      })
      .catch(() => undefined);
  }, [answerFile, sid]);

  useEffect(() => {
    const r = open !== null ? reads[open] : undefined;
    if (!pilot || open === null || !r || r.url || !r.hasImage) return;
    let gone = false;
    void pilotSheet(classCode, open)
      .then((blob) => {
        if (!gone) setReads((rr) => (rr[open] ? { ...rr, [open]: { ...rr[open]!, url: URL.createObjectURL(blob) } } : rr));
      })
      .catch(() => undefined);
    return () => {
      gone = true;
    };
  }, [open, pilot, classCode, reads]);

  function chooseSource(next: DemoSource) {
    if (next === source) return;
    setDemoSource(next);
    setSource(next);
    setReads({});
    setStatus({});
    setMsg(null);
    setOpen(null);
  }

  const put = (roll: number, read: Read) => {
    setReads((r) => ({ ...r, [roll]: read }));
    setStatus((s) => ({ ...s, [roll]: "needs_review" }));
  };

  async function aiRead(file: Blob, name: string, forRoll?: number): Promise<number | null> {
    if (!sid) return null;
    const form = new FormData();
    form.append("image", file, name);
    form.append("name", name);
    const out = await dcall<{ cells: ReadCell[]; roll: number | null; cached: boolean; check_code: string | null }>(`/${sid}/read`, { form });
    const roll = forRoll ?? out.roll ?? matchSheet(name, {}, classCode).roll;
    if (!roll) {
      setMsg({ text: tr("demo.entry.no_roll", { name }), bad: true });
      return null;
    }
    put(roll, { cells: out.cells, source: "ai", name, url: URL.createObjectURL(file), codeMismatch: !!(out.check_code && openCode && out.check_code !== openCode) });
    return roll;
  }

  async function onSheet1(files: FileList | null) {
    const file = files?.[0];
    if (!file) return;
    await guard("demo.busy.read1", async () => {
      const roll = await aiRead(file, file.name);
      if (roll) setMsg({ text: tr("demo.entry.read_ai", { roll }) });
    });
  }

  async function useDemoSheet1() {
    if (!sid) return;
    await guard("demo.busy.read1", async () => {
      const name = `${classCode}-roll01.png`;
      const roll = await aiRead(await demoBlob(`/${sid}/sheets/${name}`), name);
      if (roll) setMsg({ text: tr("demo.entry.read_ai", { roll }) });
    });
  }

  async function autoFill(files: { name: string; blob: Blob }[]) {
    const file = answerFile;
    let loaded = 0;
    let mismatch = 0;
    for (const f of files) {
      const meta = pngText(new Uint8Array(await f.blob.arrayBuffer()));
      const m = matchSheet(f.name, meta, classCode);
      if (!m.demo) {
        await aiRead(f.blob, f.name); // not a demo sheet: the AI reads it instead
        continue;
      }
      if (!m.roll || reads[m.roll]?.source === "ai") continue;
      const sheet = file?.sheets[`${classCode}-roll${String(m.roll).padStart(2, "0")}.png`];
      if (!sheet) continue;
      const bad = !!(m.checkCode && openCode && m.checkCode !== openCode);
      mismatch += bad ? 1 : 0;
      put(m.roll, { cells: sheet.cells, source: "file", name: f.name, url: URL.createObjectURL(f.blob), codeMismatch: bad });
      loaded += 1;
    }
    setMsg({ text: tr("demo.entry.autofilled", { n: loaded }) + (mismatch ? " " + tr("demo.entry.mismatch_n", { n: mismatch }) : "") });
  }

  async function onAutoFill(list: FileList | null) {
    if (!list?.length) return;
    if (!answerFile) {
      setMsg({ text: tr("demo.entry.need_answer_file"), bad: true });
      return;
    }
    await guard("demo.busy.autofill", () => autoFill(Array.from(list, (f) => ({ name: f.name, blob: f }))));
  }

  async function useDemoSheets() {
    if (!sid || !answerFile) return;
    await guard("demo.busy.autofill", async () => {
      const files = [];
      for (const r of rolls) {
        if (reads[r]?.source === "ai") continue;
        const name = `${classCode}-roll${String(r).padStart(2, "0")}.png`;
        files.push({ name, blob: await demoBlob(`/${sid}/sheets/${name}`) });
      }
      await autoFill(files);
    });
  }

  async function onAnswerFile(list: FileList | null) {
    const f = list?.[0];
    if (!f) return;
    try {
      const data = JSON.parse(await f.text()) as ReadsFile;
      if (!data.demo || !data.sheets) throw new Error("not an answer file");
      saveReads(data);
      setAnswerFile(data);
      setMsg({ text: tr("demo.entry.answer_file_ok") });
    } catch {
      setMsg({ text: tr("demo.entry.answer_file_bad"), bad: true });
    }
  }

  async function pilotReadFolder(roll: number) {
    await guard("demo.busy.read1", async () => {
      const out = await pilotRead(classCode, roll, undefined, production?.paperId);
      put(roll, { cells: out.cells, source: "ai", name: `${classCode}-roll${String(roll).padStart(2, "0")}`, pilot: true, hasImage: !!pilotRoll(roll)?.has_image });
      setMsg({ text: tr("demo.entry.read_ai", { roll }) });
    });
  }

  async function pilotReadPicked(list: FileList | null) {
    const file = list?.[0];
    if (!file || !firstRoll) return;
    await guard("demo.busy.read1", async () => {
      const out = await pilotRead(classCode, firstRoll, file, production?.paperId);
      put(firstRoll, { cells: out.cells, source: "ai", name: file.name, url: URL.createObjectURL(file), pilot: true });
      setMsg({ text: tr("demo.entry.read_ai", { roll: firstRoll }) });
    });
  }

  async function pilotFill() {
    await guard("demo.busy.autofill", async () => {
      const skip = rolls.filter((r) => reads[r]?.source === "ai");
      const out = await pilotAutofill(classCode, skip);
      for (const sh of out.sheets) {
        put(sh.roll, { cells: sh.cells, source: "file", name: `${classCode}-roll${String(sh.roll).padStart(2, "0")}`, pilot: true, verified: sh.verified, hasImage: sh.has_image });
      }
      setMsg({ text: tr("pilot.autofilled", { n: out.sheets.length }) });
    });
  }

  async function guard(what: string, fn: () => Promise<unknown>) {
    setBusy(true);
    setBusyText(what);
    setMsg(null);
    try {
      await fn();
    } catch (e) {
      setMsg({ text: e instanceof DemoError && e.message ? e.message : tr("demo.error"), bad: true });
    } finally {
      setBusy(false);
    }
  }

  const reviewNext = (from: number) => rolls.find((r) => r > from && status[r] === "needs_review") ?? rolls.find((r) => status[r] === "needs_review") ?? null;
  const approved = rolls.filter((r) => status[r] === "approved");
  const waiting = rolls.filter((r) => status[r] === "needs_review");

  // Next not entered: the next roll number with no sheet and no status, brought into view.
  function nextEmpty() {
    const from = lastJump.current ?? 0;
    const target = rolls.find((r) => r > from && !status[r]) ?? rolls.find((r) => !status[r]) ?? null;
    if (target === null) {
      setMsg({ text: tr("demo.entry.all_entered") });
      return;
    }
    lastJump.current = target;
    const row = document.querySelector<HTMLElement>(`[data-testid="demo-roll-${target}"]`);
    row?.scrollIntoView({ block: "center" });
    row?.focus();
    setMsg({ text: tr("demo.entry.next_empty_msg", { n: target }) });
  }

  async function finish() {
    const rest = rolls.filter((r) => status[r] !== "approved" && status[r] !== "absent").length;
    if (rest > 0 && !window.confirm(tr("demo.entry.finish_confirm", { n: rest }))) return;
    await guard("demo.busy.finish", async () => {
      const cls = klass ?? (await activeClass(true));
      const seq = slotForNew(await db.checks.where("classId").equals(cls.id).toArray(), cls.id);
      // the paper the sheets were written on: the one chosen in Enter check, or the demo's own paper (step 2)
      const formKey = production?.formKey ?? localStorage.getItem("cc.demo.paper") ?? "A";
      if (formKey.startsWith("P-") && !formOf(formKey)) await fetchPaperKey(formKey, { role: "teacher", classId: cls.id });
      const items = formOf(formKey)?.items.length ?? ITEMS; // the chosen paper's own number of items
      const rows = rolls.map((r) => (status[r] === "approved" && reads[r] ? rowFrom(reads[r].cells, items) : Array.from({ length: items }, () => "")));
      const absent = rolls.filter((r) => status[r] !== "approved").map((r) => r - 1);
      const paperId = production ? production.paperId : pilot ? null : localStorage.getItem("cc.demo.paper");
      await db.checks.put({
        id: `${cls.id}:${seq}`, classId: cls.id, term: seq, formKey, children: rows, updatedAt: Date.now(), absent, viaPhoto: approved.map((r) => r - 1),
        kind: production?.kind ?? "pre", round: 1, checkDate: pilot && pilotInfo ? pilotInfo.test_date : new Date().toISOString().slice(0, 10), paperVersion: keys.content_hash, trackId: null, expectedChildren: strength, status: "entering", confirm: false, paperId, paperCode: production ? production.paperCode : openCode,
      });
      const done = await finishCheck(cls.id, seq, formKey, rows, cls.simulated, undefined, stagesFor(formKey, rows, new Map()));
      await db.checks.update(`${cls.id}:${seq}`, { status: "closed", trackId: done.track });
      await reload();
      onFinished();
    });
  }

  const noSheet = (r: number): boolean => pilot && !status[r] && pilotRoll(r)?.status === "no_sheet" && !pilotRoll(r)?.has_image;
  const absentRoll = (r: number): boolean => pilot && !status[r] && pilotRoll(r)?.status === "absent";
  const label = (r: number): string => (noSheet(r) ? tr("pilot.no_sheet") : absentRoll(r) ? tr("demo.status.absent") : tr(`demo.status.${status[r] ?? "empty"}` as "demo.status.empty"));

  if (production && probe.state !== "ready") return null;
  return (
    <section className="stack" aria-labelledby="demo-entry-title" data-testid="demo-entry">
      <h2 id="demo-entry-title">{tr(production ? "pilot.entry.title" : "demo.s4.title")}</h2>
      {probe.state !== "hidden" ? (
        <fieldset className="card stack" data-testid="pilot-source">
          <legend>{tr("pilot.source.title")}</legend>
          <div className="row">
            <label className="row">
              <input type="radio" name="demo-source" checked={source === "synthetic"} onChange={() => chooseSource("synthetic")} data-testid="source-synthetic" />
              {tr("pilot.source.synthetic")}
            </label>
            <label className="row">
              <input type="radio" name="demo-source" checked={source === "pilot"} disabled={probe.state !== "ready"} onChange={() => chooseSource("pilot")} data-testid="source-pilot" />
              {tr("pilot.source.pilot")}
            </label>
          </div>
          <p className="muted">{probe.state === "ready" ? tr("pilot.source.note") : tr("pilot.unavailable", { reason: probe.reason })}</p>
        </fieldset>
      ) : null}
      {pilot ? <PilotBanner /> : null}
      <p className="chip" data-testid="demo-entry-label">
        {pilot ? tr("pilot.banner") : tr("demo.label.sheets")}
      </p>
      {pilot && probe.state === "ready" ? (
        <div className="card stack" data-testid="pilot-panel">
          <label className="field">
            <span>{tr("pilot.class")}</span>
            <select
              value={pilotCode}
              onChange={(e) => {
                setPilotCode(e.target.value);
                setReads({});
                setStatus({});
                setFirstRoll(null);
              }}
              data-testid="pilot-class"
            >
              {probe.manifest.classes.map((c) => (
                <option key={c.class_code} value={c.class_code} disabled={c.dictation_override}>
                  {tr("pilot.class_option", { code: c.class_code, n: c.strength })}
                </option>
              ))}
            </select>
          </label>
          {probe.manifest.classes
            .filter((c) => c.dictation_override)
            .map((c) => (
              <p key={c.class_code} className="muted">
                {tr("pilot.class_unsupported", { code: c.class_code })}
              </p>
            ))}
          <h3>{tr("pilot.first.title")}</h3>
          <p className="muted">{tr("pilot.first.note")}</p>
          <label className="field">
            <span>{tr("pilot.first.roll")}</span>
            <select value={firstRoll ?? ""} onChange={(e) => setFirstRoll(e.target.value ? Number(e.target.value) : null)} data-testid="pilot-first-roll">
              <option value="">-</option>
              {(pilotInfo?.rolls ?? [])
                .filter((x) => x.has_image)
                .map((x) => (
                  <option key={x.roll} value={x.roll}>
                    {tr("pilot.first.sheet", { n: x.roll })}
                  </option>
                ))}
            </select>
          </label>
          <div className="row">
            <button type="button" className="btn btn-primary" disabled={busy || !firstRoll || !pilotRoll(firstRoll)?.has_image} onClick={() => firstRoll && void pilotReadFolder(firstRoll)} data-testid="pilot-read">
              {tr("pilot.first.read")}
            </button>
            <label className="btn btn-secondary">
              {tr("pilot.first.pick")}
              <input type="file" accept="image/png,image/jpeg" className="sr" disabled={busy || !firstRoll} onChange={(e) => void pilotReadPicked(e.target.files)} data-testid="pilot-pick" />
            </label>
            <button type="button" className="btn btn-secondary" aria-expanded={gallery} onClick={() => setGallery((g) => !g)} data-testid="pilot-gallery-toggle">
              {tr("pilot.first.title")} ▾
            </button>
          </div>
          {gallery ? (
            <ul className="plain row" data-testid="pilot-gallery">
              {(pilotInfo?.rolls ?? [])
                .filter((x) => x.has_image)
                .map((x) => (
                  <li key={x.roll}>
                    <Thumb classCode={classCode} roll={x.roll} selected={firstRoll === x.roll} onPick={() => setFirstRoll(x.roll)} />
                  </li>
                ))}
            </ul>
          ) : null}
          <h3>{tr("demo.entry.autofill_title")}</h3>
          <p className="muted">{tr("pilot.autofill_note")}</p>
          <button type="button" className="btn btn-primary" disabled={busy} onClick={() => void pilotFill()} data-testid="pilot-autofill">
            {tr("pilot.autofill")}
          </button>
        </div>
      ) : null}
      <div className="card stack" hidden={pilot}>
        <h3>{tr("demo.entry.sheet1")}</h3>
        <p className="muted">{tr("demo.entry.sheet1_note")}</p>
        <AiOffNote text={tr("ai.off.read")} testId="demo-ai-off" />
        <div className="row">
          <label className={aiOff ? "btn btn-secondary is-disabled" : "btn btn-secondary"} aria-disabled={aiOff || undefined}>
            {tr("demo.entry.upload1")}
            <input type="file" accept="image/png,image/jpeg" className="sr" disabled={busy || aiOff} onChange={(e) => void onSheet1(e.target.files)} data-testid="demo-upload-1" />
          </label>
          <button type="button" className="btn btn-secondary" disabled={busy || aiOff} onClick={() => void useDemoSheet1()} data-testid="demo-use-1">
            {tr("demo.entry.use1")}
          </button>
        </div>
      </div>
      <div className="card stack" hidden={pilot}>
        <h3>{tr("demo.entry.autofill_title")}</h3>
        <p className="muted">{tr("demo.entry.autofill_note")}</p>
        <div className="row">
          <label className="btn btn-secondary">
            {tr("demo.entry.autofill_upload")}
            <input type="file" multiple accept="image/png,image/jpeg" className="sr" disabled={busy} onChange={(e) => void onAutoFill(e.target.files)} data-testid="demo-autofill-files" />
          </label>
          <button type="button" className="btn btn-primary" disabled={busy || !answerFile} onClick={() => void useDemoSheets()} data-testid="demo-autofill">
            {tr("demo.entry.autofill")}
          </button>
        </div>
        {!answerFile ? (
          <label className="field">
            <span>{tr("demo.entry.answer_file_upload")}</span>
            <input type="file" accept="application/json" onChange={(e) => void onAnswerFile(e.target.files)} data-testid="demo-answer-file" />
          </label>
        ) : null}
      </div>
      {busy ? <Busy ai text={tr((busyText || "demo.working") as "demo.working")} testId="demo-busy" /> : null}
      {msg ? (
        <p role={msg.bad ? "alert" : "status"} data-testid="demo-entry-msg">
          {msg.text}
        </p>
      ) : null}

      <h3>{tr("demo.entry.rolls_title")}</h3>
      <p className="muted" data-testid="demo-entry-progress">
        {tr("demo.entry.progress", { approved: approved.length, waiting: waiting.length, total: strength })}
      </p>
      <button type="button" className="btn btn-secondary" onClick={nextEmpty} data-testid="demo-next-empty">
        {tr("check.next_empty")}
      </button>
      <ul className="plain demo-rolls" data-testid="demo-rolls">
        {rolls.map((r) => (
          <li key={r} className="demo-roll" tabIndex={-1} data-testid={`demo-roll-${r}`} data-status={status[r] ?? "empty"}>
            <span className="demo-roll-n">{tr("demo.entry.roll", { n: r })}</span>
            <span className="chip">{label(r)}</span>
            {reads[r] ? <span className="muted">{reads[r].source === "ai" ? tr("demo.read.ai") : reads[r].pilot ? tr("pilot.read_file") : tr("demo.read.file")}</span> : null}
            {reads[r]?.source === "ai" ? <RecordedChip testId={`demo-recorded-${r}`} /> : null}
            {reads[r]?.source === "file" && reads[r].pilot ? <span className="chip">{reads[r].verified ? tr("pilot.verified") : tr("pilot.unverified")}</span> : null}
            {pilot && !reads[r] && pilotRoll(r)?.has_image && !pilotRoll(r)?.in_answer_file ? <span className="muted">{tr("pilot.unread")}</span> : null}
            {reads[r]?.codeMismatch ? <span className="chip chip-negative">{tr("demo.entry.mismatch")}</span> : null}
            {!reads[r] && !noSheet(r) && !absentRoll(r) ? (
              <button
                type="button"
                className="chip-btn"
                aria-pressed={status[r] === "absent"}
                aria-label={tr(status[r] === "absent" ? "demo.entry.absent_undo_n" : "demo.entry.absent_n", { n: r })}
                onClick={() => setStatus((s) => (s[r] === "absent" ? Object.fromEntries(Object.entries(s).filter(([k]) => Number(k) !== r)) : { ...s, [r]: "absent" }))}
                data-testid={`demo-absent-${r}`}
              >
                {tr(status[r] === "absent" ? "demo.entry.absent_undo" : "demo.status.absent")}
              </button>
            ) : null}
            {reads[r] ? (
              <button
                type="button"
                className="chip-btn"
                aria-label={tr("demo.entry.preview", { n: r })}
                onClick={(e) => {
                  opener.current = e.currentTarget;
                  setOpen(r);
                }}
                data-testid={`demo-preview-${r}`}
              >
                {tr("demo.entry.open")}
              </button>
            ) : null}
          </li>
        ))}
      </ul>
      <button type="button" className="btn btn-primary" disabled={busy || approved.length === 0 || waiting.length > 0} onClick={() => void finish()} data-testid="demo-finish">
        {tr("demo.entry.finish")}
      </button>
      {waiting.length > 0 ? <p className="muted">{tr("demo.entry.finish_note")}</p> : null}
      {pilot ? <p className="muted">{tr("pilot.finish_note")}</p> : null}

      {open !== null && reads[open] ? (
        <ReviewDrawer
          roll={open}
          read={reads[open]}
          onClose={() => {
            setOpen(null);
            opener.current?.focus();
          }}
          onApprove={(cells) => {
            setReads((rr) => ({ ...rr, [open]: { ...rr[open]!, cells } }));
            setStatus((s) => ({ ...s, [open]: "approved" }));
            const next = reviewNext(open);
            setOpen(next !== null && next !== open ? next : null);
          }}
          onNext={() => setOpen(reviewNext(open))}
          onAbsent={() => {
            setStatus((s) => ({ ...s, [open]: "absent" }));
            setOpen(reviewNext(open));
          }}
          onReread={async () => {
            const read = reads[open];
            if (read?.pilot) {
              const blob = read.url ? await (await fetch(read.url)).blob() : undefined;
              await guard("demo.busy.reread", async () => {
                const out = await pilotRead(classCode, open, blob, production?.paperId);
                put(open, { cells: out.cells, source: "ai", name: read.name, url: read.url, pilot: true, hasImage: read.hasImage });
              });
              return;
            }
            if (!read?.url) return;
            const blob = await (await fetch(read.url)).blob();
            await guard("demo.busy.reread", () => aiRead(blob, read.name, open));
          }}
        />
      ) : null}
    </section>
  );
}

function ReviewDrawer({ roll, read, onClose, onApprove, onNext, onAbsent, onReread }: { roll: number; read: Read; onClose: () => void; onApprove: (cells: ReadCell[]) => void; onNext: () => void; onAbsent: () => void; onReread: () => Promise<void> }) {
  const { tr } = useApp();
  const aiOff = isAiOff(useAiMode());
  const [cells, setCells] = useState<ReadCell[]>(read.cells);
  const [zoom, setZoom] = useState(1);
  const [turn, setTurn] = useState(0);
  const first = useRef<HTMLButtonElement | null>(null);

  useEffect(() => setCells(read.cells), [read]);
  useEffect(() => {
    first.current?.focus();
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [onClose, roll]);

  return createPortal(
    <div className="demo-drawer" role="dialog" aria-modal="false" aria-labelledby="demo-drawer-title" data-testid="demo-drawer">
      <div className="demo-drawer-head">
        <h3 id="demo-drawer-title">{tr("demo.drawer.title", { n: roll })}</h3>
        {read.pilot ? <PilotBanner /> : null}
        <span className="chip" data-testid="demo-drawer-source">
          {read.source === "ai" ? tr("demo.read.ai") : read.pilot ? tr("pilot.read_file") : tr("demo.read.file")}
        </span>
        {read.source === "ai" ? <RecordedChip testId="demo-drawer-recorded" /> : null}
        {read.pilot && read.source === "file" ? <span className="chip">{read.verified ? tr("pilot.verified") : tr("pilot.unverified")}</span> : null}
        <button type="button" className="chip-btn" ref={first} onClick={onClose} data-testid="demo-drawer-close">
          {tr("common.close")}
        </button>
      </div>
      <div className="demo-drawer-body">
        <div className="demo-drawer-image" role="region" tabIndex={0} aria-label={tr("demo.drawer.image")}>
          {read.url ? <img src={read.url} alt={read.pilot ? tr("pilot.sheet_alt", { n: roll }) : tr("demo.drawer.image_alt", { n: roll })} style={{ transform: `scale(${zoom}) rotate(${turn}deg)` }} data-testid="demo-drawer-img" /> : <p className="muted">{tr("demo.drawer.no_image")}</p>}
        </div>
        <div className="stack">
          <div className="row">
            <button type="button" className="chip-btn" onClick={() => setZoom((z) => Math.min(3, z + 0.5))}>
              {tr("demo.drawer.zoom_in")}
            </button>
            <button type="button" className="chip-btn" onClick={() => setZoom((z) => Math.max(1, z - 0.5))}>
              {tr("demo.drawer.zoom_out")}
            </button>
            <button type="button" className="chip-btn" onClick={() => setTurn((t) => (t + 90) % 360)}>
              {tr("demo.drawer.rotate")}
            </button>
          </div>
          <ol className="plain demo-cells">
            {cells.map((c, i) => (
              <li key={i} className={c.status === "check" ? "demo-cell demo-cell-low" : "demo-cell"}>
                <label>
                  <span>
                    {tr("demo.drawer.box", { n: i + 1 })}
                    {c.status === "check" ? ` · ${tr("demo.drawer.unsure")}` : ""}
                  </span>
                  <input
                    inputMode="numeric"
                    value={c.status === "blank" ? "" : c.text}
                    maxLength={7}
                    onChange={(e) => setCells(cells.map((x, j) => (j === i ? { text: e.target.value.replace(/\D/g, ""), status: e.target.value ? "ok" : "blank" } : x)))}
                    data-testid={`demo-cell-${i + 1}`}
                  />
                </label>
              </li>
            ))}
          </ol>
          <div className="row">
            <button type="button" className="btn btn-primary" onClick={() => onApprove(cells)} data-testid="demo-approve">
              {tr("demo.drawer.approve")}
            </button>
            <button type="button" className="btn btn-secondary" onClick={onNext} data-testid="demo-next-unreviewed">
              {tr("demo.drawer.next")}
            </button>
            <button type="button" className="btn btn-secondary" onClick={onAbsent} data-testid="demo-absent">
              {tr("demo.drawer.absent")}
            </button>
            <button type="button" className="btn btn-secondary" disabled={aiOff || (!read.url && !read.hasImage)} aria-describedby={aiOff ? "demo-reread-off" : undefined} onClick={() => void onReread()} data-testid="demo-reread">
              {tr("demo.drawer.reread")}
            </button>
          </div>
          {aiOff ? (
            <p className="muted" id="demo-reread-off" data-testid="demo-reread-off">
              {tr("ai.off.reread")}
            </p>
          ) : null}
        </div>
      </div>
    </div>,
    document.body,
  );
}

function Thumb({ classCode, roll, selected, onPick }: { classCode: string; roll: number; selected: boolean; onPick: () => void }) {
  const { tr } = useApp();
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    let gone = false;
    let made: string | null = null;
    void pilotSheet(classCode, roll)
      .then((blob) => {
        if (gone) return;
        made = URL.createObjectURL(blob);
        setUrl(made);
      })
      .catch(() => undefined);
    return () => {
      gone = true;
      if (made) URL.revokeObjectURL(made);
    };
  }, [classCode, roll]);
  return (
    <button type="button" className={selected ? "chip-btn chip-selected" : "chip-btn"} aria-pressed={selected} onClick={onPick} data-testid={`pilot-thumb-${roll}`}>
      {url ? <img src={url} alt={tr("pilot.sheet_alt", { n: roll })} width={72} /> : null}
      <span>{tr("pilot.first.sheet", { n: roll })}</span>
    </button>
  );
}
