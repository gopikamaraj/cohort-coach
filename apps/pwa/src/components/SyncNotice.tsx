// The notice shown when the app comes back online (or opens) with changes made while it was offline: how many
// will now be saved to her account in the cloud, the progress, then the result, with what could not be saved
// and why, and a Retry. All the sending is in lib/cloudStore.ts; this only shows its state.
import { useEffect, useRef, useSyncExternalStore } from "react";
import { closeSyncNotice, retryFailed, subscribeSync, syncState } from "../lib/cloudStore";
import { useApp } from "../state";

export function SyncNotice() {
  const { tr } = useApp();
  const s = useSyncExternalStore(subscribeSync, syncState, syncState);
  const ref = useRef<HTMLDialogElement>(null);
  const open = s.phase !== "idle";
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);
  const allSaved = s.phase === "done" && s.failed.length === 0;
  useEffect(() => {
    if (!allSaved || s.conflicts > 0) return; // a clean result closes itself; one that needs reading stays until she closes it
    const t = setTimeout(closeSyncNotice, 3000);
    return () => clearTimeout(t);
  }, [allSaved, s.conflicts]);
  return (
    <dialog ref={ref} className="sheet" aria-labelledby="sync-title" onCancel={(e) => (s.phase === "syncing" ? e.preventDefault() : closeSyncNotice())} data-testid="sync-notice">
      {open ? (
        <div className="sheet-body stack">
          <h2 id="sync-title">{tr("sync.title")}</h2>
          <p data-testid="sync-body">{tr("sync.body", { n: s.total })}</p>
          {s.phase === "syncing" ? (
            <>
              <progress max={s.total} value={s.sent + s.failed.length} aria-label={tr("sync.progress", { done: s.sent + s.failed.length, total: s.total })} data-testid="sync-progress" />
              <p role="status">{tr("sync.progress", { done: s.sent + s.failed.length, total: s.total })}</p>
            </>
          ) : null}
          {allSaved ? (
            <p role="status" data-testid="sync-saved">
              {tr("sync.saved", { n: s.sent })}
            </p>
          ) : null}
          {s.phase === "done" && s.failed.length > 0 ? (
            <div role="alert" data-testid="sync-failed">
              <p>{tr("sync.not_saved", { n: s.failed.length })}</p>
              <ul>
                {s.failed.map((f, i) => (
                  <li key={`${f.what}-${i}`}>{tr("sync.failed_row", { what: f.what, reason: f.reason })}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {s.phase === "done" && s.conflicts > 0 ? <p data-testid="sync-conflicts">{tr("sync.conflicts_note", { n: s.conflicts })}</p> : null}
          {s.phase === "done" ? (
            <div className="row">
              {s.failed.length > 0 ? (
                <button type="button" className="btn btn-primary" onClick={() => void retryFailed()} data-testid="sync-retry">
                  {tr("sync.retry")}
                </button>
              ) : null}
              <button type="button" className={s.failed.length > 0 ? "btn btn-secondary" : "btn btn-primary"} onClick={closeSyncNotice} data-testid="sync-close">
                {tr("sync.close")}
              </button>
            </div>
          ) : null}
        </div>
      ) : null}
    </dialog>
  );
}
