// What a teacher sees under her mistakes table about cohorts. She no longer creates one (a coach does, on the
// Coach screen, from the classes that entered checks); a one-class cohort she made earlier still shows. Below
// it, the other teachers whose classes show the same mistakes (nickname and class name, no counts).
import { useEffect, useState } from "react";
import type { Key } from "../i18n";
import { forCheck, syncPending, type ClassCohort } from "../lib/classCohort";
import { peersFor, type Peer } from "../lib/cloudStore";
import { href } from "../lib/router";
import { buildAnswerMap } from "../lib/results";
import { useApp } from "../state";

export function ClassCohortMaker({ onlyConfirmed }: { onlyConfirmed: boolean }) {
  const { tr, lang, profile, check, online, role } = useApp();
  const checkId = check?.id ?? profile?.id ?? "";
  const [made, setMade] = useState<ClassCohort | null>(() => (checkId ? forCheck(checkId) : null));
  // The errors to choose from: those children show (confirmed), and, unless the box above the table asks for
  // confirmed ones only, those seen on one question so far (possible), with their own counts.
  const map = check && profile ? buildAnswerMap(check.formKey, check.children, check.absent ?? [], check.approved) : null;
  const possibleOf = (code: string) => (onlyConfirmed ? 0 : (map?.legend.find((l) => l.code === code)?.possible ?? 0));
  const confirmed = profile ? Object.entries(profile.counts).filter(([, n]) => n > 0) : [];
  const extra = onlyConfirmed || !map ? [] : map.legend.filter((l) => l.possible > 0 && !confirmed.some(([c]) => c === l.code)).map((l) => [l.code, 0] as [string, number]);
  const found = [...confirmed, ...extra].sort((a, b) => b[1] - a[1] || possibleOf(b[0]) - possibleOf(a[0]));
  const [peers, setPeers] = useState<Peer[]>([]); // other teachers whose classes show the same mistakes

  useEffect(() => {
    setMade(checkId ? forCheck(checkId) : null);
  }, [checkId]);
  useEffect(() => {
    if (online) void syncPending(lang).then(() => setMade(checkId ? forCheck(checkId) : null));
  }, [online, lang, checkId]);

  const codes = found.map(([c]) => c).join(",");
  useEffect(() => {
    if (!online || !codes) return setPeers([]);
    void peersFor(codes.split(",")).then(setPeers);
  }, [online, codes]);

  if ((role !== "teacher" && role !== "judge") || !profile || found.length === 0) return null;
  if (made) {
    return (
      <section className="card stack" data-testid="class-cohort-made" aria-labelledby="cc-made">
        <h2 id="cc-made">{tr("cohort.mine.section")}</h2>
        <p>
          <strong>{made.name}</strong>
        </p>
        <p>
          <span className="chip" data-testid="class-cohort-label">
            {tr("cohort.mine.label")}
          </span>
        </p>
        <p>{tr("cohort.mine.errors_line", { names: made.errors.map((c) => tr(`err.${c}` as Key)).join("; ") })}</p>
        {!made.synced ? <p className="muted">{tr("cohort.mine.saved_here")}</p> : <p className="muted">{tr("cohort.mine.created")}</p>}
        <a className="btn btn-primary" href={href("/cohort")} data-testid="to-class-cohort">
          {tr("pack.title")}
        </a>
      </section>
    );
  }
  if (peers.length === 0) return null; // nothing to say until another teacher's class shows the same mistake
  return (
    <section className="card stack" data-testid="class-cohort-start">
      <p data-testid="class-cohort-peers">{tr("cohort.mine.peers", { names: peers.map((p) => (p.class ? `${p.teacher} (${p.class})` : p.teacher)).join("; ") })}</p>
    </section>
  );
}
