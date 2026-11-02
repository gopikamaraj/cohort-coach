// The picture of the selected roll's sheet, beside the boxes. It is not a dialog: the page stays visible
// and editable, so she can compare the picture with what the AI read. Under 900 px it is a bottom drawer
// 40% of the height; at 900 px and above a side drawer 40% of the width. The picture is held in memory
// by the caller and is never saved.
import { useEffect, useRef, useState } from "react";
import { Icon, IconButton } from "./icons";
import { useApp } from "../state";

export function SheetDrawer({
  roll,
  url,
  source,
  canApprove,
  showReread,
  canReread,
  rereadReason,
  onApprove,
  onReread,
  keptUntil,
  onDeleteCopy,
  onClose,
}: {
  roll: number;
  url: string | null;
  source: string;
  canApprove: boolean;
  showReread: boolean;
  canReread: boolean;
  rereadReason: string;
  onApprove: () => void;
  onReread: () => void;
  keptUntil: string | null;
  onDeleteCopy: () => void;
  onClose: () => void;
}) {
  const { tr } = useApp();
  const [zoom, setZoom] = useState(1);
  const [turn, setTurn] = useState(0);
  const [fit, setFit] = useState(true);
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    setZoom(1);
    setTurn(0);
    setFit(true);
  }, [url]);
  useEffect(() => {
    ref.current?.focus();
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [onClose]);
  return (
    <aside ref={ref} tabIndex={-1} className="sheet-drawer" role="complementary" aria-labelledby="sheet-drawer-title" data-testid="sheet-drawer">
      <div className="sheet-drawer-bar">
        <h2 id="sheet-drawer-title">{tr("check.drawer_title", { n: roll + 1 })}</h2>
        <span className="muted" data-testid="drawer-source">
          {source}
        </span>
        <IconButton icon="close" iconOnly label={tr("check.preview_close")} onClick={onClose} testId="drawer-close" />
      </div>
      <div className="sheet-drawer-tools" role="toolbar" aria-label={tr("check.drawer_tools")}>
        <IconButton icon="plus" iconOnly label={tr("check.drawer_zoom_in")} onClick={() => { setFit(false); setZoom((z) => Math.min(4, z + 0.5)); }} testId="drawer-zoom-in" />
        <IconButton icon="minus" iconOnly label={tr("check.drawer_zoom_out")} onClick={() => { setFit(false); setZoom((z) => Math.max(0.5, z - 0.5)); }} testId="drawer-zoom-out" />
        <IconButton icon="rotate" iconOnly label={tr("check.drawer_rotate")} onClick={() => setTurn((t) => (t + 90) % 360)} testId="drawer-rotate" />
        <button type="button" className="btn btn-secondary" onClick={() => { setFit(true); setZoom(1); }} data-testid="drawer-fit">
          <Icon name="image" /> <span>{tr("check.drawer_fit")}</span>
        </button>
      </div>
      <div className="sheet-drawer-body" tabIndex={0} role="group" aria-label={tr("check.drawer_alt", { n: roll + 1 })}>
        {url ? (
          <img src={url} alt={tr("check.drawer_alt", { n: roll + 1 })} data-testid="drawer-image" style={{ width: fit ? "100%" : `${zoom * 100}%`, transform: `rotate(${turn}deg)` }} />
        ) : (
          <p className="muted" data-testid="drawer-none">
            {tr("check.no_picture")}
          </p>
        )}
      </div>
      <div className="sheet-drawer-actions">
        <button type="button" className="btn btn-primary" onClick={onApprove} disabled={!canApprove} data-testid="drawer-approve">
          {tr("check.approve")}
        </button>
        {showReread ? (
          <button type="button" className="btn btn-secondary" onClick={onReread} disabled={!canReread} aria-describedby={rereadReason ? "reread-reason" : undefined} data-testid="drawer-reread">
            {tr("check.reread")}
          </button>
        ) : null}
        <button type="button" className="btn btn-secondary" onClick={onClose} data-testid="drawer-close-text">
          {tr("common.close")}
        </button>
      </div>
      {keptUntil ? (
        <p className="muted" data-testid="kept-until">
          {tr("check.kept_until", { date: keptUntil })}{" "}
          <button type="button" className="chip-btn" onClick={onDeleteCopy} data-testid="kept-delete">
            {tr("check.keep_delete")}
          </button>
        </p>
      ) : null}
      {showReread && rereadReason ? (
        <p id="reread-reason" className="muted" data-testid="reread-reason">
          {rereadReason}
        </p>
      ) : null}
    </aside>
  );
}
