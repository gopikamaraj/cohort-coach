// Pieces of the Practice Class screen: the five children (original SVG figures: plain shapes,
// no gender, religion or caste markers), the materials tray, the judge-only layers panel and the
// feedback card.
import type { ReactNode } from "react";
import type { FeedbackCard, Layers, PracticeChild } from "../lib/practice";
import { useApp } from "../state";

// Five figures that differ by hair and shirt only; nothing says who they "are".
const SHIRTS = ["#1b4f9c", "#1d6b4f", "#9a6700", "#6b3fa0", "#a33b2e"];

function Figure({ index, speaking }: { index: number; speaking: boolean }) {
  const hair = index % 5;
  return (
    <svg viewBox="0 0 64 72" width="56" height="63" aria-hidden="true" className={speaking ? "figure figure-on" : "figure"}>
      <rect x="14" y="40" width="36" height="30" rx="4" fill={SHIRTS[index % SHIRTS.length]} />
      <circle cx="32" cy="26" r="15" fill="#e6c3a0" stroke="#14201f" strokeWidth="1.5" />
      {hair === 0 ? <path d="M17 24c0-12 30-12 30 0c-6-5-24-5-30 0z" fill="#14201f" /> : null}
      {hair === 1 ? <path d="M17 26l4-16l6 9l5-12l5 12l6-9l4 16c-8-6-22-6-30 0z" fill="#14201f" /> : null}
      {hair === 2 ? (
        <>
          <path d="M17 25c0-13 30-13 30 0c-8-6-22-6-30 0z" fill="#14201f" />
          <circle cx="32" cy="8" r="6" fill="#14201f" />
        </>
      ) : null}
      {hair === 3 ? <path d="M17 28c-2-18 28-20 30-4c-8-6-18-4-24 0c-2 2-4 4-6 4z" fill="#14201f" /> : null}
      {hair === 4 ? <path d="M17 22c4-10 26-10 30 0l-3 4c-7-5-17-5-24 0z" fill="#14201f" /> : null}
      <circle cx="26" cy="27" r="1.8" fill="#14201f" />
      <circle cx="38" cy="27" r="1.8" fill="#14201f" />
      <path d={speaking ? "M26 34q6 6 12 0z" : "M27 34q5 3 10 0"} fill={speaking ? "#14201f" : "none"} stroke="#14201f" strokeWidth="1.5" />
    </svg>
  );
}

export function ChildrenRow({ children, speaker }: { children: PracticeChild[]; speaker: string | null }) {
  const { tr } = useApp();
  return (
    <ul className="kids" aria-label={tr("practice.children")}>
      {children.map((c, i) => (
        <li key={c.name} className={speaker === c.name ? "kid kid-on" : "kid"} data-testid={`kid-${i}`} aria-current={speaker === c.name ? "true" : undefined}>
          <Figure index={i} speaking={speaker === c.name} />
          <span className="kid-name">{c.name}</span>
          {c.shy ? <span className="kid-shy">{tr("practice.shy")}</span> : null}
        </li>
      ))}
    </ul>
  );
}

/** Pictures for the materials tray. They are SVG and drawn here: no image files. */
function MaterialArt({ kind }: { kind: string }) {
  if (kind === "bundles") {
    return (
      <svg viewBox="0 0 48 32" width="48" height="32" aria-hidden="true">
        {Array.from({ length: 10 }, (_, i) => (
          <rect key={i} x={4 + i * 4} y="4" width="3" height="24" fill="#e8b93c" stroke="#14201f" strokeWidth="0.8" />
        ))}
        <rect x="2" y="13" width="44" height="6" fill="#fbfcfd" stroke="#14201f" strokeWidth="1" />
      </svg>
    );
  }
  if (kind === "sticks") {
    return (
      <svg viewBox="0 0 48 32" width="48" height="32" aria-hidden="true">
        <rect x="6" y="8" width="3" height="20" fill="#e8b93c" stroke="#14201f" strokeWidth="0.8" transform="rotate(-12 7 18)" />
        <rect x="18" y="6" width="3" height="20" fill="#e8b93c" stroke="#14201f" strokeWidth="0.8" />
        <rect x="30" y="8" width="3" height="20" fill="#e8b93c" stroke="#14201f" strokeWidth="0.8" transform="rotate(14 31 18)" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 48 32" width="48" height="32" aria-hidden="true">
      <rect x="4" y="4" width="40" height="24" fill="#fbfcfd" stroke="#14201f" strokeWidth="1" />
      <line x1="24" y1="4" x2="24" y2="28" stroke="#14201f" strokeWidth="1" />
      <line x1="4" y1="12" x2="44" y2="12" stroke="#14201f" strokeWidth="1" />
    </svg>
  );
}

export function Materials({ items, disabled, onTap }: { items: string[]; disabled: boolean; onTap: (material: string) => void }) {
  const { tr } = useApp();
  const names: Record<string, string> = { bundles: tr("practice.bundles"), sticks: tr("practice.sticks"), chart: tr("practice.chart") };
  return (
    <div className="tray" role="group" aria-label={tr("practice.materials")}>
      {items.map((m) => (
        <button key={m} type="button" className="tool" disabled={disabled} onClick={() => onTap(m)} data-testid={`tap-${m}`}>
          <MaterialArt kind={m} />
          <span>{names[m] ?? m}</span>
        </button>
      ))}
    </div>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="layer">
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

/** Judge mode: the five layers of one turn, straight from the API's `layers` trace. */
export function LayersPanel({ layers }: { layers: Layers }) {
  const { tr } = useApp();
  const { input, processing: p, guardrails: g, evaluation: e, output: o } = layers;
  const eng = p.engine;
  const failed = g.validators.filter((v) => !v.ok);
  return (
    <div className="layers" data-testid="layers-panel">
      <p className="muted">{tr("layers.judge_only")}</p>
      <dl>
        <Row label={tr("layers.input")}>
          <span data-testid="layer-input">{input.teacher_text ?? `[${input.material}]`}</span>
        </Row>
        <Row label={tr("layers.processing")}>
          <span data-testid="layer-label">
            {p.label.move_id}
            {p.label.confidence !== undefined ? ` (${p.label.confidence})` : ""}
            {p.label.forced ? ` · ${p.label.forced}` : ""}
          </span>
          <br />
          <span data-testid="layer-engine">
            {eng.speaker ?? "–"} · {eng.intent}
            {eng.answer !== null ? ` · ${eng.answer}${eng.correct === false ? ` (${eng.error_code})` : ""}` : ""}
          </span>
          {Object.keys(eng.strength_after).length > 0 ? (
            <>
              <br />
              <span>{Object.entries(eng.strength_after).map(([n, v]) => `${n} ${eng.strength_before[n] ?? "?"} → ${v}`).join(", ")}</span>
            </>
          ) : null}
        </Row>
        <Row label={tr("layers.guardrails")}>
          <span data-testid="layer-guardrails">
            {g.validators.length - failed.length}/{g.validators.length} ✓
            {g.checker ? ` · ${g.checker.passed ? "pass" : g.checker.failed_items.join(",")}` : ""}
            {g.retries ? ` · retries ${g.retries}` : ""}
            {g.fallback_used ? ` · ${g.fallback_used}` : ""}
          </span>
        </Row>
        <Row label={tr("layers.evaluation")}>
          <span data-testid="layer-eval">
            {e.latency_ms} ms · {e.tokens.in}/{e.tokens.out} tok · cache {e.tokens.cache_read} · ${e.cost_usd.toFixed(4)}
            {e.call_ms ? ` · label ${e.call_ms.label ?? "–"} ms · child line ${e.call_ms.child ?? "–"} ms · check ${e.call_ms.check ?? "–"} ms` : ""}
            {e.stages ? ` · speech-to-text ${e.stages.stt_ms} ms · voice wait ${e.stages.tts_wait_ms} ms` : ""}
          </span>
        </Row>
        <Row label={tr("layers.output")}>
          <span data-testid="layer-output">
            {o.source} · {o.badge}
          </span>
        </Row>
      </dl>
    </div>
  );
}

function highlight(quote: string): ReactNode {
  return <mark>{quote}</mark>;
}

/** The private feedback card: strengths and one thing to try, her own words highlighted. */
export function FeedbackView({
  card,
  rating,
  onRate,
  onFlag,
  flagged,
}: {
  card: FeedbackCard;
  rating: Record<string, "up" | "down">;
  onRate: (id: string, value: "up" | "down") => void;
  onFlag: () => void;
  flagged: boolean;
}) {
  const { tr } = useApp();
  const Thumbs = ({ id }: { id: string }) => (
    <div className="row">
      <button type="button" className="btn btn-secondary" aria-pressed={rating[id] === "up"} onClick={() => onRate(id, "up")}>
        👍 {tr("practice.helpful")}
      </button>
      <button type="button" className="btn btn-secondary" aria-pressed={rating[id] === "down"} onClick={() => onRate(id, "down")}>
        👎 {tr("practice.not_helpful")}
      </button>
    </div>
  );
  return (
    <section className="feedback" aria-labelledby="fb-title" data-testid="feedback">
      <h2 id="fb-title">{tr("practice.feedback")}</h2>
      <p className="muted">
        {tr("practice.private")} {card.badge !== "none" ? <strong data-testid="fb-badge">{tr("practice.checked")}</strong> : null}
      </p>
      <h3>{tr("practice.strengths")}</h3>
      <ul className="plain">
        {card.strengths.map((s, i) => (
          <li key={s.point} className="card" data-testid={`strength-${i}`}>
            <p>{s.comment}</p>
            <p className="muted">
              {tr("practice.you_said")}: {highlight(s.quote)}
            </p>
            <Thumbs id={s.point} />
          </li>
        ))}
      </ul>
      <h3>{tr("practice.try")}</h3>
      <div className="card" data-testid="try-next">
        <p>{card.try_next.suggestion}</p>
        {card.try_next.quote ? (
          <p className="muted">
            {tr("practice.you_said")}: {highlight(card.try_next.quote)}
          </p>
        ) : null}
        <Thumbs id={`try:${card.try_next.point}`} />
      </div>
      {card.note ? <p className="note">{card.note}</p> : null}
      {Object.keys(rating).length > 0 ? <p role="status">{tr("practice.thanks")}</p> : null}
      <button type="button" className="btn btn-flag" onClick={onFlag} disabled={flagged}>
        {tr("cards.flag")}
      </button>
      {flagged ? <p role="status">{tr("cards.flagged")}</p> : null}
    </section>
  );
}
