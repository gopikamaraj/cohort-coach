// The cost and time of the LAST action, in a slim bar above the bottom tabs. Tap it for the table. It is
// this action only, never a total: the next action starts it again from nothing. Cloud Run and anything
// else that is an estimate says "est.".
import { useState, useSyncExternalStore } from "react";
import type { Key } from "../i18n";
import { footerOn, getAction, money, seconds, setFooterOn, subscribe, totalText, type KindUsage } from "../lib/action";
import { useApp } from "../state";

const num = (n: number | undefined) => new Intl.NumberFormat().format(Math.round((n ?? 0) * 10) / 10);
const USD = { currency: "USD", inr_per_usd: null };

export function UsageFooter() {
  const { tr } = useApp();
  const action = useSyncExternalStore(subscribe, getAction);
  const on = useSyncExternalStore(subscribe, footerOn);
  const [open, setOpen] = useState(false);
  if (!on || !action) return null;
  const u = action.usage;
  const working = action.phase !== "done";
  const na = tr("usage.na");
  const label = tr(`usage.a.${action.name}` as Key) || action.name;
  const shown = (k: KindUsage): string => {
    const d = u?.display ?? USD;
    if (k.calls === 0) return "—";
    if (k.priced) return money(k.cost_usd, d);
    return k.cost_usd > 0 ? `${money(k.cost_usd, d)} + ${na}` : na;
  };
  const time = action.wallMs !== null ? seconds(action.wallMs) : "…";
  return (
    <aside className="usage" data-testid="usage-footer" data-phase={action.phase} aria-label={tr("usage.last")}>
      {open ? (
        <div className="usage-panel" role="region" aria-label={tr("usage.last")} data-testid="usage-panel">
          <p className="usage-only">{tr("usage.this_only")}</p>
          {u ? (
            <table>
              <tbody>
                <tr>
                  <th scope="row">{tr("usage.claude")}</th>
                  <td>{tr("usage.calls", { n: u.by_kind.llm.calls })}</td>
                  <td>{tr("usage.tokens", { i: num(u.by_kind.llm.input_tokens), o: num(u.by_kind.llm.output_tokens) })}</td>
                  <td>{shown(u.by_kind.llm)}</td>
                </tr>
                <tr>
                  <th scope="row">{tr("usage.tts")}</th>
                  <td>{tr("usage.calls", { n: u.by_kind.tts.calls })}</td>
                  <td>{tr("usage.characters", { n: num(u.by_kind.tts.characters) })}</td>
                  <td>{shown(u.by_kind.tts)}</td>
                </tr>
                <tr>
                  <th scope="row">{tr("usage.stt")}</th>
                  <td>{tr("usage.calls", { n: u.by_kind.stt.calls })}</td>
                  <td>{tr("usage.audio_seconds", { n: num(u.by_kind.stt.seconds) })}</td>
                  <td>{shown(u.by_kind.stt)}</td>
                </tr>
                <tr>
                  <th scope="row">
                    {tr("usage.cloud")} <span className="usage-est">{tr("usage.est")}</span>
                  </th>
                  <td>{tr("usage.calls", { n: u.by_kind.cloud_run.calls })}</td>
                  <td>
                    {seconds(u.time.request_ms)}
                    {u.by_kind.cloud_run.cold ? ` · ${tr("usage.cold")}` : ""}
                  </td>
                  <td>{shown(u.by_kind.cloud_run)}</td>
                </tr>
                <tr>
                  <th scope="row">{tr("usage.time")}</th>
                  <td colSpan={3}>
                    {tr("usage.wall", { t: seconds(action.wallMs ?? 0) })} · {tr("usage.sum", { t: seconds(u.time.calls_sum_ms) })}
                  </td>
                </tr>
                <tr className="usage-total">
                  <th scope="row">{tr("usage.total")}</th>
                  <td colSpan={3}>{totalText(u, na)}</td>
                </tr>
              </tbody>
            </table>
          ) : (
            <p className="muted">{tr("usage.counting")}</p>
          )}
          {u && u.by_kind.llm.calls + u.by_kind.tts.calls + u.by_kind.stt.calls === 0 ? <p className="muted">{tr("usage.none_billed")}</p> : null}
          <button type="button" className="btn btn-secondary" onClick={() => setFooterOn(false)} data-testid="usage-hide">
            {tr("usage.hide")}
          </button>
        </div>
      ) : null}
      <button type="button" className="usage-bar" aria-expanded={open} onClick={() => setOpen((v) => !v)} data-testid="usage-toggle">
        <span>
          {tr("usage.last")}: {label}
        </span>
        <span aria-hidden="true">|</span>
        <span>{time}</span>
        <span aria-hidden="true">|</span>
        <span>{u ? totalText(u, na) : "…"}</span>
        {working ? (
          <span className="usage-busy" role="status" aria-label={tr("usage.counting")}>
            ⋯
          </span>
        ) : null}
      </button>
    </aside>
  );
}
