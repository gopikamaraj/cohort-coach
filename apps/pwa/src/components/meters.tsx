// A confusion meter per child: how strongly each simulated child still holds the mistake. A word and a
// bar, never colour alone, from the engine's state. The children are simulated.
import type { Key } from "../i18n";
import type { ChildMeter } from "../lib/watch";
import { useApp } from "../state";

export function Meters({ children }: { children: ChildMeter[] }) {
  const { tr } = useApp();
  return (
    <ul className="meters" aria-label={tr("watch.meter")} data-testid="meters">
      {children.map((c) => (
        <li key={c.name}>
          <span>{c.name}</span>
          <span className="meter" aria-hidden="true">
            <span style={{ width: `${Math.round(c.level * 100)}%` }} />
          </span>
          <span>{tr(`watch.band.${c.band}` as Key)}</span>
        </li>
      ))}
    </ul>
  );
}
