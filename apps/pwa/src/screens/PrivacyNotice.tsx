// The privacy notice (India's DPDP Act, 2023): what we collect and why, where it lives, how long, who sees it,
// her rights and how to use them, and who to write to. In her language. The same text is in docs/privacy.md.
import { Icon } from "../components/icons";
import { href } from "../lib/router";
import { useApp } from "../state";

const ROWS = ["answers", "counts", "rehearsal", "voice", "feedback", "consent"] as const;

export default function PrivacyNotice() {
  const { tr } = useApp();
  return (
    <section aria-labelledby="pn-title" data-testid="privacy-notice">
      <h1 id="pn-title">
        <Icon name="shield" /> {tr("notice.title")}
      </h1>
      <p>{tr("notice.intro")}</p>
      <h2>{tr("notice.what")}</h2>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>{tr("notice.col_data")}</th>
              <th>{tr("notice.col_why")}</th>
              <th>{tr("notice.col_where")}</th>
              <th>{tr("notice.col_keep")}</th>
            </tr>
          </thead>
          <tbody>
            {ROWS.map((r) => (
              <tr key={r}>
                <th>{tr(`notice.${r}` as "notice.answers")}</th>
                <td>{tr(`notice.${r}_why` as "notice.answers_why")}</td>
                <td>{tr(`notice.${r}_where` as "notice.answers_where")}</td>
                <td>{tr(`notice.${r}_keep` as "notice.answers_keep")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h2>{tr("notice.children")}</h2>
      <p>{tr("notice.children_body")}</p>
      <h2>{tr("notice.processors")}</h2>
      <p>{tr("notice.processors_body")}</p>
      <h2>{tr("notice.rights")}</h2>
      <ul className="plain">
        {(["access", "correct", "erase", "withdraw", "grievance", "nominate"] as const).map((k) => (
          <li key={k}>
            <strong>{tr(`notice.r_${k}` as "notice.r_access")}</strong> {tr(`notice.r_${k}_how` as "notice.r_access_how")}
          </li>
        ))}
      </ul>
      <h2>{tr("notice.contact")}</h2>
      <p data-testid="grievance">{tr("notice.contact_body")}</p>
      <p className="muted">{tr("notice.review")}</p>
      <a className="btn btn-primary btn-with-icon" href={href("/profile")} data-testid="notice-to-profile">
        <Icon name="profile" /> <span>{tr("notice.choose")}</span>
      </a>
    </section>
  );
}
