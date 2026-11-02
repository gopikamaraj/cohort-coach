// The v2 component set. Presentation only: no data, no API, no decisions. Every component takes
// its words from the caller (strings come from the shared en/hi/ta files), so nothing here has a
// fixed width or a hard-coded sentence. Styles: styles/components.css; values: styles/tokens.css.
import { useEffect, useId, useRef } from "react";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Icon } from "../components/icons";
import { avatarSvg, lookFromSeed, validateSvg } from "../sprites";

const cx = (...parts: (string | false | null | undefined)[]) => parts.filter(Boolean).join(" ");

/* ---- Button: filled (the one main action), tonal, outlined, text; loading and disabled ---- */
export type ButtonVariant = "filled" | "tonal" | "outlined" | "text" | "danger";
export function Button({
  variant = "filled",
  icon,
  loading = false,
  block = false,
  className,
  children,
  disabled,
  type = "button",
  ...rest
}: { variant?: ButtonVariant; icon?: string; loading?: boolean; block?: boolean } & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button type={type} className={cx("ui-btn", `ui-btn--${variant}`, block && "ui-btn--block", className)} disabled={disabled || loading} aria-busy={loading || undefined} {...rest}>
      {loading ? <span className="ui-spin" aria-hidden="true" /> : icon ? <Icon name={icon} size={20} /> : null}
      <span>{children}</span>
    </button>
  );
}

/* ---- Card ---- */
export function Card({ title, icon, focus = false, children, footer, as: Tag = "section" }: { title?: string; icon?: string; focus?: boolean; children?: ReactNode; footer?: ReactNode; as?: "section" | "article" | "div" }) {
  return (
    <Tag className={cx("ui-card", focus && "ui-card--focus")}>
      {title ? (
        <div className="ui-card__head">
          {icon ? <Icon name={icon} /> : null}
          <h2>{title}</h2>
        </div>
      ) : null}
      {children}
      {footer ? <div className="ui-card__foot">{footer}</div> : null}
    </Tag>
  );
}

/* ---- Chip (a filter or a choice) and StatusPill (a state: icon and word, never colour alone) ---- */
export function Chip({ children, pressed, onClick, icon }: { children: ReactNode; pressed?: boolean; onClick?: () => void; icon?: string }) {
  const body = (
    <>
      {icon ? <Icon name={icon} size={16} /> : null}
      <span>{children}</span>
    </>
  );
  return onClick ? (
    <button type="button" className="ui-chip" aria-pressed={pressed} onClick={onClick}>
      {body}
    </button>
  ) : (
    <span className="ui-chip">{body}</span>
  );
}
export type Tone = "info" | "good" | "warn" | "bad";
const PILL_ICON: Record<Tone, string> = { info: "info", good: "ok", warn: "flag", bad: "close" };
export function StatusPill({ tone = "info", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span className={cx("ui-pill", tone !== "info" && `ui-pill--${tone}`)}>
      <Icon name={PILL_ICON[tone]} size={16} />
      <span>{children}</span>
    </span>
  );
}

/* ---- TextField, Select, Toggle: a visible label always, help and error as text ---- */
export function TextField({ label, help, error, multiline = false, ...rest }: { label: string; help?: string; error?: string; multiline?: boolean } & Record<string, unknown>) {
  const id = useId();
  const describedBy = [help ? `${id}-h` : "", error ? `${id}-e` : ""].filter(Boolean).join(" ") || undefined;
  const common = { id, "aria-describedby": describedBy, "aria-invalid": error ? true : undefined, ...rest };
  return (
    <div className="ui-field">
      <label htmlFor={id}>{label}</label>
      {multiline ? <textarea {...(common as object)} /> : <input {...(common as object)} />}
      {help ? (
        <p className="ui-field__help" id={`${id}-h`}>
          {help}
        </p>
      ) : null}
      {error ? (
        <p className="ui-field__error" id={`${id}-e`} role="alert">
          <Icon name="info" size={16} />
          {error}
        </p>
      ) : null}
    </div>
  );
}
export function SelectField({ label, help, children, ...rest }: { label: string; help?: string; children: ReactNode } & Record<string, unknown>) {
  const id = useId();
  return (
    <div className="ui-field">
      <label htmlFor={id}>{label}</label>
      <select id={id} aria-describedby={help ? `${id}-h` : undefined} {...(rest as object)}>
        {children}
      </select>
      {help ? (
        <p className="ui-field__help" id={`${id}-h`}>
          {help}
        </p>
      ) : null}
    </div>
  );
}
export function Toggle({ label, checked, onChange, disabled }: { label: string; checked: boolean; onChange: (v: boolean) => void; disabled?: boolean }) {
  return (
    <label className="ui-toggle">
      <input type="checkbox" role="switch" checked={checked} disabled={disabled} onChange={(e) => onChange(e.target.checked)} />
      <span className="ui-toggle__track" aria-hidden="true" />
      <span>{label}</span>
    </label>
  );
}

/* ---- Segmented control ---- */
export function Segmented<T extends string>({ label, value, options, onChange }: { label: string; value: T; options: { value: T; label: string }[]; onChange: (v: T) => void }) {
  return (
    <div role="group" aria-label={label} className="ui-seg">
      {options.map((o) => (
        <button key={o.value} type="button" aria-pressed={o.value === value} onClick={() => onChange(o.value)}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

/* ---- ListRow ---- */
export function ListRow({ title, sub, icon, href, onClick, trailing }: { title: string; sub?: string; icon?: string; href?: string; onClick?: () => void; trailing?: ReactNode }) {
  const inner = (
    <>
      {icon ? <Icon name={icon} /> : null}
      <span className="ui-row__text">
        <span className="ui-row__title">{title}</span>
        {sub ? (
          <>
            <br />
            <span className="ui-row__sub">{sub}</span>
          </>
        ) : null}
      </span>
      {trailing ?? (href || onClick ? <Icon name="chevron" size={20} /> : null)}
    </>
  );
  if (href) return <a className="ui-row" href={href}>{inner}</a>;
  if (onClick) return <button type="button" className="ui-row" onClick={onClick}>{inner}</button>;
  return <div className="ui-row">{inner}</div>;
}
export function List({ children }: { children: ReactNode[] }) {
  return (
    <ul className="ui-list">
      {children.map((c, i) => (
        <li key={i}>{c}</li>
      ))}
    </ul>
  );
}

/* ---- BigNumber (the caller passes a count that code computed) and ProgressMeter ---- */
export function BigNumber({ value, label }: { value: string | number; label: string }) {
  return (
    <div className="ui-bignum">
      <span className="ui-bignum__value">{value}</span>
      <span className="ui-bignum__label">{label}</span>
    </div>
  );
}
export function ProgressMeter({ value, max, label }: { value: number; max: number; label: string }) {
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;
  return (
    <div className="ui-meter">
      <div className="ui-meter__track" role="progressbar" aria-valuemin={0} aria-valuemax={max} aria-valuenow={value} aria-label={label}>
        <div className="ui-meter__fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="ui-meter__text">{label}</span>
    </div>
  );
}

/* ---- Callout ---- */
const CALL_ICON = { info: "info", warning: "flag", success: "ok", error: "info" } as const;
export function Callout({ tone = "info", children }: { tone?: keyof typeof CALL_ICON; children: ReactNode }) {
  return (
    <div className={cx("ui-callout", tone !== "info" && `ui-callout--${tone}`)} role={tone === "error" ? "alert" : "note"}>
      <Icon name={CALL_ICON[tone]} size={20} />
      <p>{children}</p>
    </div>
  );
}

/* ---- EmptyState: a small inline picture, a plain line, one next step ---- */
export function EmptyState({ title, text, action }: { title: string; text?: string; action?: ReactNode }) {
  return (
    <div className="ui-empty">
      <svg className="ui-empty__art" viewBox="0 0 96 96" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
        <rect x="14" y="22" width="68" height="52" rx="8" />
        <path d="M14 38h68M30 52h20M30 62h34" />
        <circle cx="70" cy="18" r="6" />
      </svg>
      <h3>{title}</h3>
      {text ? <p>{text}</p> : null}
      {action}
    </div>
  );
}

/* ---- Skeleton: shown while loading, with a name for screen readers ---- */
export function Skeleton({ lines = 3, label }: { lines?: number; label: string }) {
  return (
    <div role="status" aria-label={label} aria-busy="true" style={{ display: "grid", gap: "var(--s2)" }}>
      {Array.from({ length: lines }, (_, i) => (
        <span key={i} className="ui-skel" style={{ width: i === lines - 1 ? "60%" : "100%" }} />
      ))}
    </div>
  );
}

/* ---- Dialog and BottomSheet on the native dialog element ---- */
export function Dialog({ open, onClose, title, children, sheet = false, closeLabel }: { open: boolean; onClose: () => void; title: string; children: ReactNode; sheet?: boolean; closeLabel: string }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);
  return (
    <dialog ref={ref} className={cx("ui-dialog", sheet && "ui-dialog--sheet")} aria-label={title} onClose={onClose} onClick={(e) => e.target === ref.current && onClose()}>
      <div className="ui-dialog__body">
        <h2>{title}</h2>
        {children}
        <Button variant="text" onClick={onClose}>
          {closeLabel}
        </Button>
      </div>
    </dialog>
  );
}
export const BottomSheet = (props: Omit<Parameters<typeof Dialog>[0], "sheet">) => <Dialog {...props} sheet />;

/* ---- Avatar: the code-drawn child sprites; initials only when there is no sprite ---- */
export function Avatar({ seed, label }: { seed: number; label: string }) {
  const svg = avatarSvg(lookFromSeed(seed)); // drawn by our own renderer from approved data
  if (validateSvg(svg).length) return null;
  return (
    <span className="ui-avatar">
      <span className="ui-avatar__img" aria-hidden="true" dangerouslySetInnerHTML={{ __html: svg }} />
      <span className="sr">{label}</span>
    </span>
  );
}

/* ---- AudioPlayer: always with the script as text ---- */
export function AudioPlayer({ src, script, scriptLabel }: { src?: string; script: string; scriptLabel: string }) {
  return (
    <div className="ui-audio">
      {src ? <audio controls preload="none" src={src} /> : null}
      <details>
        <summary>{scriptLabel}</summary>
        <p>{script}</p>
      </details>
    </div>
  );
}

/* ---- BarChart: HTML and CSS bars, the values written out beside them (that is the text alternative) ---- */
export function BarChart({ rows, label, caption }: { rows: { label: string; value: number }[]; label: string; caption?: string }) {
  const max = Math.max(1, ...rows.map((r) => r.value));
  return (
    <figure style={{ margin: 0 }}>
      <div className="ui-bars" role="list" aria-label={label}>
        {rows.map((r) => (
          <div key={r.label} className="ui-bars__row" role="listitem">
            <span>{r.label}</span>
            <span className="ui-bars__track" aria-hidden="true">
              <span className="ui-bars__bar" style={{ display: "block", width: `${(r.value / max) * 100}%` }} />
            </span>
            <span className="ui-bars__val">{r.value}</span>
          </div>
        ))}
      </div>
      {caption ? <figcaption className="muted">{caption}</figcaption> : null}
    </figure>
  );
}

/* ---- StepFlow: icons joined by arrows; the current step is marked in text too ---- */
export function StepFlow({ steps, current }: { steps: { label: string; icon: string }[]; current?: number }) {
  return (
    <ol className="ui-steps">
      {steps.map((s, i) => (
        <li key={s.label}>
          <span className="ui-step" aria-current={i === current ? "step" : undefined}>
            <Icon name={s.icon} size={20} />
            {s.label}
          </span>
          {i < steps.length - 1 ? <Icon name="chevron" size={20} className="icon-arrow" /> : null}
        </li>
      ))}
    </ol>
  );
}

/* ---- Table: stacks into cards on a phone (each cell carries its column name) ---- */
export function Table({ columns, rows, caption }: { columns: string[]; rows: ReactNode[][]; caption: string }) {
  return (
    <table className="ui-table">
      <caption className="sr">{caption}</caption>
      <thead>
        <tr>
          {columns.map((c) => (
            <th key={c} scope="col">
              {c}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            {r.map((cell, j) => (
              <td key={j} data-label={columns[j]}>
                {cell}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/* ---- TopBar: the page title and its tools ---- */
export function TopBar({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="ui-topbar">
      <h1 className="ui-topbar__title">{title}</h1>
      {children ? <div className="ui-topbar__tools">{children}</div> : null}
    </div>
  );
}
export function FormGrid({ children }: { children: ReactNode }) {
  return <div className="ui-form">{children}</div>;
}
export function CardGrid({ children }: { children: ReactNode }) {
  return <div className="ui-grid">{children}</div>;
}
