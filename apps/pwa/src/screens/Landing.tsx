// The landing page: four role cards and the guided tour. Picking a role opens a scope dialog built
// from the server's role config (what the role can and cannot do), then the role's dashboard.
import { useCallback, useEffect, useState } from "react";
import { Icon } from "../components/icons";
import { InstallEntry } from "../components/install";
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
  const { tr, setRole } = useApp();
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
      </div>
      <section className="panel stack" aria-labelledby="howto-title" data-testid="how-to-use">
        <h2 id="howto-title">{tr("landing.howto_title")}</h2>
        <ul>
          <li>
            {tr("landing.howto_pilot_pre")} <strong>3A Math</strong> / <strong>3B Math</strong> {tr("landing.howto_pilot_post")} <strong>{tr("role.teacher")}</strong>{tr("landing.howto_pilot_end")}
          </li>
          <li>
            {tr("landing.howto_officer_pre")} <strong>Block Officer</strong> {tr("landing.howto_officer_post")}
          </li>
        </ul>
      </section>
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
          <h2 className="l-group">{tr("landing.judges_title")}</h2>
          <div className="role-cards" data-testid="judge-cards">
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
            <button type="button" className="tile tile-start" onClick={() => {
                setRole("judge");
                go("/judge");
              }} data-testid="card-judge">
              <span className="m-iconwell" aria-hidden="true">
                <Icon name="judge" size={28} />
              </span>
              <span className="l-card-text">
                <strong className="role-name">{tr("role.judge")}</strong>
                <span className="role-line">{tr("landing.judge_hint")}</span>
              </span>
              <Icon name="chevron" size={24} className="l-go" />
            </button>
          </div>
          <h2 className="l-group">{tr("landing.roles_title")}</h2>
          <div className="role-cards" data-testid="role-cards">
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
          <h2 className="l-group">{tr("landing.team_title")}</h2>
          <div className="role-cards" data-testid="team-cards">
            <button
              type="button"
              className="tile tile-start"
              onClick={() => {
                setRole("admin");
                go("/admin");
              }}
              data-testid="card-admin"
            >
              <span className="m-iconwell" aria-hidden="true">
                <Icon name="admin" size={28} />
              </span>
              <span className="l-card-text">
                <strong className="role-name">{tr("role.admin")}</strong>
                <span className="role-line">{tr("landing.admin_hint")}</span>
              </span>
              <Icon name="chevron" size={24} className="l-go" />
            </button>
          </div>
          <InstallEntry variant="card" />
        </>
      )}
    </section>
  );
}
