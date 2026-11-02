// A small (i) button that explains a control. It opens on hover, on keyboard focus and on tap, and
// closes on Escape or a tap elsewhere (a pointer hover shows it with CSS alone); the text is also read by screen readers through aria-describedby.
import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { Icon } from "./icons";

export function InfoTip({ label, text, testId }: { label: string; text: string; testId: string }) {
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLSpanElement>(null);
  const id = useId();
  const tip = useRef<HTMLSpanElement>(null);
  // The tip opens under its label; if that would run past an edge of the screen, slide it back in.
  const fit = () => {
    const t = tip.current;
    if (!t) return;
    t.style.marginLeft = "0px";
    t.style.display = "block"; // hidden tips take no room, so show it unseen just to measure
    t.style.visibility = "hidden";
    const r = t.getBoundingClientRect();
    t.style.display = "";
    t.style.visibility = "";
    const edge = 12;
    const shift = Math.min(0, document.documentElement.clientWidth - edge - r.right) || Math.max(0, edge - r.left);
    t.style.marginLeft = `${shift}px`;
  };
  useLayoutEffect(() => {
    if (open) fit();
  }, [open]);
  useEffect(() => {
    if (!open) return;
    const away = (e: Event) => {
      if (!box.current?.contains(e.target as Node)) setOpen(false);
    };
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("pointerdown", away);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("pointerdown", away);
      document.removeEventListener("keydown", esc);
    };
  }, [open]);
  return (
    <span className="infotip" ref={box} onMouseEnter={fit}>
      <button type="button" className="infotip-btn" aria-label={label} aria-describedby={id} aria-expanded={open} onClick={() => setOpen(!open)} onFocus={(e) => e.currentTarget.matches(":focus-visible") && setOpen(true)} data-testid={`${testId}-info`}>
        <Icon name="info" size={20} />
      </button>
      <span role="tooltip" id={id} ref={tip} className={open ? "infotip-text infotip-on" : "infotip-text"} data-testid={`${testId}-tip`}>
        {text}
      </span>
    </span>
  );
}
