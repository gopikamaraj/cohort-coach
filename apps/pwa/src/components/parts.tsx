// Small shared pieces: the simulated banner, the status line, and tally bundles.
import type { ReactNode } from "react";
import { useApp } from "../state";
import { useLinkSpeed } from "../lib/net";
import { useConsent } from "../lib/useConsent";
import { countsOn } from "../lib/consent";
import { href } from "../lib/router";
import { isAiOff, isRecorded, useAiMode } from "../lib/aiMode";
import { Icon } from "./icons";
import { isPilotUser } from "../lib/pilot";

/** In the header when the server's AI is not live: "AI: recorded answers" or "AI: off". */
export function AiModeBadge() {
  const { tr } = useApp();
  const mode = useAiMode();
  if (!isRecorded(mode) && !isAiOff(mode) && mode !== "stub") return null;
  const key = isRecorded(mode) ? "ai.mode.recorded" : isAiOff(mode) ? "ai.mode.off" : "ai.mode.stub";
  return (
    <p className={isAiOff(mode) ? "status status-off ai-badge" : "status ai-badge"} title={tr(`${key}_tip` as "ai.mode.recorded_tip")} data-testid="ai-mode-badge" data-mode={mode}>
      <span className="status-word">{tr(key as "ai.mode.recorded")}</span>
    </p>
  );
}

/** Next to any AI answer on screen when the server replays recordings: "Recorded AI answer". */
export function RecordedChip({ testId }: { testId?: string }) {
  const { tr } = useApp();
  const mode = useAiMode();
  if (!isRecorded(mode)) return null;
  return (
    <span className="chip" data-testid={testId ?? "recorded-chip"}>
      {tr("ai.recorded")}
    </span>
  );
}

/** One line saying an AI feature is off and what still works (shown only when the AI is off). */
export function AiOffNote({ text, testId }: { text: string; testId?: string }) {
  const mode = useAiMode();
  if (!isAiOff(mode)) return null;
  return (
    <p className="banner banner-warn" role="status" data-testid={testId ?? "ai-off-note"}>
      {text}
    </p>
  );
}

/** Shown whenever synthetic data is on screen. */
export function SimulatedBanner() {
  const { tr } = useApp();
  return (
    <p className="banner" role="note">
      {tr("banner.simulated")}
    </p>
  );
}

/** Shown on a pilot class's pages (nickname 3A Math or 3B Math) unless the class itself is simulated. */
export function PilotClassBanner() {
  const { tr, klass } = useApp();
  if (!isPilotUser() || klass?.simulated) return null;
  return (
    <p className="chip chip-negative" role="note" data-testid="pilot-class-banner">
      {tr("banner.pilot")}
    </p>
  );
}

/**
 * Online, offline and waiting-to-send: an icon and a word, never colour alone. When the phone's
 * browser can estimate the signal, its word and download speed follow (an estimate; no upload).
 */
export function StatusLine() {
  const { tr, online, forcedOffline, pending } = useApp();
  const link = useLinkSpeed();
  const consent = useConsent();
  // Online with a result waiting and nothing sent: class counts leave only when she has agreed to share
  // them, so say that instead of "waiting" (it would wait for ever).
  const held = online && pending > 0 && !countsOn(consent);
  const text = !online
    ? tr(forcedOffline ? "status.offline_forced" : "status.offline")
    : held
      ? tr("status.held", { n: pending })
      : pending > 0
        ? tr("status.waiting", { n: pending })
        : tr("status.online");
  const icon = !online ? "cloudoff" : pending > 0 ? "upload" : "cloud";
  const showLink = online && link !== null;
  return (
    <p className={`${online ? "status" : "status status-off"}${showLink ? " status-has-link" : ""}`} role="status" data-testid="status" title={showLink ? tr("status.speed_note") : undefined}>
      <Icon name={icon} size={18} />
      <span className="status-word">{held ? <a href={href("/profile")} data-testid="status-held">{text}</a> : text}</span>
      {showLink ? (
        <span className="status-link" data-testid="status-speed">
          <Icon name="signal" size={16} />
          <span>
            <span className="status-word">{tr(`status.signal_${link.signal}` as "status.signal_good")} · </span>
            {tr("status.mbps", { n: link.mbps })}
          </span>
        </span>
      ) : null}
    </p>
  );
}

/** Says what still works with no signal, in her language, under the header. */
export function OfflineNote() {
  const { tr, online } = useApp();
  if (online) return null;
  return (
    <p className="offline-note" role="note" data-testid="offline-note">
      <Icon name="info" size={20} />
      <span>{tr("status.offline_note")}</span>
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
