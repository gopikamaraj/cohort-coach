// The stage lines on the error card: where it most likely went wrong, in counts, with a probe.
// Never a percentage, never a cause stated as fact, never shown to a child.
import type { StageCounts } from "../lib/stages";
import { PROBE_KEY, STAGE_KEY, STAGE_ORDER } from "../lib/stages";
import type { Key } from "../i18n";
import { useApp } from "../state";

export function StageLines({ stages }: { stages: StageCounts }) {
  const { tr } = useApp();
  const lineFor = (code: string): string => {
    const key = code === "SUB-SFL" || code === "SUB-NODEC" || code === "PV-HEARD" || code === "PV-REVERSE" || code === "ADD-NOCARRY" ? `err.desc.${code}` : `sig.${code}`;
    return tr(key as Key);
  };
  const stagesShown = STAGE_ORDER.filter((s) => stages.by_stage.some((x) => x.stage === s));
  if (stagesShown.length === 0 && stages.missed_teaching === 0 && stages.not_attempted === 0) return null;
  return (
    <section aria-labelledby="stages-title" data-testid="stage-lines">
      <h2 id="stages-title">{tr("stage.title")}</h2>
      <p className="muted">{tr("stage.note")}</p>
      {stagesShown.map((stage) => (
        <div key={stage} className="card" data-testid={`stage-${stage}`}>
          <h3>{tr(STAGE_KEY[stage] as Key)}</h3>
          <ul>
            {stages.by_signature
              .filter((s) => s.stage === stage)
              .map((s) => (
                <li key={s.code}>{tr("stage.line", { n: s.n, total: stages.checked, what: lineFor(s.code) })}</li>
              ))}
          </ul>
          <p className="muted" data-testid={`probe-${stage}`}>
            {tr("stage.probe", { probe: tr(PROBE_KEY[stage] as Key) })}
          </p>
        </div>
      ))}
      {stages.missed_teaching > 0 ? <p data-testid="stage-missed">{tr("stage.missed", { n: stages.missed_teaching })}</p> : null}
      {stages.not_attempted > 0 ? <p>{tr("stage.blank", { n: stages.not_attempted })}</p> : null}
    </section>
  );
}
