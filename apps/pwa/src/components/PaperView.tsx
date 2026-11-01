// One check paper on screen: its status, a preview of the items (anchor and adaptive apart), the
// answer key, a grid of which items check each error, and the automatic check results. The numbers
// come from the server's paper record; nothing is computed here but the grouping.
import { useState } from "react";
import type { Key } from "../i18n";
import { coverageGrid, itemText, layoutName, pdfUrl, PaperError, type Layout, type Paper, type PaperRole } from "../lib/papers";
import { Busy } from "./Busy";
import { Icon } from "./icons";
import { useApp } from "../state";
import { WhyLines } from "./WhyLines";

export function PaperView({ paper, role, layout, showKey = false }: { paper: Paper; role: PaperRole; layout?: Layout; showKey?: boolean }) {
  const { tr } = useApp();
  const [keyOpen, setKeyOpen] = useState(showKey);
  const [msg, setMsg] = useState("");
  const [opening, setOpening] = useState<"paper" | "key" | null>(null);
  const anchors = paper.items.filter((i) => i.is_anchor);
  const adaptive = paper.items.filter((i) => !i.is_anchor);
  const grid = coverageGrid(paper);
  const lay = layout ?? paper.language;

  async function open(what: "paper" | "key") {
    setMsg("");
    setOpening(what);
    try {
      const url = await pdfUrl(paper.id, what, lay, role);
      window.open(url, "_blank", "noopener");
    } catch (e) {
      setMsg(tr(e instanceof PaperError && e.status === 409 ? "papers.queued_note" : "papers.error"));
    } finally {
      setOpening(null);
    }
  }

  const list = (items: Paper["items"]) => (
    <ul className="plain paper-items">
      {items.map((it) => (
        <li key={it.n} data-testid={`paper-item-${it.n}`}>
          <span className="paper-n">{it.n}.</span> {itemText(it, tr("papers.say"))}
          {keyOpen ? (
            <span className="muted">
              {" "}
              · {tr("papers.correct")} <strong>{it.correct}</strong>
              {Object.keys(it.wrong).length
                ? Object.entries(it.wrong).map(([code, answers]) => ` · ${code}: ${answers.join(", ")}`)
                : ` · ${tr(it.template === "sub-no-borrow" ? "papers.no_error_anchor" : "papers.no_error")}`}
            </span>
          ) : null}
          <WhyLines why={it.why} testId={`why-${it.n}`} />
        </li>
      ))}
    </ul>
  );

  return (
    <article className="card stack" data-testid="paper-view" aria-label={tr("papers.paper_for", { code: paper.check_code })}>
      <h3 className="paper-code" data-testid="paper-code">
        {paper.check_code}
      </h3>
      <p>
        <span className="chip" data-testid="paper-status">
          {tr(`papers.status.${paper.status}` as Key)}
        </span>
        {paper.frozen ? <span className="chip"> {tr("papers.frozen")}</span> : null}
        {paper.custom ? <span className="chip"> {tr("papers.reason.custom")}</span> : null}
      </p>
      <p className="muted" data-testid="paper-source">
        {tr(`papers.source_${paper.profile_source}` as Key)} · {tr(`papers.plan.${paper.blueprint}` as Key)} · {tr("papers.rules_v", { n: paper.rules_version })} ·{" "}
        {layoutName(tr as never, paper.language)}
      </p>
      {paper.status === "queued" ? <p role="status">{tr("papers.queued_note")}</p> : null}
      {paper.status === "rejected" && paper.rejected_reason ? <p role="status">{tr("papers.rejected_note", { reason: paper.rejected_reason })}</p> : null}

      <h4>{tr("papers.anchor_title")}</h4>
      <p className="muted">{tr("papers.anchor_note")}</p>
      <div data-testid="paper-anchors">{list(anchors)}</div>
      {adaptive.length ? (
        <>
          <h4>{tr("papers.adaptive_title")}</h4>
          <p className="muted">{tr("papers.adaptive_note")}</p>
          <div data-testid="paper-adaptive">{list(adaptive)}</div>
        </>
      ) : null}
      {paper.not_assessed.length ? (
        <p data-testid="paper-not-assessed">
          {tr("papers.not_assessed")}: {paper.not_assessed.map((s) => tr(`papers.skill.${s}` as Key)).join(", ")}
        </p>
      ) : null}

      <h4>{tr("papers.coverage_title")}</h4>
      <div className="table-scroll" role="region" tabIndex={0} aria-label={tr("papers.coverage_title")}>
        <table data-testid="coverage-grid">
          <thead>
            <tr>
              <th scope="col">{tr("papers.coverage_col_code")}</th>
              {paper.items.map((it) => (
                <th key={it.n} scope="col">
                  {it.n}
                </th>
              ))}
              <th scope="col">{tr("papers.coverage_col_count")}</th>
            </tr>
          </thead>
          <tbody>
            {grid.map((row) => (
              <tr key={row.code} data-testid={`coverage-${row.code}`}>
                <th scope="row">{row.code}</th>
                {paper.items.map((it) => (
                  <td key={it.n} aria-label={row.items.has(it.n) ? tr("papers.coverage_yes", { n: it.n }) : undefined}>
                    {row.items.has(it.n) ? "●" : ""}
                  </td>
                ))}
                <td>{row.assessed ? row.count : tr("papers.not_assessed")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h4>
        {tr("papers.checks_title")}
        <span className="obs">
          <button type="button" className="obs-btn info-btn" aria-label={tr("papers.checks_what")} aria-describedby={`checks-what-${paper.id}`} data-testid="paper-checks-info">
            <Icon name="info" size={18} />
          </button>
          <span role="tooltip" id={`checks-what-${paper.id}`} className="obs-tip" data-testid="paper-checks-info-text">
            <strong>{tr("papers.checks_what")}</strong>
            {(["key", "wrong", "distinct", "dupes", "coverage", "twin", "words", "layout"] as const).map((k) => (
              <span key={k}>{tr(`papers.check_${k}` as Key)}</span>
            ))}
          </span>
        </span>
      </h4>
      {paper.findings.length === 0 ? (
        <p data-testid="paper-checks-ok">{tr("papers.checks_ok")}</p>
      ) : (
        <ul data-testid="paper-findings">
          {paper.findings.map((f, i) => (
            <li key={i}>
              {f.rule}
              {f.item ? ` (${tr("papers.item_n", { n: f.item })})` : ""}: {f.detail}
            </li>
          ))}
        </ul>
      )}

      <div className="row">
        <button type="button" className="btn btn-primary" disabled={!paper.printable && role !== "coach"} onClick={() => void open("paper")} data-testid="paper-print">
          {tr("papers.print")}
        </button>
        <button type="button" className="btn btn-secondary" disabled={!paper.printable && role !== "coach"} onClick={() => void open("key")} data-testid="paper-key-pdf">
          {tr("papers.key")}
        </button>
        <button type="button" className="btn btn-secondary" aria-pressed={keyOpen} onClick={() => setKeyOpen(!keyOpen)} data-testid="paper-key-toggle">
          {keyOpen ? tr("papers.key_hide") : tr("papers.key_show")}
        </button>
      </div>
      {opening ? <Busy text={tr(opening === "paper" ? "papers.opening_paper" : "papers.opening_key")} testId="paper-pdf-busy" /> : null}
      {msg ? <p role="alert">{msg}</p> : null}
    </article>
  );
}
