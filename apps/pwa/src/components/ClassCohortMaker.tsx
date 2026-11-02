// "Create a cohort for my class": choose which of this class's errors to work on (the most common one
// is chosen for her), name it, and confirm. It makes a cohort of one class, labelled everywhere
// "Just my class: no other teachers yet". Counts only are saved.
import { useEffect, useState } from "react";
import type { Key } from "../i18n";
import { create, forCheck, syncPending, type ClassCohort } from "../lib/classCohort";
import { peersFor, type Peer } from "../lib/cloudStore";
import { CohortError } from "../lib/cohort";
import { href } from "../lib/router";
import { shownClassName } from "../lib/checks";
import { buildAnswerMap } from "../lib/results";
import { useApp } from "../state";

export function ClassCohortMaker({ onlyConfirmed }: { onlyConfirmed: boolean }) {
  const { tr, lang, profile, check, klass, online, role } = useApp();
  const checkId = check?.id ?? profile?.id ?? "";
  const [made, setMade] = useState<ClassCohort | null>(() => (checkId ? forCheck(checkId) : null));
  const [open, setOpen] = useState(false);
  // The errors to choose from: those children show (confirmed), and, unless the box above the table asks for
  // confirmed ones only, those seen on one question so far (possible), with their own counts.
  const map = check && profile ? buildAnswerMap(check.formKey, check.children, check.absent ?? [], check.approved) : null;
  const possibleOf = (code: string) => (onlyConfirmed ? 0 : (map?.legend.find((l) => l.code === code)?.possible ?? 0));
  const confirmed = profile ? Object.entries(profile.counts).filter(([, n]) => n > 0) : [];
  const extra = onlyConfirmed || !map ? [] : map.legend.filter((l) => l.possible > 0 && !confirmed.some(([c]) => c === l.code)).map((l) => [l.code, 0] as [string, number]);
  const found = [...confirmed, ...extra].sort((a, b) => b[1] - a[1] || possibleOf(b[0]) - possibleOf(a[0]));
  const [picked, setPicked] = useState<string[]>([]);
  const [name, setName] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
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
  const nameFor = (codes: string[]) =>
    tr("cohort.mine.name_default", { class: shownClassName(tr, klass), error: codes[0] ? tr(`err.${codes[0]}` as Key) : "" });
  const start = () => {
    const first = found.slice(0, 1).map(([c]) => c);
    setPicked(first);
    setName(nameFor(first));
    setMsg("");
    setOpen(true);
  };
  const toggle = (code: string) => setPicked((p) => (p.includes(code) ? p.filter((x) => x !== code) : [...p, code]));

  async function submit() {
    if (picked.length === 0) {
      setMsg(tr("cohort.mine.need_one"));
      return;
    }
    setBusy(true);
    try {
      const row = await create({ checkId, name, errors: found.map(([c]) => c).filter((c) => picked.includes(c)), counts: profile?.counts ?? {}, childrenChecked: profile?.childrenChecked ?? 0, simulated: Boolean(profile?.simulated), language: lang }, online);
      setMade(row);
      setOpen(false);
    } catch (e) {
      setMsg(e instanceof CohortError ? tr("cohort.mine.error") : tr("cohort.mine.error"));
    } finally {
      setBusy(false);
    }
  }

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
  if (!open) {
    return (
      <section className="card stack" data-testid="class-cohort-start">
        <button type="button" className="btn btn-primary" onClick={start} data-testid="class-cohort-open">
          {tr("cohort.mine.cta")}
        </button>
        {peers.length > 0 ? (
          <p data-testid="class-cohort-peers">{tr("cohort.mine.peers", { names: peers.map((p) => (p.class ? `${p.teacher} (${p.class})` : p.teacher)).join("; ") })}</p>
        ) : (
          <p className="muted">{tr("cohort.mine.label")}</p>
        )}
      </section>
    );
  }
  return (
    <form
      className="card stack"
      data-testid="class-cohort-form"
      aria-labelledby="cc-form"
      onSubmit={(e) => {
        e.preventDefault();
        void submit();
      }}
    >
      <h2 id="cc-form">{tr("cohort.mine.form_title")}</h2>
      <p className="chip">{tr("cohort.mine.label")}</p>
      <fieldset className="stack">
        <legend>{tr("cohort.mine.pick")}</legend>
        {found.map(([code, n]) => (
          <label key={code} className="check-line">
            <input type="checkbox" checked={picked.includes(code)} onChange={() => toggle(code)} data-testid={`pick-${code}`} />{" "}
            {tr("cohort.mine.pick_line", { name: tr(`err.${code}` as Key), n, total: profile.childrenChecked })}
            {possibleOf(code) > 0 ? ` · ${tr("results.map.legend_possible", { n: possibleOf(code) })}` : ""}
          </label>
        ))}
      </fieldset>
      <label>
        {tr("cohort.mine.name")}
        <input type="text" value={name} maxLength={80} onChange={(e) => setName(e.target.value)} data-testid="class-cohort-name" />
      </label>
      <p className="muted">{tr("cohort.mine.counts_only")}</p>
      {msg ? (
        <p role="alert" data-testid="class-cohort-msg">
          {msg}
        </p>
      ) : null}
      <div className="row">
        <button type="submit" className="btn btn-primary" disabled={busy || name.trim() === ""} data-testid="class-cohort-create">
          {tr("cohort.mine.create")}
        </button>
        <button type="button" className="btn btn-secondary" onClick={() => setOpen(false)}>
          {tr("cohort.mine.cancel")}
        </button>
      </div>
    </form>
  );
}
