// Watch (judge mode): an AI teacher runs the Practice Class in an experienced or a struggling style.
// The run is data from the server, played back here with pause, step, 2x and skip to feedback.
// Every teacher line says it is the AI playing the teacher; every child line carries an English
// subtitle; each turn shows the move, a confusion meter and, on request, what the machinery did.
import { useCallback, useEffect, useRef, useState } from "react";
import { Icon } from "../components/icons";
import { SimulatedBanner } from "../components/parts";
import type { Key } from "../i18n";
import { fetchMeter, fetchRun, nextPlayback, TURN_MS, type Meter, type Playback, type Style, type WatchRun, type WatchTurn } from "../lib/watch";
import { useJudge } from "../lib/roles";
import { useApp } from "../state";
import { Meters } from "../components/meters";
import { SeatStrip, SpriteSpec } from "../components/practice";

const STYLES: Style[] = ["experienced", "struggling"];

function Machinery({ turn }: { turn: WatchTurn }) {
  const { tr } = useApp();
  const m = turn.machinery;
  return (
    <div className="panel" data-testid={`machinery-${turn.turn}`}>
      <h4>{tr("watch.code")}</h4>
      <p>
        {tr("watch.code_line", { move: turn.teacher.move.label, who: String(m.code.engine["speaker"] ?? "-"), intent: String(m.code.engine["intent"] ?? "-") })}
      </p>
      <h4>{tr("watch.ai")}</h4>
      <ul>
        {m.ai_calls.map((c) => (
          <li key={c.call}>
            {tr("watch.call_line", { n: c.call, name: c.name, ms: c.latency_ms ?? 0 })} ({c.source})
          </li>
        ))}
      </ul>
      <h4>{tr("watch.checks")}</h4>
      <p>
        {m.validators.map((v) => `${v.ok ? "✓" : "✗"} ${v.name}`).join("  ")}
        {m.checker ? `  ${m.checker.passed ? "✓" : "✗"} checker` : ""}
      </p>
      {m.fallback ? <p className="muted">{tr("watch.fallback", { why: m.fallback })}</p> : null}
      <SpriteSpec child={turn.children.find((c) => c.speaking)} />
    </div>
  );
}

function TurnCard({ turn, machinery }: { turn: WatchTurn; machinery: boolean }) {
  const { tr } = useApp();
  const tag = turn.teacher.move;
  return (
    <article className="panel" data-testid={`watch-turn-${turn.turn}`}>
      <p className="muted" data-testid={`ai-label-${turn.turn}`}>
        {tr("watch.ai_label")}
      </p>
      <p>
        <strong>{tr("watch.teacher")}:</strong> {turn.teacher.line}
      </p>
      <p className="muted" data-testid={`move-tag-${turn.turn}`}>
        {tr("watch.move", { move: tag.label })}
        {tag.strategy ? `, ${tr("watch.strategy")}` : ""}
        {tag.quality === "common_mistake" ? `, ${tr("watch.mistake")}` : ""}
      </p>
      {turn.child.text ? (
        <>
          <p>
            <strong>{turn.child.speaker}:</strong> {turn.child.text}
          </p>
          {typeof turn.child.written === "number" ? (
            <p className="slate" data-testid={`slate-${turn.turn}`}>
              {tr("practice.slate", { who: turn.child.speaker ?? "", n: turn.child.written })}
            </p>
          ) : null}
          <p className="muted" data-testid={`subtitle-${turn.turn}`}>
            {tr("watch.subtitle")}: {turn.child.text_en}
          </p>
        </>
      ) : null}
      <SeatStrip children={turn.children} />
      <Meters children={turn.children} />
      {machinery ? <Machinery turn={turn} /> : null}
    </article>
  );
}

function Feedback({ run }: { run: WatchRun }) {
  const { tr } = useApp();
  return (
    <div className="panel" data-testid={`feedback-${run.provenance.style}`}>
      <h3>{tr(`watch.style.${run.provenance.style}` as Key)}</h3>
      <p className="muted">{tr("watch.touched", { n: run.summary.rubric_points_touched, total: run.summary.rubric_points })}</p>
      {run.feedback.strengths.map((s) => (
        <p key={s.point}>
          <strong>{s.text}</strong> {s.comment}
          <br />
          <span className="muted">“{s.quote}” ({tr("watch.turn", { n: s.turn })})</span>
        </p>
      ))}
      <p>
        <strong>{tr("watch.try_next")}:</strong> {run.feedback.try_next.suggestion}
      </p>
      <p className="muted">{tr("watch.checked")}</p>
    </div>
  );
}

function RunView({ run }: { run: WatchRun }) {
  const { tr } = useApp();
  const total = run.turns.length;
  const [p, setP] = useState<Playback>({ index: 0, playing: true, speed: 1 });
  const [machinery, setMachinery] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (!p.playing) return;
    timer.current = setTimeout(() => setP((x) => nextPlayback(x, total, "tick")), TURN_MS / p.speed);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [p, total]);
  const act = (a: Parameters<typeof nextPlayback>[2]) => setP((x) => nextPlayback(x, total, a));
  const shown = run.turns.slice(0, p.index);
  return (
    <section className="stack" data-testid={`run-${run.provenance.style}`}>
      <p className="chip" data-testid="run-kind">
        {run.kind === "live run" ? tr("watch.live") : tr("watch.recorded")}
        {run.kind === "recorded run" && run.provenance.recorded_at ? ` · ${run.provenance.recorded_at}` : ""}
      </p>
      {run.reason ? <p role="status" data-testid="run-reason">{tr("watch.why", { why: run.reason })}</p> : null}
      <div className="stack row">
        <button type="button" className="btn btn-secondary" onClick={() => act(p.playing ? "pause" : "play")} data-testid="w-play">
          {p.playing ? tr("watch.pause") : tr("watch.play")}
        </button>
        <button type="button" className="btn btn-secondary" onClick={() => act("step")} data-testid="w-step">
          {tr("watch.step")}
        </button>
        <button type="button" className="btn btn-secondary" onClick={() => act("fast")} aria-pressed={p.speed === 2} data-testid="w-fast">
          2×
        </button>
        <button type="button" className="btn btn-secondary" onClick={() => act("skip")} data-testid="w-skip">
          {tr("watch.skip")}
        </button>
        <label className="check">
          <input type="checkbox" checked={machinery} onChange={(e) => setMachinery(e.target.checked)} data-testid="w-machinery" />
          <span>{tr("watch.machinery")}</span>
        </label>
      </div>
      {shown.map((t) => (
        <TurnCard key={t.turn} turn={t} machinery={machinery} />
      ))}
      {p.index >= total ? <Feedback run={run} /> : null}
    </section>
  );
}

export default function Watch() {
  const { tr, lang } = useApp();
  const judge = useJudge();
  const [runs, setRuns] = useState<Partial<Record<Style, WatchRun>>>({});
  const [busy, setBusy] = useState<Style | null>(null);
  const [live, setLive] = useState(false);
  const [failed, setFailed] = useState(false);
  const [meter, setMeter] = useState<Meter | null>(null);

  const refreshMeter = useCallback(() => void fetchMeter().then(setMeter), []);
  useEffect(refreshMeter, [refreshMeter]);

  const load = (style: Style) => {
    setBusy(style);
    setFailed(false);
    fetchRun(style, lang, live)
      .then((r) => setRuns((x) => ({ ...x, [style]: r })))
      .catch(() => setFailed(true))
      .finally(() => {
        setBusy(null);
        refreshMeter();
      });
  };

  if (!judge) {
    return (
      <section aria-labelledby="watch-title">
        <h1 id="watch-title">{tr("watch.title")}</h1>
        <p role="status">{tr("watch.demo_only")}</p>
      </section>
    );
  }
  const both = runs.experienced && runs.struggling;
  return (
    <section aria-labelledby="watch-title" data-testid="watch">
      <h1 id="watch-title">
        <Icon name="practice" /> {tr("watch.title")}
      </h1>
      <SimulatedBanner />
      <p>{tr("watch.intro")}</p>
      <div className="stack">
        {STYLES.map((s) => (
          <button key={s} type="button" className="btn btn-primary" disabled={busy !== null} onClick={() => load(s)} data-testid={`watch-${s}`}>
            {tr(`watch.style.${s}` as Key)}
          </button>
        ))}
        <label className="check">
          <input type="checkbox" checked={live} onChange={(e) => setLive(e.target.checked)} data-testid="watch-live" />
          <span>{tr("watch.live_box")}</span>
        </label>
        {meter ? (
          <p className="muted" data-testid="watch-meter">
            {tr("watch.meter_line", { n: meter.live_runs_this_hour, cap: meter.cap_per_hour, cost: meter.cost_usd_this_hour.toFixed(3) })}
          </p>
        ) : null}
      </div>
      {busy ? <p role="status">{tr("watch.loading")}</p> : null}
      {failed ? <p role="alert">{tr("flow.error")}</p> : null}
      <div className={both ? "compare" : undefined}>
        {STYLES.map((s) => (runs[s] ? <RunView key={`${s}-${runs[s]?.provenance.recorded_at ?? ""}-${runs[s]?.kind}`} run={runs[s]!} /> : null))}
      </div>
    </section>
  );
}
