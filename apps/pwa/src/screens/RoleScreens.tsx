// Coach (a DIET-like role) and Mentor (one of the teachers). Both are small for now and say plainly what is
// built and what is not. The coach sees aggregates only, from the simulated block; nothing about one class.
import { useEffect, useState } from "react";
import { Icon } from "../components/icons";
import { SimulatedBanner } from "../components/parts";
import { API_BASE } from "../lib/api";
import type { Key } from "../i18n";
import { useApp } from "../state";

interface Block {
  classes: number;
  schools: number;
  terms: Record<string, { classes: number; children_checked: number; children_showing: Record<string, number> }>;
}

const ERRORS = ["PV-HEARD", "PV-REVERSE", "ADD-NOCARRY", "SUB-SFL", "SUB-NODEC"] as const;
const MIN_CLASSES = 5; // a figure covering fewer than 5 classes is hidden

export function Coach() {
  const { tr } = useApp();
  const [block, setBlock] = useState<Block | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    fetch(`${API_BASE}/api/demo/block`)
      .then((r) => r.json())
      .then((b) => setBlock(b as Block))
      .catch(() => setFailed(true));
  }, []);
  return (
    <section aria-labelledby="co-title" data-testid="coach">
      <h1 id="co-title">
        <Icon name="coach" /> {tr("coach.title")}
      </h1>
      <SimulatedBanner />
      <p>{tr("coach.intro")}</p>
      {failed ? <p role="alert">{tr("prog.offline")}</p> : null}
      {block ? (
        Object.entries(block.terms).map(([term, t]) => (
          <div key={term} className="panel" data-testid={`coach-${term}`}>
            <h2>{tr("coach.term", { term, classes: t.classes, schools: block.schools })}</h2>
            {t.classes < MIN_CLASSES ? (
              <p>{tr("coach.hidden", { min: MIN_CLASSES })}</p>
            ) : (
              <ul className="plain">
                {ERRORS.map((e) => (
                  <li key={e}>
                    <strong>{tr(`err.${e}` as Key)}</strong>: {tr("coach.count", { n: t.children_showing[e] ?? 0, total: t.children_checked })}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))
      ) : null}
      <p className="muted">{tr("coach.later")}</p>
    </section>
  );
}

export function Mentor() {
  const { tr } = useApp();
  return (
    <section aria-labelledby="me-title" data-testid="mentor">
      <h1 id="me-title">
        <Icon name="mentor" /> {tr("mentor.title")}
      </h1>
      <p>{tr("mentor.intro")}</p>
      <ol className="steps prog">
        {(["1", "2", "3", "4"] as const).map((n) => (
          <li key={n}>
            <strong>
              <Icon name="mic" size={20} /> {tr(`mentor.step${n}` as "mentor.step1")}
            </strong>
          </li>
        ))}
      </ol>
      <p className="muted">{tr("mentor.later")}</p>
    </section>
  );
}
