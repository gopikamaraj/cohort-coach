// Pieces of the Practice Class screen: the five children (original SVG figures: plain shapes,
// no gender, religion or caste markers), the materials tray, the judge-only layers panel and the
// feedback card.
import type { ReactNode } from "react";
import type { Key } from "../i18n";
import type { FeedbackCard, Layers, PracticeChild } from "../lib/practice";
import { useApp } from "../state";
import { avatarSvg, personaLook, seatRow } from "../sprites";
import { loadItem, palette } from "../sprites/data";
import { compileItem } from "../sprites/grammar";

/** A child's face: drawn from her persona and the expression the server chose for this turn. */
function Face({ persona, expression, speaking }: { persona: string | null; expression: string; speaking: boolean }) {
  if (!persona) return null;
  const svg = avatarSvg(personaLook(persona).look, expression, "closed");
  return <div className={speaking ? "sprite figure sprite-speaking" : "sprite figure"} aria-hidden="true" dangerouslySetInnerHTML={{ __html: svg }} />;
}

export const EXPRESSIONS = ["confused", "distracted", "got_it", "neutral", "shy", "thinking", "wrong_answer"] as const;

/** How a child looks right now, in words, under her name. The face comes from the server's table.
 * Every child who spoke this turn is highlighted; the first speaker is the current one. */
export function ChildrenRow({ children, speakers, faces }: { children: PracticeChild[]; speakers: string[]; faces: Record<string, string> }) {
  const { tr } = useApp();
  return (
    <ul className="kids" aria-label={tr("practice.children")}>
      {children.map((c, i) => {
        const expression = faces[c.name] ?? c.expression;
        const label = (EXPRESSIONS as readonly string[]).includes(expression) ? tr(`practice.expr.${expression}` as Key) : "";
        const on = speakers.includes(c.name);
        return (
          <li key={c.name} className={on ? "kid kid-on" : "kid"} data-testid={`kid-${i}`} data-speaking={on ? "true" : undefined} aria-current={speakers[0] === c.name ? "true" : undefined}>
            <Face persona={c.persona} expression={expression} speaking={on} />
            <span className="kid-name">{c.name}</span>
            {label ? (
              <span className={on ? "kid-mood kid-mood-on" : "kid-mood"} data-testid={`kid-mood-${i}`} data-expression={expression}>
                {label}
              </span>
            ) : null}
            {c.shy ? <span className="kid-shy" title={tr("practice.shy")}>{tr("practice.shy")}</span> : null}
          </li>
        );
      })}
    </ul>
  );
}

/** The board: the problem the engine posed, with the first number drawn as tens and ones. Counts come
 * from this function, never from a model. */
export function BlockBoard({ a, b, kind }: { a: number; b: number; kind: string }) {
  const { tr } = useApp();
  const tens = Math.floor(a / 10);
  const ones = a % 10;
  const sign = kind.startsWith("add") ? "+" : "−";
  return (
    <section className="pcx-card" aria-labelledby="pcx-board" data-testid="board">
      <div className="pcx-boardhead">
        <h2 id="pcx-board">{tr("practice.board")}</h2>
        <span className="pcx-pill">{tr("practice.blocks")}</span>
      </div>
      <p className="pcx-sum" data-testid="board-sum">{`${a} ${sign} ${b} = ?`}</p>
      <div className="pcx-mat">
        <div className="pcx-place">
          <h3>{tr("practice.tens_n", { n: tens })}</h3>
          <div className="pcx-pieces" role="img" aria-label={tr("practice.tens_n", { n: tens })}>
            {Array.from({ length: tens }, (_, i) => (
              <i key={i} className="pcx-rod" />
            ))}
          </div>
        </div>
        <div className="pcx-place">
          <h3>{tr("practice.ones_n", { n: ones })}</h3>
          <div className="pcx-pieces" role="img" aria-label={tr("practice.ones_n", { n: ones })}>
            {Array.from({ length: ones }, (_, i) => (
              <i key={i} className="pcx-unit" />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

export type Section = "class" | "materials" | "goal" | "judge";

/** Sections of a running rehearsal, one at a time, so the phone never scrolls past the children. */
export function SectionTabs({ section, onSection, judge }: { section: Section; onSection: (s: Section) => void; judge: boolean }) {
  const { tr } = useApp();
  const all: Section[] = judge ? ["class", "materials", "goal", "judge"] : ["class", "materials", "goal"];
  const label: Record<Section, string> = { class: tr("practice.sec_class"), materials: tr("practice.materials"), goal: tr("practice.sec_goal"), judge: tr("practice.sec_judge") };
  return (
    <div className="sections" role="tablist" aria-label={tr("practice.sections")}>
      {all.map((s) => (
        <button
          key={s}
          type="button"
          role="tab"
          id={`sec-${s}`}
          aria-selected={section === s}
          aria-controls={`panel-${s}`}
          className={section === s ? "section-tab section-on" : "section-tab"}
          onClick={() => onSection(s)}
          data-testid={`sec-${s}`}
        >
          {label[s]}
        </button>
      ))}
    </div>
  );
}

/** The five children's seats on one strip (Watch and the AI-layers views). */
export function SeatStrip({ children }: { children: { persona?: string | null; expression?: string; speaking?: boolean }[] }) {
  const { tr } = useApp();
  const seats = children.flatMap((c) => (c.persona ? [{ look: personaLook(c.persona).look, expression: c.expression ?? "neutral", speaking: Boolean(c.speaking) }] : []));
  if (seats.length === 0) return null;
  return <div className="sprite seatstrip" role="img" aria-label={tr("sprite.scene.seat_row")} dangerouslySetInnerHTML={{ __html: seatRow(seats) }} />;
}

/** The sprite spec of one child, as JSON: what the page drew and why (judge mode). */
export function SpriteSpec({ child }: { child: { persona?: string | null; expression?: string; speaking?: boolean } | undefined }) {
  const { tr } = useApp();
  if (!child?.persona) return null;
  const { seed, look } = personaLook(child.persona);
  const spec = { persona: child.persona, seed, look, expression: child.expression, mouth: child.speaking ? "open" : "closed", table: "services/api/sprites/expression.py" };
  return (
    <div data-testid="sprite-spec">
      <h4>{tr("sprite.spec_title")}</h4>
      <pre className="spec">{JSON.stringify(spec, null, 1)}</pre>
    </div>
  );
}

/** One item on its own, 24 by 24, in the default palette. */
function itemIcon(id: string): string {
  const inner = compileItem(loadItem(id), palette("default"));
  return inner.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" role="img" ');
}

/** Tray pictures are sprite items drawn here from the enabled pack: no image files. */
function MaterialArt({ item }: { item: string | undefined }) {
  if (!item) return null;
  let svg: string;
  try {
    svg = itemIcon(item);
  } catch {
    return null;
  }
  return <div className="sprite tool-art" aria-hidden="true" dangerouslySetInnerHTML={{ __html: svg }} />;
}

export function Materials({ items, itemFor, disabled, onTap }: { items: string[]; itemFor: Record<string, string>; disabled: boolean; onTap: (material: string) => void }) {
  const { tr } = useApp();
  const names: Record<string, string> = { bundles: tr("practice.bundles"), sticks: tr("practice.sticks"), chart: tr("practice.chart") };
  return (
    <>
    <div className="tray" role="group" aria-label={tr("practice.materials")}>
      {items.map((m) => (
        <button key={m} type="button" className="tool" disabled={disabled} onClick={() => onTap(m)} data-testid={`tap-${m}`}>
          <MaterialArt item={itemFor[m]} />
          <span>{names[m] ?? m}</span>
        </button>
      ))}
    </div>
    <p className="muted" data-testid="tray-help">{tr("practice.tray_help")}</p>
    </>
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
