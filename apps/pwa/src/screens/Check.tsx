// T2: check entry. One roll number at a time: the boxes (typed, or filled from a picture the AI read), the
// "missed the teaching" checkboxes, and Approve. A roll counts only once she has approved it (or marked the
// child absent), and Finish entering waits until every roll is approved or absent. Per-child answers are
// saved on this phone only; only class counts are queued to send. Sheet pictures are held in memory and
// dropped at Finish: never saved, never sent again.
import { useCallback, useEffect, useRef, useState } from "react";
import { BLANK, enteredChildren, finishCheck, hasAnswers, UNREADABLE } from "../lib/check";
import { activeClass, db, getSetting, type CheckRow, type ProfileRow } from "../lib/db";
import { formOf, keys } from "../lib/diagnosis";
import { flushAllowed } from "../lib/sendnow";
import { getConsent, hasConsent, recordOnServer, setConsent, type Choices } from "../lib/consent";
import { deleteKept, fetchKept, keepSheet, keepStatus, listKept, type Kept } from "../lib/keptSheets";
import { isOnline, useOnline } from "../lib/net";
import { go } from "../lib/router";
import { RecordedChip, SimulatedBanner } from "../components/parts";
import { isAiOff, isRecorded, useAiMode, useDevTesting } from "../lib/aiMode";
import { Icon } from "../components/icons";
import { applyReads, SheetError } from "../lib/sheets";
import { readPicture, AddSheets, type ReadResult } from "../components/AddSheets";
import { SheetDrawer } from "../components/SheetDrawer";
import { stagesFor } from "../lib/stages";
import { useHubIdentity } from "../components/PaperHubParts";
import { fetchPaperKey } from "../lib/paperKeys";
import { StartCheck, type CheckMeta } from "../components/StartCheck";
import { formatCheckLabel, shownClassName, suggestKind, today, trackToEvaluate } from "../lib/checks";
import { pcall } from "../lib/papers";
import { afterApprove, conceptQuestions, countRolls, dataState, finishGate, formatQuestions, isApproved, listRolls, nextNotEntered, nextToApprove, optionKey, type RollSet } from "../lib/rolls";
import { useApp } from "../state";

const MAX_DIGITS = 9;

/** Per child, the concepts she tagged "missed the teaching on this". Stays on this phone. */
type Missed = Map<number, Set<string>>;

function missedFrom(check: CheckRow | null | undefined): Missed {
  const out: Missed = new Map();
  for (const [child, names] of Object.entries(check?.missedConcepts ?? {})) out.set(Number(child), new Set(names));
  for (const child of check?.missed ?? []) out.set(child, new Set(["addition", "place_value", "subtraction"])); // older whole-sheet tag
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

type Meta = CheckMeta & { confirm: boolean };

function metaOf(check: CheckRow | null | undefined): Meta | null {
  return check?.kind ? { kind: check.kind, checkDate: check.checkDate ?? today(), expectedChildren: check.expectedChildren ?? null, confirm: !!check.confirm, paperId: check.paperId ?? null, paperCode: check.paperCode ?? null } : null;
}

/** Everything about the rolls that changes together, kept in one object so a write never sees half of it. */
interface Snap {
  rows: string[][];
  absent: Set<number>;
  approved: Set<number>;
  missed: Missed;
}

function snapOf(check: CheckRow | null | undefined): Snap {
  return { rows: check?.children ?? [], absent: new Set(check?.absent ?? []), approved: new Set(check?.approved ?? []), missed: missedFrom(check) };
}

const emptyRow = (n: number) => Array.from({ length: n }, () => "");

interface Picture {
  url: string;
  blob: Blob;
  sha: string;
}

export default function Check({ onDone }: { onDone?: () => void } = {}) {
  const { tr, lang, term, klass, check, reload, role } = useApp();
  const aiMode = useAiMode();
  const devTesting = useDevTesting();
  // Testing only: the roll numbers the "mark the rest absent" box marked, so unticking it can undo exactly those.
  const [devAbsent, setDevAbsent] = useState<Set<number>>(new Set());
  const aiOff = isAiOff(aiMode);
  const online = useOnline();
  const [formKey, setFormKey] = useState<string | null>(check?.formKey ?? null);
  const snap = useRef<Snap>(snapOf(check));
  const [, bump] = useState(0);
  const [child, setChild] = useState(0);
  const [q, setQ] = useState(0);
  const inputs = useRef<(HTMLInputElement | null)[]>([]);
  const [message, setMessage] = useState("");
  const [reading, setReading] = useState(false);
  const [photoNote, setPhotoNote] = useState("");
  const [flags, setFlags] = useState<Record<number, number[]>>({}); // boxes to check, per child; not saved
  // The pictures, in memory only: gone when she leaves this screen or finishes.
  const [pics, setPics] = useState<Record<number, Picture>>({});
  const picUrls = useRef<Set<string>>(new Set());
  const [drawer, setDrawer] = useState(false);
  // Approved sheets kept for her for 60 days (only if she agreed): which roll numbers have a kept copy.
  const [keepOn, setKeepOn] = useState(false);
  const [retention, setRetention] = useState(60);
  const [kept, setKept] = useState<Record<number, Kept>>({});
  const [keepNote, setKeepNote] = useState("");
  const [asked, setAsked] = useState(() => getConsent()?.keep_sheets !== undefined);
  const iconRef = useRef<HTMLButtonElement>(null);
  const who = useHubIdentity();
  const [, setKeyTick] = useState(0);
  useEffect(() => {
    if (formKey && formKey.startsWith("P-") && !formOf(formKey)) void fetchPaperKey(formKey, who).then(() => setKeyTick((n) => n + 1)).catch(() => undefined);
  }, [formKey]); // only when the paper changes
  const form = formKey ? formOf(formKey) : undefined;
  const items = form?.items.length ?? 10;
  // Writes go one after another, so the last key typed is always the last thing saved.
  const writes = useRef<Promise<void>>(Promise.resolve());
  const inFlight = useRef(0);
  const photoKids = useRef<Set<number>>(new Set(check?.viaPhoto ?? []));
  const [meta, setMeta] = useState<Meta | null>(metaOf(check));
  const metaRef = useRef(meta);
  metaRef.current = meta;
  const [history, setHistory] = useState<CheckRow[]>([]);
  const [profiles, setProfiles] = useState<ProfileRow[]>([]);
  const [reopened, setReopened] = useState(false); // a finished check opened again for changes

  const checkKey = klass ? `${klass.id}:${term}` : "";
  useEffect(() => {
    if (!klass?.id || !formKey) return;
    void keepStatus(role, klass.id).then((s) => {
      setKeepOn(s.enabled);
      setRetention(s.retention_days);
      if (s.enabled) void listKept(role, klass.id, `${klass.id}:${term}`).then((l) => setKept(Object.fromEntries(l.map((k) => [k.roll - 1, k]))));
    });
  }, [klass?.id, term, formKey, role]);

  const dropPictures = useCallback(() => {
    picUrls.current.forEach((u) => URL.revokeObjectURL(u));
    picUrls.current.clear();
    setPics({});
  }, []);
  useEffect(() => {
    const urls = picUrls.current;
    return () => urls.forEach((u) => URL.revokeObjectURL(u));
  }, []);

  useEffect(() => {
    if (check && inFlight.current === 0) {
      setFormKey(check.formKey);
      snap.current = snapOf(check);
      photoKids.current = new Set(check.viaPhoto ?? []);
      setMeta(metaOf(check));
      bump((n) => n + 1);
    }
  }, [check]);

  useEffect(() => {
    const id = klass?.id;
    if (!id) return;
    void Promise.all([db.checks.where("classId").equals(id).toArray(), db.profiles.where("classId").equals(id).toArray()]).then(([c, p]) => {
      setHistory(c);
      setProfiles(p);
    });
  }, [klass?.id, check]);

  /** Make `next` the current state and save it on this phone. */
  const commit = useCallback(
    (next: Snap, form: string | null = null, over?: Meta) => {
      snap.current = next;
      bump((n) => n + 1);
      setMessage("");
      inFlight.current += 1;
      writes.current = writes.current.then(async () => {
        const key = form ?? formKey;
        const cls = klass ?? (await activeClass(false));
        const termNow = await getSetting("term", term);
        const m = over ?? metaRef.current ?? { kind: suggestKind(history, profiles, termNow), checkDate: today(), expectedChildren: null, confirm: false };
        if (key) {
          await db.checks.put({
            id: `${cls.id}:${termNow}`, classId: cls.id, term: termNow, formKey: key, children: next.rows, updatedAt: Date.now(), missedConcepts: missedToStore(next.missed), absent: [...next.absent], approved: [...next.approved], viaPhoto: [...photoKids.current],
            kind: m.kind, round: 1, checkDate: m.checkDate, paperVersion: keys.content_hash, trackId: m.kind === "post" ? trackToEvaluate(history, profiles) : null, expectedChildren: m.expectedChildren, status: "entering", confirm: m.confirm,
            paperId: m.paperId ?? null, paperCode: m.paperCode ?? null,
          });
        }
        inFlight.current -= 1;
        if (inFlight.current === 0) setMessage(tr("check.saved"));
      });
    },
    [klass, term, tr, formKey, history, profiles],
  );

  const clone = (): Snap => ({ rows: snap.current.rows.map((r) => [...r]), absent: new Set(snap.current.absent), approved: new Set(snap.current.approved), missed: new Map(snap.current.missed) });
  const size = meta?.expectedChildren ?? null;
  const setOf = (): RollSet => ({ rows: snap.current.rows, absent: snap.current.absent, approved: snap.current.approved });
  const rollTotal = Math.max(snap.current.rows.length, size ?? 0);
  const rowAt = (s: Snap, i: number) => s.rows[i] ?? emptyRow(items);
  const ensure = (s: Snap, i: number) => {
    while (s.rows.length <= i) s.rows.push(emptyRow(items));
  };

  const start = (form: string, chosen: CheckMeta) => {
    const m = { ...chosen, confirm: false };
    setMeta(m);
    setFormKey(form);
    setChild(0);
    setQ(0);
    dropPictures();
    const n = formOf(form)?.items.length ?? 10;
    commit({ rows: Array.from({ length: Math.max(1, m.expectedChildren ?? 1) }, () => emptyRow(n)), absent: new Set(), approved: new Set(), missed: new Map() }, form, m);
  };

  const entered = enteredChildren(snap.current.rows).length;

  // A wrong paper chosen by mistake: back to the paper list. Before any answer it is free; after, she is asked
  // first and the roll numbers entered so far are cleared (the paper stays as it was).
  // Clear everything entered in this check (answers, approvals, absent marks, tags, pictures in memory) and start the
  // roll list again on the same paper and class size. Copies already kept online stay until she deletes them or 60 days pass.
  const clearEntered = () => {
    if (!formKey) return;
    const any = entered > 0 || snap.current.absent.size > 0 || snap.current.approved.size > 0;
    if (!any) return;
    if (!window.confirm(tr("check.clear_confirm", { n: entered + snap.current.absent.size }) + (Object.keys(kept).length > 0 ? " " + tr("check.clear_kept") : ""))) return;
    dropPictures();
    setDrawer(false);
    photoKids.current = new Set();
    setFlags({});
    setDevAbsent(new Set());
    setChild(0);
    setQ(0);
    setPhotoNote("");
    commit({ rows: Array.from({ length: Math.max(1, size ?? 1) }, () => emptyRow(items)), absent: new Set(), approved: new Set(), missed: new Map() });
  };

  const chooseAnother = async () => {
    if ((entered > 0 || snap.current.absent.size > 0) && !window.confirm(tr("check.another_confirm", { n: entered + snap.current.absent.size }))) return;
    await writes.current;
    const cls = klass ?? (await activeClass(false));
    const termNow = await getSetting("term", term);
    await db.checks.delete(`${cls.id}:${termNow}`);
    dropPictures();
    setDrawer(false);
    snap.current = { rows: [], absent: new Set(), approved: new Set(), missed: new Map() };
    photoKids.current = new Set();
    setFlags({});
    setDevAbsent(new Set());
    setMeta(null);
    setFormKey(null);
    setChild(0);
    await reload();
  };

  // The first sheet entered freezes the paper on the server: it can no longer change.
  const frozenSent = useRef(false);
  const freezePaper = () => {
    const id = meta?.paperId;
    if (frozenSent.current || !id) return;
    frozenSent.current = true;
    void pcall(`/api/papers/${encodeURIComponent(id)}/freeze`, "teacher", { method: "POST" }).catch(() => {
      frozenSent.current = false; // try again with the next box
    });
  };

  const setCell = (index: number, value: string) => {
    if (!formKey) return;
    if (value !== "") freezePaper();
    const s = clone();
    ensure(s, child);
    const row = rowAt(s, child);
    row[index] = value;
    s.rows[child] = row;
    s.approved.delete(child); // any change needs approving again
    if (flags[child]?.includes(index)) setFlags({ ...flags, [child]: (flags[child] ?? []).filter((i) => i !== index) });
    commit(s);
  };

  const goTo = (index: number) => {
    setChild(Math.max(0, Math.min(index, Math.max(rollTotal, 1) - 1)));
    setQ(0);
    setPhotoNote("");
  };

  const toggleAbsent = (on: boolean) => {
    if (!formKey) return;
    const s = clone();
    ensure(s, child);
    if (on && hasAnswers(rowAt(s, child)) && !window.confirm(tr("check.absent_confirm"))) return;
    if (on) {
      s.absent.add(child);
      s.missed.delete(child);
      s.rows[child] = emptyRow(items);
      s.approved.delete(child);
      photoKids.current.delete(child);
    } else {
      s.absent.delete(child);
      s.approved.delete(child);
    }
    commit(s);
  };

  // Testing only (DEV_TESTING=1): mark every roll number with nothing entered as absent; unticking undoes those
  // that are still absent and empty.
  const markRestAbsent = (on: boolean) => {
    if (!formKey) return;
    const s = clone();
    if (on) {
      const marked = new Set<number>();
      for (let i = 0; i < rollTotal; i++) {
        if (dataState(setOf(), i) !== "not_entered") continue;
        ensure(s, i);
        s.absent.add(i);
        s.missed.delete(i);
        s.approved.delete(i);
        marked.add(i);
      }
      if (marked.size === 0) return;
      setDevAbsent(marked);
    } else {
      for (const i of devAbsent) if (s.absent.has(i) && !hasAnswers(rowAt(s, i))) s.absent.delete(i);
      setDevAbsent(new Set());
    }
    commit(s);
  };

  const toggleMissed = (concept: string, on: boolean) => {
    if (!formKey) return;
    const s = clone();
    const names = new Set(s.missed.get(child) ?? []);
    if (on) names.add(concept);
    else names.delete(concept);
    s.missed.set(child, names);
    s.approved.delete(child);
    commit(s);
  };

  const showPicture = (roll: number, blob: Blob, sha: string) => {
    setPics((p) => {
      const old = p[roll];
      if (old) {
        URL.revokeObjectURL(old.url);
        picUrls.current.delete(old.url);
      }
      const url = URL.createObjectURL(blob);
      picUrls.current.add(url);
      return { ...p, [roll]: { url, blob, sha } };
    });
  };

  /** Fill a roll from a read (the camera, a folder picture, or a re-read): Entered, not approved. */
  const fillFromRead = (roll: number, res: ReadResult) => {
    if (!formKey) return;
    freezePaper();
    const { row, flagged } = applyReads(res.cells, items);
    const s = clone();
    ensure(s, roll);
    s.rows[roll] = row;
    s.absent.delete(roll);
    s.approved.delete(roll);
    photoKids.current.add(roll);
    showPicture(roll, res.shrunk, res.sha);
    setFlags((f) => ({ ...f, [roll]: flagged }));
    commit(s);
  };

  const failNote = (e: unknown) => {
    const kind = e instanceof SheetError ? e.kind : "other";
    setPhotoNote(kind === "offline" ? "check.photo_offline" : kind === "typing" ? "check.photo_typing" : kind === "bad_photo" ? "check.photo_bad" : kind === "paused" ? "check.folder_paused" : "check.photo_failed");
  };

  // Photo of this child's sheet: the server reads it blind, the boxes fill in, and she checks them.
  const onCamera = async (file: Blob) => {
    if (!formKey) return;
    if (!hasConsent("core")) {
      setPhotoNote("check.photo_need_notice");
      return;
    }
    if (!isOnline()) {
      setPhotoNote("check.photo_offline");
      return;
    }
    if (hasAnswers(rowAt(snap.current, child)) && !window.confirm(tr("check.photo_replace"))) return;
    setReading(true);
    setPhotoNote("");
    try {
      const res = await readPicture(file, formKey);
      fillFromRead(child, res);
      setQ(applyReads(res.cells, items).flagged[0] ?? 0);
      setPhotoNote("check.photo_done");
    } catch (e) {
      failNote(e);
    } finally {
      setReading(false);
    }
  };

  const reread = async () => {
    const pic = pics[child];
    if (!pic || !formKey) return;
    setReading(true);
    try {
      const { readSheetFull } = await import("../lib/sheets");
      const res = await readSheetFull(pic.blob, formKey, { sha256: pic.sha });
      fillFromRead(child, { ...res, shrunk: pic.blob, sha: pic.sha });
      setPhotoNote("check.photo_done");
    } catch (e) {
      failNote(e);
    } finally {
      setReading(false);
    }
  };

  const approve = (i: number) => {
    const s = clone();
    if (dataState(setOf(), i) !== "entered") return;
    if (!pics[i] && !window.confirm(tr("check.approve_nopic"))) return;
    s.approved.add(i);
    commit(s);
    void keepCopy(i);
    goTo(afterApprove({ rows: s.rows, absent: s.absent, approved: s.approved }, i, size));
  };

  // Testing only (DEV_TESTING=1): approve every entered roll at once, without the picture question.
  const approveAll = () => {
    const s = clone();
    const done: number[] = [];
    for (let i = 0; i < rollTotal; i++) {
      if (dataState(setOf(), i) === "entered" && !s.approved.has(i)) {
        s.approved.add(i);
        done.push(i);
      }
    }
    if (done.length === 0) return;
    commit(s);
    done.forEach((i) => void keepCopy(i));
  };

  // Keep this roll's picture for 60 days after approval, if she agreed. The picture stays on the phone either way.
  const keepCopy = async (i: number) => {
    const p = pics[i];
    if (!p || !keepOn || !klass || !hasConsent("keep_sheets")) return;
    try {
      const k = await keepSheet(role, klass.id, checkKey, i + 1, p.blob, p.sha);
      setKept((cur) => ({ ...cur, [i]: k }));
      setKeepNote("");
    } catch {
      setKeepNote(tr("check.keep_failed", { n: i + 1 }));
    }
  };

  const chooseKeep = (on: boolean) => {
    const before = getConsent();
    const base: Choices = { core: true, counts: false, practice_ai: false, share_rehearsal: false, feedback: false, ...(before ?? {}) };
    const after = setConsent({ ...base, core: true, keep_sheets: on });
    void recordOnServer(before, after);
    setAsked(true);
  };

  // The icon opens the picture from memory, or fetches the kept copy (after a reload, or on another day).
  const openSheet = async () => {
    if (drawer) return setDrawer(false);
    if (!pics[child] && kept[child] && klass) {
      try {
        showPicture(child, await fetchKept(role, klass.id, checkKey, child + 1), "");
      } catch {
        setKeepNote(tr("check.keep_missing", { n: child + 1 }));
        return;
      }
    }
    setDrawer(true);
  };

  const deleteCopy = async () => {
    if (!klass) return;
    try {
      await deleteKept(role, klass.id, checkKey, child + 1);
      setKept((cur) => {
        const next = { ...cur };
        delete next[child];
        return next;
      });
      setKeepNote(tr("check.keep_deleted", { n: child + 1 }));
    } catch {
      setKeepNote(tr("check.keep_delete_failed"));
    }
  };

  const finish = async () => {
    if (!formKey) return;
    const gate = finishGate(setOf(), size);
    if (!gate.enabled) return;
    if (!window.confirm(tr("check.finish_confirm", { a: gate.entered, b: gate.absent }))) return;
    await writes.current; // the last write lands before the check is closed
    const cls = klass ?? (await activeClass(false));
    const termNow = await getSetting("term", term);
    const s = snap.current;
    // only approved answers feed the finder; an absent roll has none
    const all = s.rows.map((r, i) => (s.absent.has(i) || !s.approved.has(i) ? emptyRow(items) : r));
    const stages = stagesFor(formKey, all, s.missed);
    const done = await finishCheck(cls.id, termNow, formKey, all, cls.simulated, undefined, stages);
    await db.checks.update(`${cls.id}:${termNow}`, { status: "closed", trackId: meta?.kind === "post" ? trackToEvaluate(history, profiles) : done.track });
    dropPictures();
    setDrawer(false);
    await reload();
    void flushAllowed(isOnline()).then(reload);
    if (onDone) onDone();
    else go("/cards");
  };

  if (!formKey) {
    return (
      <section aria-labelledby="start-title">
        {klass?.simulated ? <SimulatedBanner /> : null}
        <StartCheck className={shownClassName(tr, klass)} term={term} onStart={start} lastCount={history.find((c) => c.expectedChildren)?.expectedChildren ?? null} preferKind={suggestKind(history, profiles, term)} />
      </section>
    );
  }

  // A finished check: what was entered, See results, and Reopen to change it.
  if (check?.status === "closed" && check.formKey === formKey && !reopened) {
    const reopen = async () => {
      if (klass) await db.checks.update(`${klass.id}:${term}`, { status: "entering" });
      setReopened(true);
    };
    return (
      <section aria-labelledby="check-title" data-testid="check-finished">
        <h1 id="check-title">{tr("check.title")}</h1>
        {klass?.simulated ? <SimulatedBanner /> : null}
        <div className="card stack">
          <h2>{tr("check.finished_title")}</h2>
          <p data-testid="check-finished-counts">{tr("check.finished_body", { n: enteredChildren(snap.current.rows).length, a: snap.current.absent.size })}</p>
          <div className="row">
            <button type="button" className="btn btn-primary" onClick={() => (onDone ? onDone() : go("/cards"))} data-testid="check-see-results">
              {tr("check.see_results")}
            </button>
            <button type="button" className="btn btn-secondary" onClick={() => void reopen()} data-testid="check-reopen">
              {tr("check.reopen")}
            </button>
          </div>
          <p className="muted">{tr("check.reopen_note")}</p>
        </div>
      </section>
    );
  }

  const rs = setOf();
  const shownMeta = meta ?? { kind: suggestKind(history, profiles, term), checkDate: today(), expectedChildren: null, confirm: false };
  const label = formatCheckLabel(tr, { id: "", classId: "", term, formKey, children: [], updatedAt: 0, kind: shownMeta.kind, checkDate: shownMeta.checkDate, paperCode: meta?.paperCode ?? null }, shownClassName(tr, klass), lang);
  const row = rowAt(snap.current, child);
  const state = dataState(rs, child);
  const isAbsent = state === "absent";
  const approvedNow = isApproved(rs, child);
  const counts = countRolls(rs, size);
  const gate = finishGate(rs, size);
  const focusNext = (i: number) => inputs.current[Math.min(items - 1, i + 1)]?.focus();
  const mine = snap.current.missed.get(child) ?? new Set<string>();
  const adaptive = new Set((form?.items ?? []).filter((it) => (it as { anchor?: boolean }).anchor === false).map((it) => it.n));
  const concepts = conceptQuestions(form?.items ?? []);
  const and = tr("check.and");
  const moreText = (n: number) => tr("check.n_more", { n });
  const sourceText = photoKids.current.has(child) ? (isRecorded(aiMode) ? tr("ai.recorded") : tr("check.src_ai")) : "";
  const blockedReason = aiOff ? tr("ai.off.photo") : !online ? tr("check.photo_offline") : null;
  const pic = pics[child];
  const nextApprove = nextToApprove(rs, child, size);
  const nextEmpty = nextNotEntered(rs, child, size);
  const noteText = (n: (typeof gate.notes)[number]) => {
    if (n.kind === "none_entered") return tr("check.finish_none");
    if (n.kind === "ready") return tr("check.finish_ready", { n: n.total });
    const list = listRolls(n.rolls, n.more, and, moreText);
    return tr(n.kind === "not_entered" ? "check.finish_not_entered" : "check.finish_not_approved", { rolls: list });
  };

  return (
    <section aria-labelledby="check-title" className={drawer ? "has-drawer" : undefined}>
      <h1 id="check-title">{tr("check.title")}</h1>
      {klass?.simulated ? <SimulatedBanner /> : null}
      <div className="check-header" data-testid="check-header">
        <p className="check-label" data-testid="check-label">
          <strong>{label}</strong>
        </p>
        <p className="muted" data-testid="check-progress">
          {shownMeta.expectedChildren ? tr("check.progress_of", { n: entered, total: shownMeta.expectedChildren }) : tr("check.progress", { n: entered })}
        </p>
        <button type="button" className="chip-btn" onClick={() => void chooseAnother()} data-testid="choose-another">
          {tr("check.another")}
        </button>
        <button type="button" className="chip-btn" onClick={clearEntered} disabled={entered === 0 && snap.current.absent.size === 0} data-testid="clear-entered">
          {tr("check.clear")}
        </button>
        {meta?.paperCode ? (
          <p className="muted" data-testid="check-paper-code">
            {tr("papers.attached", { code: meta.paperCode })}
          </p>
        ) : null}
      </div>

      {keepOn && !asked ? (
        <div className="card stack" data-testid="keep-ask">
          <strong>{tr("check.keep_title", { days: retention })}</strong>
          <p className="muted">{tr("check.keep_why", { days: retention })}</p>
          <div className="row">
            <button type="button" className="btn btn-primary" onClick={() => chooseKeep(true)} data-testid="keep-yes">
              {tr("check.keep_yes")}
            </button>
            <button type="button" className="btn btn-secondary" onClick={() => chooseKeep(false)} data-testid="keep-no">
              {tr("check.keep_no")}
            </button>
          </div>
        </div>
      ) : null}
      {keepNote ? (
        <p role="status" className="muted" data-testid="keep-note">
          {keepNote}
        </p>
      ) : null}
      <p role="status" aria-live="polite" data-testid="roll-counts">
        {tr("check.counts_line", { e: counts.entered, a: counts.approved, x: counts.absent, n: counts.notEntered })}
      </p>
      <h2 data-testid="child-title">{tr("check.child", { n: child + 1 })}</h2>
      <div className="roll-line">
        <label className="field">
          <span>{tr("check.pick")}</span>
          <select value={child} onChange={(e) => goTo(Number(e.target.value))} data-testid="child-select">
            {Array.from({ length: Math.max(rollTotal, 1) }, (_, i) => (
              <option key={i} value={i}>
                {tr(optionKey(rs, i), { n: i + 1 })}
              </option>
            ))}
          </select>
        </label>
        {sourceText ? (
          <span className="muted" data-testid="roll-source">
            {sourceText}
          </span>
        ) : null}
        {pic || kept[child] ? (
          <button
            ref={iconRef}
            type="button"
            className="btn btn-secondary btn-icon sheet-icon-btn"
            onClick={() => void openSheet()}
            aria-expanded={drawer}
            aria-label={tr("check.show_sheet", { n: child + 1 })}
            title={tr("check.show_sheet", { n: child + 1 })}
            data-testid="show-sheet"
          >
            <Icon name="image" />
          </button>
        ) : null}
      </div>
      {!pic && state === "entered" && photoKids.current.has(child) ? (
        <p id="no-pic-reason" className="muted" data-testid="no-pic-reason">
          {tr("check.no_picture_reload")}
        </p>
      ) : !pic ? (
        <p id="no-pic-reason" className="sr">
          {tr("check.no_picture")}
        </p>
      ) : null}
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
          <AddSheets
            formKey={formKey}
            paperCode={meta?.paperCode ?? null}
            size={size}
            blockedReason={blockedReason}
            hasAnswers={(r) => hasAnswers(snap.current.rows[r] ?? []) || snap.current.absent.has(r)}
            onCamera={onCamera}
            onApply={fillFromRead}
            busy={reading}
          />
          <div className="boxes" role="group" aria-label={tr("check.child", { n: child + 1 })}>
            {Array.from({ length: items }, (_, i) => {
              const cell = row[i] ?? "";
              const special = cell === BLANK ? "blank" : cell === UNREADABLE ? "unreadable" : "";
              const flagged = flags[child]?.includes(i) ?? false;
              const n = form?.items[i]?.n ?? i + 1;
              return (
                <div key={i} className={`${i === q ? "box box-on" : "box"}${flagged ? " box-check" : ""}`} data-check={flagged ? "true" : undefined} data-testid={`box-${i + 1}`}>
                  <label className="box-q" htmlFor={`cell-${i}`}>
                    {tr("check.q", { n })}
                    {adaptive.has(n) ? <span className="chip" data-testid={`extra-${i + 1}`}> {tr("check.extra")}</span> : null}
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
                  {flagged ? <span className="box-flag">{tr("check.photo_flag")}</span> : null}
                </div>
              );
            })}
          </div>
          <fieldset className="stack missed-box" data-testid="missed-group">
            <legend>{tr("check.missed_title")}</legend>
            {concepts.map(({ concept, questions }) => (
              <label key={concept} className="check">
                <input type="checkbox" checked={mine.has(concept)} onChange={(e) => toggleMissed(concept, e.target.checked)} data-testid={`missed-${concept}`} />
                <span>{tr(`check.missed_${concept}` as "check.missed_addition", { qs: formatQuestions(questions, and) })}</span>
              </label>
            ))}
          </fieldset>
          <div className="check-actions">
            <button type="button" className="btn btn-primary" onClick={() => approve(child)} disabled={state !== "entered" || approvedNow} data-testid="approve">
              {tr("check.approve")}
            </button>
          </div>
        </>
      )}
      {photoNote ? (
        <p role="status" data-testid="photo-note">
          {tr(photoNote as "check.photo_done")} {photoNote === "check.photo_done" ? <RecordedChip testId="photo-recorded" /> : null}
        </p>
      ) : null}
      <div className="row">
        <button type="button" className="btn btn-secondary" onClick={() => goTo(child - 1)} disabled={child === 0} data-testid="prev-child">
          {tr("check.prev")}
        </button>
        <button type="button" className="btn btn-secondary" onClick={() => goTo(child + 1)} disabled={child + 1 >= Math.max(rollTotal, 1)} data-testid="next-child">
          {tr("check.next")}
        </button>
        <button type="button" className="btn btn-secondary" onClick={() => nextEmpty !== null && goTo(nextEmpty)} disabled={nextEmpty === null} data-testid="next-empty">
          {tr("check.next_empty")}
        </button>
        <button type="button" className="btn btn-secondary" onClick={() => nextApprove !== null && goTo(nextApprove)} disabled={nextApprove === null} aria-describedby={nextApprove === null ? "nothing-to-approve" : undefined} data-testid="next-approve">
          {tr("check.next_approve")}
        </button>
        {devTesting && nextApprove !== null ? (
          <button type="button" className="btn btn-secondary" onClick={approveAll} data-testid="approve-all-dev">
            {tr("check.approve_all_dev")}
          </button>
        ) : null}
      </div>
      {devTesting && (counts.notEntered > 0 || devAbsent.size > 0) ? (
        <label className="check">
          <input type="checkbox" checked={devAbsent.size > 0} onChange={(e) => markRestAbsent(e.target.checked)} data-testid="absent-rest-dev" />
          {tr("check.absent_rest_dev")}
        </label>
      ) : null}
      {nextApprove === null ? (
        <p id="nothing-to-approve" className="muted" data-testid="nothing-to-approve">
          {tr("check.nothing_to_approve")}
        </p>
      ) : null}
      <p className="muted" role="status" data-testid="check-count">
        {message}
      </p>
      <div className="finish-bar" data-testid="finish-bar">
        <div id="finish-note" className="finish-note" data-testid="finish-note">
          {gate.notes.map((n) => (
            <p key={n.kind} className="finish-note" data-testid={`finish-note-${n.kind}`}>
              {noteText(n)}
            </p>
          ))}
        </div>
        <button type="button" className="btn btn-primary" onClick={() => void finish()} disabled={!gate.enabled} aria-describedby="finish-note" data-testid="finish">
          {tr("check.finish")}
        </button>
      </div>
      {drawer ? (
        <SheetDrawer
          roll={child}
          url={pic?.url ?? null}
          source={sourceText}
          canApprove={state === "entered" && !approvedNow}
          showReread={photoKids.current.has(child) && !!pic}
          canReread={!!pic && !blockedReason && !reading}
          rereadReason={blockedReason ?? ""}
          onApprove={() => approve(child)}
          onReread={() => void reread()}
          keptUntil={kept[child] ? new Date(kept[child].delete_after).toLocaleDateString(lang) : null}
          onDeleteCopy={() => void deleteCopy()}
          onClose={() => {
            setDrawer(false);
            iconRef.current?.focus();
          }}
        />
      ) : null}
    </section>
  );
}
