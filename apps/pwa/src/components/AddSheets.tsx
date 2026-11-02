// Add the sheets: the camera for the selected roll, or a folder of pictures (or many pictures chosen from
// the gallery where a phone cannot choose a folder). Pictures are read three at a time, matched to roll
// numbers (file name, then the header the reader saw, then the teacher chooses), and only then filled in.
// Every picture stays in memory: nothing is written to the phone's storage or kept after Finish.
import { useEffect, useMemo, useRef, useState } from "react";
import { classCodeOf, folderPickerSupported, isPicture, matchPicture, runQueue, sha256Hex, summarise, type Match } from "../lib/folder";
import { downscale, readSheetFull, SheetError, type SheetRead } from "../lib/sheets";
import { Busy } from "./Busy";
import { Icon } from "./icons";
import { useApp } from "../state";

export interface ReadResult extends SheetRead {
  shrunk: Blob;
  sha: string;
}

type Pending = "other_class" | "needs_roll" | "duplicate" | "exists";
interface Item {
  id: number;
  file: File;
  sha: string;
  status: "queued" | "reading" | "read" | "failed" | "applied" | "skipped";
  reason?: string;
  result?: ReadResult;
  match?: Match;
  roll?: number; // zero-based
  pending?: Pending;
  thumb?: string;
}

const REASON: Record<string, "check.photo_offline" | "check.photo_typing" | "check.photo_bad" | "check.photo_failed" | "check.folder_paused" | "check.folder_cancelled"> = {
  offline: "check.photo_offline",
  typing: "check.photo_typing",
  bad_photo: "check.photo_bad",
  paused: "check.folder_paused",
  cancelled: "check.folder_cancelled",
  other: "check.photo_failed",
};

export async function readPicture(file: Blob, formKey: string, signal?: AbortSignal): Promise<ReadResult> {
  const sha = await sha256Hex(file);
  const shrunk = await downscale(file);
  const res = await readSheetFull(shrunk, formKey, { sha256: sha, signal });
  return { ...res, shrunk, sha };
}

export function AddSheets({
  formKey,
  paperCode,
  size,
  blockedReason,
  hasAnswers,
  onCamera,
  onApply,
  busy,
}: {
  formKey: string;
  paperCode: string | null;
  size: number | null;
  blockedReason: string | null; // the AI is off or the phone is offline: both actions wait, typing stays
  hasAnswers: (roll: number) => boolean;
  onCamera: (file: File) => Promise<void>;
  onApply: (roll: number, r: ReadResult) => void;
  busy: boolean;
}) {
  const { tr } = useApp();
  const folderOk = useMemo(() => folderPickerSupported(), []);
  const classCode = classCodeOf(paperCode);
  const [items, setItems] = useState<Item[]>([]);
  const [skippedFiles, setSkippedFiles] = useState(0);
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null);
  const ctrl = useRef<AbortController | null>(null);
  const urls = useRef<Set<string>>(new Set());
  const dirRef = useRef<HTMLInputElement>(null);
  const hasRef = useRef(hasAnswers);
  hasRef.current = hasAnswers; // the reads take a while: always ask the latest

  useEffect(() => {
    const u = urls.current;
    return () => {
      ctrl.current?.abort();
      u.forEach((x) => URL.revokeObjectURL(x));
    };
  }, []);

  // the folder input needs the attribute set as a DOM property in React
  useEffect(() => {
    if (folderOk && dirRef.current) dirRef.current.setAttribute("webkitdirectory", "");
  }, [folderOk]);

  const patch = (id: number, p: Partial<Item>) => setItems((all) => all.map((it) => (it.id === id ? { ...it, ...p } : it)));
  const drop = (it: Item) => {
    if (it.thumb) {
      URL.revokeObjectURL(it.thumb);
      urls.current.delete(it.thumb);
    }
  };

  const total = size ?? 100;
  const clamp = (n: number) => n >= 0 && n < Math.max(total, 1);

  /** After the reads: fill in the clear ones, and set the rest aside with the reason. */
  const settle = (list: Item[]): Item[] => {
    const next = list.map((it) => ({ ...it }));
    const claimed = new Map<number, Item[]>();
    for (const it of next) {
      if (it.status !== "read" || !it.result) continue;
      const m = matchPicture(it.file.name, it.result.header, classCode, size);
      it.match = m;
      if (m.state === "needs_roll") it.pending = "needs_roll";
      else if (m.state === "other_class") {
        it.pending = "other_class";
        it.roll = m.roll - 1;
      } else {
        it.roll = m.roll - 1;
        claimed.set(it.roll, [...(claimed.get(it.roll) ?? []), it]);
      }
    }
    for (const [r, group] of claimed) {
      if (group.length > 1) group.forEach((it) => (it.pending = "duplicate"));
      else if (!clamp(r)) (group[0] as Item).pending = "needs_roll";
      else if (hasRef.current(r)) (group[0] as Item).pending = "exists";
      else {
        const it = group[0] as Item;
        onApply(r, it.result as ReadResult);
        it.status = "applied";
      }
    }
    return next;
  };

  const run = async (files: File[]) => {
    const pictures = files.filter(isPicture);
    setSkippedFiles(files.length - pictures.length);
    const seen = new Set<string>();
    const fresh: Item[] = [];
    let dupes = 0;
    let id = 0;
    for (const file of pictures) {
      const sha = await sha256Hex(file);
      if (seen.has(sha)) {
        dupes += 1; // the same picture twice is read once
        continue;
      }
      seen.add(sha);
      fresh.push({ id: id++, file, sha, status: "queued" });
    }
    setSkippedFiles((n) => n + dupes);
    setItems(fresh);
    ctrl.current = new AbortController();
    const signal = ctrl.current.signal;
    let results = fresh;
    const update = (idx: number, p: Partial<Item>) => {
      results = results.map((it, i) => (i === idx ? { ...it, ...p } : it));
      setItems(results);
    };
    setProgress({ done: 0, total: fresh.length });
    await runQueue(
      fresh,
      async (it, idx) => {
        update(idx, { status: "reading" });
        try {
          const r = await readPicture(it.file, formKey, signal);
          const thumb = URL.createObjectURL(r.shrunk);
          urls.current.add(thumb);
          update(idx, { status: "read", result: r, thumb });
        } catch (e) {
          const kind = e instanceof SheetError ? e.kind : "other";
          if (kind === "paused") ctrl.current?.abort(); // the cost cap: stop and say so
          update(idx, { status: "failed", reason: kind });
        }
      },
      { signal, onProgress: setProgress },
    );
    // pictures never started (Cancel) stay queued; the rest are matched now
    const settled = settle(results);
    setItems(settled);
    setProgress(null);
  };

  const retry = async (it: Item) => {
    patch(it.id, { status: "reading", reason: undefined });
    try {
      const r = await readPicture(it.file, formKey);
      const thumb = URL.createObjectURL(r.shrunk);
      urls.current.add(thumb);
      const one = settle([{ ...it, status: "read" as const, result: r, thumb, reason: undefined }])[0] as Item;
      setItems((all) => all.map((x) => (x.id === it.id ? one : x)));
    } catch (e) {
      patch(it.id, { status: "failed", reason: e instanceof SheetError ? e.kind : "other" });
    }
  };

  const apply = (it: Item, r: number) => {
    onApply(r, it.result as ReadResult);
    drop(it);
    patch(it.id, { status: "applied", pending: undefined, roll: r });
  };
  const choose = (it: Item, r: number) => {
    if (hasRef.current(r)) patch(it.id, { roll: r, pending: "exists" });
    else apply(it, r);
  };
  const skip = (it: Item) => {
    drop(it);
    patch(it.id, { status: "skipped", pending: undefined });
  };
  const useOneOfGroup = (it: Item) => {
    const r = it.roll as number;
    items.filter((x) => x.pending === "duplicate" && x.roll === r && x.id !== it.id).forEach(skip);
    if (hasRef.current(r)) patch(it.id, { pending: "exists" });
    else apply(it, r);
  };
  const exists = items.filter((x) => x.pending === "exists");

  const onFolder = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = [...(e.target.files ?? [])];
    e.target.value = "";
    if (files.length > 0) void run(files);
  };
  const onCam = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (f) void onCamera(f);
  };

  const disabled = !!blockedReason;
  const matches = items.map((it) => it.match).filter((m): m is Match => !!m);
  const sum = summarise(items.length + skippedFiles, skippedFiles, matches);
  const pendingItems = items.filter((x) => x.pending);
  const failed = items.filter((x) => x.status === "failed");
  const reading = progress !== null;

  return (
    <div className="card stack folder-card" data-testid="add-sheets">
      <h2>{tr("check.add_title")}</h2>
      <div className="add-sheets">
        <label className={`btn btn-secondary photo-btn${busy ? " is-busy" : ""}${disabled ? " is-disabled" : ""}`} aria-disabled={disabled || undefined} data-testid="photo-label">
          <Icon name="camera" /> <span>{busy ? tr("check.photo_reading") : tr("check.photo")}</span>
          <input type="file" accept="image/*" capture="environment" className="sr" onChange={onCam} disabled={busy || disabled} data-testid="photo-input" />
        </label>
        <label className={`btn btn-secondary photo-btn${disabled || reading ? " is-disabled" : ""}`} aria-disabled={disabled || reading || undefined} data-testid="folder-label">
          <Icon name="folder" /> <span data-testid="folder-button-text">{folderOk ? tr("check.folder") : tr("check.pictures")}</span>
          {folderOk ? (
            <input ref={dirRef} type="file" multiple accept="image/*" className="sr" onChange={onFolder} disabled={disabled || reading} data-testid="folder-input" />
          ) : (
            <input type="file" multiple accept="image/*" className="sr" onChange={onFolder} disabled={disabled || reading} data-testid="pictures-input" />
          )}
        </label>
      </div>
      {busy && !reading ? <Busy ai testId="photo-busy" text={tr("check.photo_reading")} /> : null}
      {blockedReason ? (
        <p className="muted" role="status" data-testid="add-blocked">
          {blockedReason}
        </p>
      ) : null}
      {!folderOk ? (
        <p className="muted" data-testid="folder-fallback-note">
          {tr("check.folder_fallback")}
        </p>
      ) : null}

      <div aria-live="polite" data-testid="folder-progress">
        {progress ? (
          <>
            <Busy ai testId="folder-busy" text={tr("check.folder_reading", { n: Math.min(progress.done + 1, progress.total), total: progress.total })} />
            <div className="progress-bar" role="progressbar" aria-valuemin={0} aria-valuemax={progress.total} aria-valuenow={progress.done} aria-label={tr("check.folder_reading", { n: Math.min(progress.done + 1, progress.total), total: progress.total })}>
              <span style={{ width: `${progress.total ? (progress.done / progress.total) * 100 : 0}%` }} />
            </div>
            <button type="button" className="btn btn-secondary" onClick={() => ctrl.current?.abort()} data-testid="folder-cancel">
              {tr("check.folder_cancel")}
            </button>
          </>
        ) : null}
      </div>

      {items.length > 0 || skippedFiles > 0 ? (
        <p data-testid="folder-summary" aria-live="polite">
          {tr("check.folder_summary", { found: sum.found - sum.skipped, matched: sum.matched, need: sum.needRoll + sum.otherClass })}
          {sum.skipped > 0 ? ` ${tr("check.folder_skipped", { n: sum.skipped })}` : ""}
        </p>
      ) : null}

      {exists.length > 1 ? (
        <div className="row">
          <button type="button" className="btn btn-secondary" onClick={() => exists.forEach((it) => apply(it, it.roll as number))} data-testid="folder-replace-all">
            {tr("check.replace_all")}
          </button>
          <button type="button" className="btn btn-secondary" onClick={() => exists.forEach(skip)} data-testid="folder-keep-all">
            {tr("check.keep_all")}
          </button>
        </div>
      ) : null}

      <ul className="folder-list">
        {pendingItems.map((it) => (
          <li key={it.id} className="folder-item" data-testid={`folder-pending-${it.pending}`}>
            {it.thumb ? <img src={it.thumb} alt={tr("check.folder_thumb", { name: it.file.name })} /> : null}
            <div className="stack">
              <span>{it.file.name}</span>
              {it.pending === "other_class" ? (
                <>
                  <span role="alert">{tr("check.folder_other_class", { found: it.match?.state === "other_class" ? it.match.found : "", mine: classCode ?? "" })}</span>
                  <span className="row">
                    <button type="button" className="btn btn-secondary" onClick={() => choose(it, it.roll as number)} data-testid="folder-use-anyway">
                      {tr("check.folder_use_anyway", { n: (it.roll as number) + 1 })}
                    </button>
                    <button type="button" className="btn btn-secondary" onClick={() => skip(it)} data-testid="folder-skip">
                      {tr("check.folder_skip")}
                    </button>
                  </span>
                </>
              ) : null}
              {it.pending === "needs_roll" ? (
                <span className="row">
                  <label>
                    <span className="sr">{tr("check.folder_which_roll")}</span>
                    <select defaultValue="" onChange={(e) => e.target.value !== "" && choose(it, Number(e.target.value))} data-testid="folder-roll-choose">
                      <option value="">{tr("check.folder_which_roll")}</option>
                      {Array.from({ length: total }, (_, i) => (
                        <option key={i} value={i}>
                          {tr("check.child", { n: i + 1 })}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button type="button" className="btn btn-secondary" onClick={() => skip(it)} data-testid="folder-skip">
                    {tr("check.folder_skip")}
                  </button>
                </span>
              ) : null}
              {it.pending === "duplicate" ? (
                <>
                  <span role="alert">{tr("check.folder_duplicate", { n: (it.roll as number) + 1 })}</span>
                  <button type="button" className="btn btn-secondary" onClick={() => useOneOfGroup(it)} data-testid="folder-use-this">
                    {tr("check.folder_use_this")}
                  </button>
                </>
              ) : null}
              {it.pending === "exists" ? (
                <>
                  <span>{tr("check.folder_exists", { n: (it.roll as number) + 1 })}</span>
                  <span className="row">
                    <button type="button" className="btn btn-secondary" onClick={() => apply(it, it.roll as number)} data-testid="folder-replace">
                      {tr("check.replace")}
                    </button>
                    <button type="button" className="btn btn-secondary" onClick={() => skip(it)} data-testid="folder-keep">
                      {tr("check.keep_mine")}
                    </button>
                  </span>
                </>
              ) : null}
            </div>
          </li>
        ))}
        {failed.map((it) => (
          <li key={it.id} className="folder-item" data-testid="folder-failed">
            <div className="stack">
              <span>{it.file.name}</span>
              <span role="alert">{tr(REASON[it.reason ?? "other"] ?? "check.photo_failed")}</span>
              {it.reason !== "paused" ? (
                <button type="button" className="btn btn-secondary" onClick={() => void retry(it)} data-testid="folder-retry">
                  {tr("check.folder_retry")}
                </button>
              ) : null}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
