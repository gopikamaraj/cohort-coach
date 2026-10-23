// Small shared pieces: the simulated banner, the status line, and tally bundles.
import type { ReactNode } from "react";
import { useApp } from "../state";

/** Shown whenever synthetic data is on screen. */
export function SimulatedBanner() {
  const { tr } = useApp();
  return (
    <p className="banner" role="note">
      {tr("banner.simulated")}
    </p>
  );
}

/** Online, offline and waiting-to-send: an icon and a word, never colour alone. */
export function StatusLine() {
  const { tr, online, forcedOffline, pending } = useApp();
  const text = !online
    ? tr(forcedOffline ? "status.offline_forced" : "status.offline")
    : pending > 0
      ? tr("status.waiting", { n: pending })
      : tr("status.online");
  return (
    <p className={online ? "status" : "status status-off"} role="status" data-testid="status">
      <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
        {online ? <circle cx="7" cy="7" r="5" fill="currentColor" /> : <rect x="2" y="2" width="10" height="10" fill="none" stroke="currentColor" strokeWidth="2" />}
      </svg>
      <span>{text}</span>
    </p>
  );
}

/**
 * The count as sticks: one stroke per child, grouped in tens and tied, the children who show
 * the error filled. Words carry the same count (this drawing has a text alternative).
 */
export function Sticks({ count, total, label }: { count: number; total: number; label: string }) {
  const stickW = 5;
  const gap = 4;
  const groupGap = 12;
  const h = 26;
  const groups = Math.ceil(total / 10);
  let x = 2;
  const marks: ReactNode[] = [];
  for (let g = 0; g < groups; g++) {
    const inGroup = Math.min(10, total - g * 10);
    const startX = x;
    for (let i = 0; i < inGroup; i++) {
      const filled = g * 10 + i < count;
      marks.push(
        <rect
          key={`${g}-${i}`}
          x={x}
          y={4}
          width={stickW}
          height={h - 8}
          fill={filled ? "var(--stick)" : "none"}
          stroke="var(--ink)"
          strokeWidth="1"
        />,
      );
      x += stickW + gap;
    }
    // the tie around a full bundle of ten
    if (inGroup === 10) marks.push(<rect key={`t${g}`} x={startX - 2} y={h / 2 - 3} width={x - gap - startX + 4} height="6" fill="var(--paper)" stroke="var(--ink)" strokeWidth="1" />);
    x += groupGap - gap;
  }
  return (
    <svg className="sticks" width={x} height={h} viewBox={`0 0 ${x} ${h}`} role="img" aria-label={label}>
      {marks}
    </svg>
  );
}
