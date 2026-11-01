// "Keep the app on your phone": a card that opens a sheet with plain steps, in her language, for a
// teacher who has never saved a web app. Where the browser allows it, an Install button shows the
// phone's own install dialog. Installing is optional; nothing depends on it.
import { useEffect, useRef, useState } from "react";
import { promptInstall, useInstall } from "../lib/install";
import { useApp } from "../state";
import { Icon } from "./icons";

const STEPS = ["install.step1", "install.step2", "install.step3", "install.step4", "install.step5"] as const;

export function InstallSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { tr } = useApp();
  const { installed, canPrompt } = useInstall();
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);
  return (
    <dialog
      ref={ref}
      className="sheet"
      aria-labelledby="install-title"
      onClose={onClose}
      onClick={(e) => {
        if (e.target === ref.current) onClose(); // a tap on the dimmed area
      }}
      data-testid="install-dialog"
    >
      {open ? (
        <div className="sheet-body">
          <div className="sheet-head">
            <span className="m-iconwell m-iconwell-lg" aria-hidden="true">
              <Icon name="install" size={28} />
            </span>
            <h2 id="install-title">{tr("install.title")}</h2>
          </div>
          {installed ? (
            <p className="m-note" role="status" data-testid="install-installed">
              <Icon name="ok" size={20} />
              <span>{tr("install.installed")}</span>
            </p>
          ) : null}
          <h3>{tr("install.what_title")}</h3>
          <p>{tr("install.what_body")}</p>
          <h3>{tr("install.steps_title")}</h3>
          <ol className="install-steps" data-testid="install-steps">
            {STEPS.map((k) => (
              <li key={k}>{tr(k)}</li>
            ))}
          </ol>
          <p className="muted">{tr("install.ios")}</p>
          <h3>{tr("install.use_title")}</h3>
          <p>{tr("install.use_body")}</p>
          <p className="muted">{tr("install.optional")}</p>
          <div className="sheet-actions">
            {canPrompt && !installed ? (
              <button
                type="button"
                className="m-btn m-btn-filled"
                onClick={() => void promptInstall().then((accepted) => accepted && onClose())}
                data-testid="install-now"
              >
                <Icon name="download" size={20} /> <span>{tr("install.now")}</span>
              </button>
            ) : null}
            <button type="button" className="m-btn m-btn-tonal" onClick={onClose} data-testid="install-close">
              {tr("install.close")}
            </button>
          </div>
        </div>
      ) : null}
    </dialog>
  );
}

/** The card on the landing page, or a plain row elsewhere. Hidden once the app is installed. */
export function InstallEntry({ variant }: { variant: "card" | "row" }) {
  const { tr } = useApp();
  const { installed } = useInstall();
  const [open, setOpen] = useState(false);
  if (installed && variant === "card") return null;
  return (
    <>
      {variant === "card" ? (
        <div className="l-install" data-testid="install-card">
          <span className="m-iconwell" aria-hidden="true">
            <Icon name="install" size={24} />
          </span>
          <div className="l-install-text">
            <strong>{tr("install.card_title")}</strong>
            <span className="muted">{tr("install.card_hint")}</span>
            <span className="muted">{tr("install.card_note")}</span>
          </div>
          <button type="button" className="m-btn m-btn-tonal" onClick={() => setOpen(true)} data-testid="install-open">
            {tr("install.open")}
          </button>
        </div>
      ) : (
        <button type="button" className="btn btn-secondary btn-with-icon" onClick={() => setOpen(true)} data-testid="install-open">
          <Icon name="install" /> <span>{installed ? tr("install.installed") : tr("install.open")}</span>
        </button>
      )}
      <InstallSheet open={open} onClose={() => setOpen(false)} />
    </>
  );
}
