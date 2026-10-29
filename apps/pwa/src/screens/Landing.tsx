// The landing page: four role cards and the guided tour. Picking a role opens a scope dialog built
// from the server's role config (what the role can and cannot do), then the role's dashboard.
import { useCallback, useEffect, useState } from "react";
import { Icon } from "../components/icons";
import { InstallEntry } from "../components/install";
import { CAN_SWITCH_MODE } from "../lib/api";
import type { Key } from "../i18n";
import { go, useQuery, type Route } from "../lib/router";
import { dialogSeen, loadRoles, markDialogSeen, type RoleConfig, type RoleId, type RolesResponse } from "../lib/roles";
import { useApp, type Role } from "../state";
import { WALK_START } from "../lib/tour";

export const ROLE_HOME: Record<RoleId, Route> = {
  teacher: "/home",
  mentor: "/mentor",
  coach: "/coach",
  officer: "/officer",
};
const ICON: Record<RoleId, string> = { teacher: "home", mentor: "mentor", coach: "coach", officer: "programme" };

function Dialog({ cfg, onEnter, onWalk, onBack }: { cfg: RoleConfig; onEnter: () => void; onWalk: () => void; onBack: () => void }) {
  const { tr } = useApp();
  const line = (l: { id: string; key: string; planned: string | null }) => (
    <li key={l.id}>
      {tr(l.key as Key)}
      {l.planned ? <span className="muted"> ({tr("roles.soon")})</span> : null}
    </li>
  );
  return (
    <div className="panel" role="dialog" aria-modal="true" aria-labelledby="dlg-title" data-testid="role-dialog">
      <h2 id="dlg-title">{tr(`role.${cfg.id}` as Key)}</h2>
      <p className="muted">{tr(cfg.holders as Key)}</p>
      <h3>{tr("dlg.can")}</h3>
      <ul>{cfg.can.map(line)}</ul>
      <h3>{tr("dlg.cannot")}</h3>
      <ul data-testid="dlg-cannot">{cfg.cannot.map(line)}</ul>
      <h3>{tr("dlg.data")}</h3>
      <p>{tr(cfg.data as Key)}</p>
      {cfg.also_on.length > 0 ? (
        <p>
          <strong>{tr("dlg.also_on")}:</strong> Telegram
        </p>
      ) : null}
      <p>
        <strong>{tr("dlg.weekly")}:</strong>{" "}
        {cfg.weekly_minutes === null ? tr("dlg.weekly_none") : tr("dlg.minutes", { n: cfg.weekly_minutes })}
      </p>
      <div className="stack">
        <button type="button" className="btn btn-primary" onClick={onEnter} data-testid="dlg-enter">
          {tr("dlg.enter")}
        </button>
        <button type="button" className="btn btn-secondary" onClick={onWalk} data-testid="dlg-walk">
          {tr("dlg.walk")}
        </button>
        <button type="button" className="btn btn-secondary" onClick={onBack} data-testid="dlg-back">
          {tr("dlg.back")}
        </button>
      </div>
    </div>
  );
}

export default function Landing() {
  const { tr, role, setRole } = useApp();
  const query = useQuery();
  const [data, setData] = useState<RolesResponse | null>(null);
  const [failed, setFailed] = useState(false);
  const [open, setOpen] = useState<RoleId | null>(null);

  const load = useCallback(() => {
    setFailed(false);
    loadRoles().then(setData, () => setFailed(true));
  }, []);
  useEffect(load, [load]);

  const wanted = query.get("open");
  useEffect(() => {
    if (data && wanted && data.roles.some((r) => r.id === wanted)) setOpen(wanted as RoleId);
  }, [data, wanted]);

  const enter = (id: RoleId) => {
    markDialogSeen(id);
    setRole(id as Role);
    go(ROLE_HOME[id]);
  };
  const choose = (id: RoleId) => {
    if (dialogSeen(id)) enter(id);
    else setOpen(id);
  };

  const cfg = data?.roles.find((r) => r.id === open) ?? null;
  return (
    <section className="landing" aria-labelledby="landing-title">
      <div className="l-hero">
        <h1 id="landing-title">{tr("landing.title")}</h1>
        <p className="l-lead">{tr("landing.intro")}</p>
        <ul className="l-chips" data-testid="mode-banner">
          <li className="m-chip" title={tr("mode.judge_hint")}>
            <Icon name="mode" size={18} />
            <span>
              <strong>{tr("mode.label")}:</strong> {tr("mode.judge")}
            </span>
          </li>
          <li className="m-chip" data-testid="mode-role">
            <Icon name="profile" size={18} />
            <span>
              <strong>{tr("mode.role")}:</strong> {tr(`role.${role === "judge" ? "teacher" : role}` as Key)}
            </span>
          </li>
        </ul>
      </div>
      {failed ? (
        <div className="m-note m-note-error" role="alert" data-testid="landing-error">
          <p>{tr("flow.error")}</p>
          <button type="button" className="m-btn m-btn-filled" onClick={load}>
            {tr("flow.retry")}
          </button>
        </div>
      ) : null}
      {cfg ? (
        <Dialog cfg={cfg} onEnter={() => enter(cfg.id)} onWalk={() => { markDialogSeen(cfg.id); setRole(cfg.id as Role); window.location.hash = `/tour/${WALK_START[cfg.id]}`; }} onBack={() => setOpen(null)} />
      ) : (
        <>
          <div className="role-cards" data-testid="role-cards">
            <a className="tile tile-start" href="#/tour/1" data-testid="card-tour">
              <span className="m-iconwell m-iconwell-on" aria-hidden="true">
                <Icon name="judge" size={28} />
              </span>
              <span className="l-card-text">
                <strong className="role-name">{tr("landing.tour")}</strong>
                <span className="role-line">{tr("landing.tour_hint")}</span>
              </span>
              <Icon name="chevron" size={24} className="l-go" />
            </a>
            {data?.roles.map((r) => (
              <button key={r.id} type="button" className="tile" onClick={() => choose(r.id)} data-testid={`card-${r.id}`}>
                <span className="m-iconwell" aria-hidden="true">
                  <Icon name={ICON[r.id]} size={28} />
                </span>
                <span className="l-card-text">
                  <strong className="role-name">{tr(`role.${r.id}` as Key)}</strong>
                  <span className="muted role-line">{tr(r.holders as Key)}</span>
                  <span className="role-line">{tr(r.card as Key)}</span>
                </span>
                <Icon name="chevron" size={24} className="l-go" />
              </button>
            ))}
          </div>
          <InstallEntry variant="card" />
          {CAN_SWITCH_MODE ? <p className="muted l-foot">{tr("landing.pilot_note")}</p> : null}
        </>
      )}
    </section>
  );
}
