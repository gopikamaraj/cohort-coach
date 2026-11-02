// The summary part of the printed pack: what the error is, why, how to spot it, what to try first, a few
// strategies and how the next check shows whether it is working. It carries no counts and no roll numbers
// (those are in the pack and the answer-sheet pages after it).
import type { Key, Lang } from "../i18n";
import { explanationFor, pick } from "../lib/errorContent";
import { keys } from "../lib/diagnosis";
import type { Pack } from "../lib/pack";
import { useApp } from "../state";

const plain = (t: string) => t.replace(/\{pv:(\d+)\}/g, "$1"); // {pv:N} marks a spoken-only reading

export function PackSummary({ pack, lang, draft }: { pack: Pack; lang: Lang; draft: boolean }) {
  const { tr } = useApp();
  const ex = explanationFor(pack.code);
  const part = (key: Key, field: Parameters<typeof pick>[0]) => {
    const p = pick(field as Partial<Record<Lang, string>> | undefined, lang);
    return p ? (
      <section>
        <h2>{tr(key)}</h2>
        <p>{plain(p.value)}</p>
      </section>
    ) : null;
  };
  const check = pack.sections.find((s) => s.id === "check");
  const strategies = pack.sections.find((s) => s.id === "strategies")?.strategies ?? [];
  const fallback = lang !== "en" && pack.sections.some((s) => s.fallback);
  return (
    <div data-testid="pack-summary">
      <h1>{tr(`err.${pack.code}` as Key)}</h1>
      <p>
        {tr("pack.summary_title")}
        {draft ? ` · ${tr("pack.draft")}` : ""}
      </p>
      {part("results.explain.what", ex?.what)}
      {part("results.explain.why", ex?.why)}
      {part("results.explain.spot", ex?.spot)}
      {part("results.explain.first", ex?.first)}
      {check?.text ? (
        <section>
          <h2>{tr("pack.sec.check")}</h2>
          <p>{plain(check.text)}</p>
        </section>
      ) : null}
      {strategies.length > 0 ? (
        <section>
          <h2>{tr("pack.sec.strategies")}</h2>
          <ul>
            {strategies.map((s) => (
              <li key={s.id}>
                <strong>{s.label}</strong>. {s.description}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      <section>
        <h2>{tr("pack.sec.working")}</h2>
        <p>{tr("pack.summary_working", { n: keys.rules.min_hits })}</p>
      </section>
      {fallback ? <p>{tr("pack.lang_missing", { language: lang })}</p> : null}
    </div>
  );
}
