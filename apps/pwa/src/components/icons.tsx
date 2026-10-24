// One small icon set (inline SVG, 24 px grid, 2 px strokes, currentColor). Icons carry meaning that words
// would otherwise repeat; every icon-only control still has an accessible name (aria-label), never just a picture.
import type { ReactNode } from "react";

const PATHS: Record<string, ReactNode> = {
  more: <path d="M5 12h.01M12 12h.01M19 12h.01" strokeWidth="3" />,
  home: <path d="M3 11l9-8 9 8M5 10v10h5v-6h4v6h5V10" />,
  check: (
    <>
      <rect x="5" y="4" width="14" height="17" rx="2" />
      <path d="M9 4h6v3H9zM9 14l2 2 4-4" />
    </>
  ),
  cards: (
    <>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="M7 15v-3M12 15V9M17 15v-5" />
    </>
  ),
  practice: (
    <>
      <circle cx="8" cy="8" r="3" />
      <circle cx="17" cy="9" r="2.5" />
      <path d="M2.5 20c0-3.3 2.5-5.5 5.5-5.5s5.5 2.2 5.5 5.5M14.5 14.8c.8-.3 1.6-.4 2.5-.3 2.5.3 4.5 2.1 4.5 5" />
    </>
  ),
  programme: (
    <>
      <circle cx="6" cy="6" r="2.5" />
      <circle cx="18" cy="18" r="2.5" />
      <path d="M8.5 6H14a3 3 0 010 6h-4a3 3 0 000 6h5.5" />
    </>
  ),
  history: (
    <>
      <path d="M3.5 12a8.5 8.5 0 108.5-8.5A8.6 8.6 0 005.5 6.5L3.5 9" />
      <path d="M3.5 4v5h5M12 8v4.5l3 2" />
    </>
  ),
  profile: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7" />
    </>
  ),
  coach: (
    <>
      <path d="M12 3l9 4.5-9 4.5-9-4.5z" />
      <path d="M7 10.5v4.5c0 1.5 2.2 3 5 3s5-1.5 5-3v-4.5" />
    </>
  ),
  mentor: (
    <>
      <circle cx="12" cy="7" r="3.5" />
      <path d="M5 21c0-4 3-6.5 7-6.5s7 2.5 7 6.5M17.5 3.5l1 1.8 2 .3-1.5 1.4.4 2-1.9-1-1.8 1 .3-2L14.5 5.6l2-.3z" />
    </>
  ),
  admin: (
    <>
      <path d="M12 3l8 3v6c0 4.5-3.2 8-8 9-4.8-1-8-4.5-8-9V6z" />
      <path d="M9 12l2.2 2.2L15.5 10" />
    </>
  ),
  judge: (
    <>
      <path d="M12 4v16M6 20h12M5 8h14" />
      <path d="M5 8l-3 6a3 3 0 006 0zM19 8l-3 6a3 3 0 006 0z" />
    </>
  ),
  speaker: (
    <>
      <path d="M4 9.5v5h3.5L12 18.5v-13L7.5 9.5z" />
      <path d="M15.5 9a4 4 0 010 6M18 6.5a8 8 0 010 11" />
    </>
  ),
  flag: <path d="M6 21V4M6 5h11l-2 4 2 4H6" />,
  camera: (
    <>
      <path d="M4 8h3l1.5-2.5h7L17 8h3v11H4z" />
      <circle cx="12" cy="13.5" r="3.5" />
    </>
  ),
  mic: (
    <>
      <rect x="9" y="3" width="6" height="11" rx="3" />
      <path d="M5.5 11.5a6.5 6.5 0 0013 0M12 18v3" />
    </>
  ),
  send: <path d="M3.5 12l17-8-6 17-3-7z" />,
  bulb: (
    <>
      <path d="M9 18h6M10 21h4" />
      <path d="M12 3a6 6 0 00-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0012 3z" />
    </>
  ),
  trash: <path d="M4 7h16M9 7V4h6v3M6.5 7l1 13h9l1-13M10 11v6M14 11v6" />,
  download: <path d="M12 3v12M7 11l5 5 5-5M4 20h16" />,
  upload: <path d="M12 16V4M7 8l5-5 5 5M4 20h16" />,
  shield: (
    <>
      <path d="M12 3l8 3v6c0 4.5-3.2 8-8 9-4.8-1-8-4.5-8-9V6z" />
      <path d="M12 9v4M12 16v.5" />
    </>
  ),
  lock: (
    <>
      <rect x="5" y="11" width="14" height="10" rx="2" />
      <path d="M8 11V8a4 4 0 018 0v3" />
    </>
  ),
  database: (
    <>
      <ellipse cx="12" cy="6" rx="7" ry="3" />
      <path d="M5 6v6c0 1.7 3.1 3 7 3s7-1.3 7-3V6M5 12v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6" />
    </>
  ),
  users: (
    <>
      <circle cx="9" cy="8" r="3.5" />
      <path d="M2.5 20c0-3.5 2.8-6 6.5-6s6.5 2.5 6.5 6M16 4.5a3.5 3.5 0 010 7M18 14.3c2.2.7 3.5 2.8 3.5 5.7" />
    </>
  ),
  chat: <path d="M4 5h16v11H9l-5 4z" />,
  star: <path d="M12 3.5l2.7 5.5 6 .9-4.4 4.2 1 6-5.3-2.8-5.3 2.8 1-6-4.4-4.2 6-.9z" />,
  plus: <path d="M12 5v14M5 12h14" />,
  minus: <path d="M5 12h14" />,
  play: <path d="M8 5v14l11-7z" />,
  pause: <path d="M8 5v14M16 5v14" strokeWidth="3" />,
  refresh: <path d="M20 5v5h-5M4 19v-5h5M5.5 9A7 7 0 0118 7.5L20 10M18.5 15A7 7 0 016 16.5L4 14" />,
  edit: <path d="M4 20h4L19 9l-4-4L4 16zM13 7l4 4" />,
  globe: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18M12 3c2.5 2.6 3.5 5.6 3.5 9s-1 6.4-3.5 9c-2.5-2.6-3.5-5.6-3.5-9s1-6.4 3.5-9z" />
    </>
  ),
  info: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v6M12 7.5v.5" />
    </>
  ),
  ok: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M8 12.5l2.7 2.7L16 9.5" />
    </>
  ),
  close: <path d="M6 6l12 12M18 6L6 18" />,
  chevron: <path d="M9 5l7 7-7 7" />,
  wifi: (
    <>
      <path d="M3 9a13 13 0 0118 0M6 12.5a8.5 8.5 0 0112 0M9 16a4 4 0 016 0" />
      <circle cx="12" cy="19" r="1" />
    </>
  ),
};

export type IconName = keyof typeof PATHS | string;

export function Icon({ name, size = 24, className = "" }: { name: IconName; size?: number; className?: string }) {
  return (
    <svg
      className={`icon ${className}`.trim()}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {PATHS[name] ?? PATHS["info"]}
    </svg>
  );
}

/** A button with an icon and a visible label, or an icon alone with an accessible name. */
export function IconButton({
  icon,
  label,
  onClick,
  variant = "secondary",
  iconOnly = false,
  disabled,
  testId,
  type = "button",
}: {
  icon: IconName;
  label: string;
  onClick?: () => void;
  variant?: "primary" | "secondary" | "flag" | "danger";
  iconOnly?: boolean;
  disabled?: boolean;
  testId?: string;
  type?: "button" | "submit";
}) {
  return (
    <button
      type={type}
      className={`btn btn-${variant}${iconOnly ? " btn-icon" : " btn-with-icon"}`}
      onClick={onClick}
      disabled={disabled}
      aria-label={iconOnly ? label : undefined}
      title={iconOnly ? label : undefined}
      data-testid={testId}
    >
      <Icon name={icon} />
      {iconOnly ? null : <span>{label}</span>}
    </button>
  );
}
