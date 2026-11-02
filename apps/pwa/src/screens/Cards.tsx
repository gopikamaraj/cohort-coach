// T3: what my class gets wrong. Every finding of the check in one list, each as the same kind of
// card: what kind of finding it is, a title, the count out of the children checked (never a
// percentage) with sticks, the sentence, a listen button (audio arrives with voice) and a "this is
// wrong" flag. Mistakes come first, then where it most likely went wrong (never stated as a cause),
// then what else was seen. The flag is kept on the phone for now: these cards are made by code.
import { useState, type ReactNode } from "react";
import { buildCards } from "../lib/cards";
import { IconButton } from "../components/icons";
import { useToast } from "../components/toast";
import { sendFeedback } from "../lib/feedback";
import { useConsent } from "../lib/useConsent";
import { Sticks, SimulatedBanner } from "../components/parts";
import { href } from "../lib/router";
import type { Key } from "../i18n";
import { useApp } from "../state";
import { PROBE_KEY, STAGE_KEY, STAGE_ORDER } from "../lib/stages";
import { BeforeAfter } from "../components/BeforeAfter";
import { ResultsDetail } from "../components/ResultsDetail";
import { MistakesTable, mistakeRows } from "../components/MistakesTable";
import { buildAnswerMap } from "../lib/results";
import { ClassCohortMaker } from "../components/ClassCohortMaker";
import { formatCheckLabel, shownClassName } from "../lib/checks";

const TRACKED = new Set(["SUB-SFL", "SUB-NODEC", "PV-HEARD", "PV-REVERSE", "ADD-NOCARRY"]);

interface Finding {
  id: string; // also the flag's context
  kind: "error" | "stage" | "other";
  title: string;
  count: number;
  total: number | null; // null: the count is of answers, not children (no sticks)
  lines: string[];
  extra?: ReactNode;
  focus?: boolean;
  testId: string;
  lineTestId?: string;
}

export default function Cards() {
  const { tr, lang, role, online, klass, profile, check } = useApp();
  const toast = useToast();
  const consent = useConsent();
  const [flagged, setFlagged] = useState<Set<string>>(new Set());
  const [code, setCode] = useState<string | null>(null);
  const [onlyConfirmed, setOnlyConfirmed] = useState(false);

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
  const flag = (id: string) => {
    if (!consent?.feedback) {
      toast(tr("feedback.need_consent"));
      return;
    }
    setFlagged(new Set(flagged).add(id));
    // No free text, just which card; the admin reviews it.
    void sendFeedback({ kind: "card_flag", language: lang, role, context: id }, online).then(() => toast(tr("cards.flagged"), "ok"));
  };

  // 1. Mistakes: one row per error in the table (confirmed, and possible when not filtered out).
  const canMap = (role === "teacher" || role === "judge") && Boolean(check) && Boolean(profile);
  const map = canMap && check ? buildAnswerMap(check.formKey, check.children, check.absent ?? [], check.approved) : null;
  const rows = mistakeRows(view.cards, map ? map.legend : null, view.childrenChecked, onlyConfirmed);

  // 2. Where it most likely went wrong: one card per stage, with its one-minute check.
  const st = profile.stages;
  const what = (code: string) => tr((TRACKED.has(code) ? `err.desc.${code}` : `sig.${code}`) as Key);
  const stages: Finding[] = st
    ? STAGE_ORDER.flatMap((stage) => {
        const n = st.by_stage.find((x) => x.stage === stage)?.n ?? 0;
        if (n === 0) return [];
        return [
          {
            id: `stage:${stage}`,
            kind: "stage" as const,
            title: tr(STAGE_KEY[stage] as Key),
            count: n,
            total: st.checked,
            lines: st.by_signature
              .filter((s) => s.stage === stage)
              .map((s) => tr("stage.line", { n: s.n, total: st.checked, what: what(s.code) })),
            extra: (
              <p className="muted" data-testid={`probe-${stage}`}>
                {tr("stage.probe", { probe: tr(PROBE_KEY[stage] as Key) })}
              </p>
            ),
            testId: `stage-${stage}`,
          },
        ];
      })
    : [];

  // 3. What else was seen: missed teaching, left blank, the simple subtraction, the untracked pattern.
  const others: Finding[] = [];
  const other = (id: string, title: string, count: number, total: number | null, line: string, testId: string) =>
    others.push({ id, kind: "other", title, count, total, lines: [line], testId });
  if (st?.missed_by_concept) {
    for (const [concept, n] of Object.entries(st.missed_by_concept)) {
      if (n <= 0) continue;
      const name = tr(`concept.${concept}` as Key);
      other(`missed:${concept}`, tr("cards.other.missed", { concept: name }), n, st.checked, tr("stage.missed_on", { n, concept: name }), `stage-missed-${concept}`);
    }
  } else if (st && st.missed_teaching > 0) {
    other("missed", tr("cards.other.missed_all"), st.missed_teaching, st.checked, tr("stage.missed", { n: st.missed_teaching }), "stage-missed");
  }
  if (st && st.not_attempted > 0) {
    other("blank", tr("cards.other.blank"), st.not_attempted, st.checked, tr("stage.blank", { n: st.not_attempted }), "finding-blank");
  }
  if (view.anchorWrong > 0) {
    other("anchor", tr("cards.other.anchor"), view.anchorWrong, view.childrenChecked, tr("cards.anchor", { n: view.anchorWrong }), "finding-anchor");
  }
  if (view.untracked > 0) {
    other("untracked", tr("cards.other.untracked"), view.untracked, null, tr("cards.untracked", { n: view.untracked }), "untracked");
  }
  others.sort((a, b) => b.count - a.count);

  const findings = [...stages, ...others];
  const kindLabel = { error: tr("cards.kind.error"), stage: tr("stage.title"), other: tr("cards.kind.other") };

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
      {findings.length + view.cards.length > 0 ? <p data-testid="findings-intro">{tr("cards.all_here", { n: findings.length + view.cards.length })}</p> : null}
      <MistakesTable rows={rows} activeCode={code} onCode={setCode} onlyConfirmed={onlyConfirmed} onOnlyConfirmed={(on) => { setOnlyConfirmed(on); if (on && code && !rows.some((r) => r.code === code && r.confirmed > 0)) setCode(null); }} flagged={flagged} onFlag={flag} canHighlight={canMap} />
      <ul className="cards findings" data-testid="findings">
        {findings.map((f) => (
          <li key={f.id} className={f.focus ? "card card-focus" : "card"} data-testid={f.testId} data-kind={f.kind}>
            <p className={`chip finding-kind finding-kind-${f.kind}`}>{kindLabel[f.kind]}</p>
            <h2>{f.title}</h2>
            <p className="count">
              <span className="numeral">{f.count}</span>{" "}
              <span className="muted">{f.total === null ? tr("cards.unit_answers") : `/ ${f.total}`}</span>
            </p>
            {f.total !== null ? <Sticks count={f.count} total={f.total} label={f.lines[0] ?? f.title} /> : null}
            {f.lines.length === 1 ? (
              <p data-testid={f.lineTestId}>{f.lines[0]}</p>
            ) : (
              <ul className="finding-lines">
                {f.lines.map((l) => (
                  <li key={l}>{l}</li>
                ))}
              </ul>
            )}
            {f.extra}
            <div className="row">
              <IconButton icon="speaker" label={tr("cards.audio")} iconOnly testId={`listen-${f.id}`} onClick={() => toast(tr("cards.audio_soon"))} />
              <IconButton icon="flag" label={tr("cards.flag")} iconOnly variant="flag" testId={`flag-${f.id}`} onClick={() => flag(f.id)} disabled={flagged.has(f.id)} />
            </div>
          </li>
        ))}
      </ul>
      {stages.length > 0 ? (
        <p className="muted" data-testid="stage-lines">
          {tr("stage.note")}
        </p>
      ) : null}
      <ClassCohortMaker onlyConfirmed={onlyConfirmed} />
      <ResultsDetail untracked={view.untracked} activeCode={code} onCode={setCode} onlyConfirmed={onlyConfirmed} />
      <BeforeAfter hideWhenEmpty />
    </section>
  );
}
