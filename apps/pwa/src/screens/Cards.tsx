// T3: what my class gets wrong. Plain-language cards with counts (never percentages), an
// example drawn from her own class's answers, a listen button (audio arrives with voice), and a
// "this is wrong" flag. The flag is kept on the phone for now: these cards are made by code.
import { useState } from "react";
import { buildCards } from "../lib/cards";
import { db } from "../lib/db";
import { Sticks, SimulatedBanner } from "../components/parts";
import { href } from "../lib/router";
import type { Key } from "../i18n";
import { useApp } from "../state";

export default function Cards() {
  const { tr, klass, profile, check } = useApp();
  const [soon, setSoon] = useState<string | null>(null);
  const [flagged, setFlagged] = useState<Set<string>>(new Set());

  if (!profile) {
    return (
      <section aria-labelledby="cards-title">
        <h1 id="cards-title">{tr("cards.title")}</h1>
        <p data-testid="cards-none">{tr("cards.none")}</p>
        <a className="btn btn-primary" href={href("/check")}>
          {tr("home.action.check")}
        </a>
      </section>
    );
  }

  const view = buildCards(profile, check ? check.children : null);
  const flag = (code: string) => {
    setFlagged(new Set(flagged).add(code));
    // Kept on the phone and queued: no free text, just which card.
    void db.syncQueue.add({ kind: "flag", classId: profile.classId, payload: { card: code, term: profile.term }, createdAt: Date.now(), tries: 0 });
  };

  return (
    <section aria-labelledby="cards-title">
      <h1 id="cards-title">{tr("cards.title")}</h1>
      {klass?.simulated || profile.simulated ? <SimulatedBanner /> : null}
      <p className="muted">{tr("cards.checked", { n: view.childrenChecked })}</p>
      {view.tooSmall ? <p>{tr("cards.small", { min: view.minChildren })}</p> : null}
      <ul className="cards">
        {view.cards.map((c) => {
          const name = tr(`err.${c.code}` as Key);
          const line = tr("cards.line", { n: c.count, total: c.total, desc: tr(`err.desc.${c.code}` as Key) });
          return (
            <li key={c.code} className={c.isFocus ? "card card-focus" : "card"} data-testid={`card-${c.code}`}>
              <h2>{name}</h2>
              <p className="count">
                <span className="numeral">{c.count}</span> <span className="muted">/ {c.total}</span>
              </p>
              <Sticks count={c.count} total={c.total} label={line} />
              <p data-testid={`line-${c.code}`}>{line}</p>
              {c.example ? <p className="example">{tr("cards.example", { example: c.example })}</p> : null}
              {c.isFocus ? <p className="focus">{tr("cards.focus")}</p> : null}
              <div className="row">
                <button type="button" className="btn btn-secondary" onClick={() => setSoon(c.code)}>
                  {tr("cards.audio")}
                </button>
                <button type="button" className="btn btn-flag" onClick={() => flag(c.code)} disabled={flagged.has(c.code)}>
                  {tr("cards.flag")}
                </button>
              </div>
              {soon === c.code ? <p className="muted" role="status">{tr("cards.audio_soon")}</p> : null}
              {flagged.has(c.code) ? <p role="status">{tr("cards.flagged")}</p> : null}
            </li>
          );
        })}
      </ul>
      {view.untracked > 0 ? <p data-testid="untracked">{tr("cards.untracked", { n: view.untracked })}</p> : null}
      {view.anchorWrong > 0 ? <p>{tr("cards.anchor", { n: view.anchorWrong })}</p> : null}
    </section>
  );
}
