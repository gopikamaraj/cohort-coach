// T3: what my class gets wrong. Plain-language cards with counts (never percentages), an
// example drawn from her own class's answers, a listen button (audio arrives with voice), and a
// "this is wrong" flag. The flag is kept on the phone for now: these cards are made by code.
import { useState } from "react";
import { buildCards } from "../lib/cards";
import { IconButton } from "../components/icons";
import { useToast } from "../components/toast";
import { sendFeedback } from "../lib/feedback";
import { useConsent } from "../lib/useConsent";
import { Sticks, SimulatedBanner } from "../components/parts";
import { href } from "../lib/router";
import type { Key } from "../i18n";
import { useApp } from "../state";
import { StageLines } from "../components/stages";
import { BeforeAfter } from "../components/BeforeAfter";
import { formatCheckLabel, shownClassName } from "../lib/checks";

export default function Cards() {
  const { tr, lang, role, online, klass, profile, check } = useApp();
  const toast = useToast();
  const consent = useConsent();
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
    if (!consent?.feedback) {
      toast(tr("feedback.need_consent"));
      return;
    }
    setFlagged(new Set(flagged).add(code));
    // No free text, just which card; the admin reviews it.
    void sendFeedback({ kind: "card_flag", language: lang, role, context: code }, online).then(() => toast(tr("cards.flagged"), "ok"));
  };

  return (
    <section aria-labelledby="cards-title">
      <h1 id="cards-title">{tr("cards.title")}</h1>
      {klass?.simulated || profile.simulated ? <SimulatedBanner /> : null}
      {check?.kind ? (
        <p data-testid="cards-check-label">
          <strong>{formatCheckLabel(tr, check, shownClassName(tr, klass), lang)}</strong>
        </p>
      ) : null}
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
                <IconButton icon="speaker" label={tr("cards.audio")} iconOnly testId={`listen-${c.code}`} onClick={() => toast(tr("cards.audio_soon"))} />
                <IconButton icon="flag" label={tr("cards.flag")} iconOnly variant="flag" testId={`flag-${c.code}`} onClick={() => flag(c.code)} disabled={flagged.has(c.code)} />
              </div>
            </li>
          );
        })}
      </ul>
      {profile.stages ? <StageLines stages={profile.stages} /> : null}
      {view.untracked > 0 ? <p data-testid="untracked">{tr("cards.untracked", { n: view.untracked })}</p> : null}
      {view.anchorWrong > 0 ? <p>{tr("cards.anchor", { n: view.anchorWrong })}</p> : null}
      <BeforeAfter />
    </section>
  );
}
