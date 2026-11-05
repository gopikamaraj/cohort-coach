// "Create a cohort for my class": choose which of this class's errors to work on (the most common one
// is chosen for her), name it, and confirm. One cohort per mistake (decided 2026-11-04): each mistake picked makes its own
// cohort of one class, labelled everywhere "Just my class: no other teachers yet", and the button comes back for any
// mistake that has none yet. Counts only are saved.
import { useEffect, useState } from "react";
import type { Key } from "../i18n";
import { allForCheck, create, syncPending, type ClassCohort } from "../lib/classCohort";
import { CohortError } from "../lib/cohort";
import { href } from "../lib/router";
import { shownClassName } from "../lib/checks";
import { buildAnswerMap } from "../lib/results";
import { useApp } from "../state";

export function ClassCohortMaker({ onlyConfirmed }: { onlyConfirmed: boolean }) {
  const { tr, lang, profile, check, klass, online, role } = useApp();
  const checkId = check?.id ?? profile?.id ?? "";
  const [made, setMade] = useState<ClassCohort[]>(() => (checkId ? allForCheck(checkId) : []));
  const [open, setOpen] = useState(false);
  // The errors to choose from: those children show (confirmed), and, unless the box above the table asks for
  // confirmed ones only, those seen on one question so far (possible), with their own counts.
  const map = check && profile ? buildAnswerMap(check.formKey, check.children, check.absent ?? [], check.approved) : null;
  const possibleOf = (code: string) => (onlyConfirmed ? 0 : (map?.legend.find((l) => l.code === code)?.possible ?? 0));
  const confirmed = profile ? Object.entries(profile.counts).filter(([, n]) => n > 0) : [];
  const extra = onlyConfirmed || !map ? [] : map.legend.filter((l) => l.possible > 0 && !confirmed.some(([c]) => c === l.code)).map((l) => [l.code, 0] as [string, number]);
  const everyFound = [...confirmed, ...extra].sort((a, b) => b[1] - a[1] || possibleOf(b[0]) - possibleOf(a[0]));
  const found = everyFound.filter(([c]) => !made.some((m) => m.errors.includes(c))); // the mistakes with no cohort yet
  const [picked, setPicked] = useState<string[]>([]);
  const [name, setName] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setMade(checkId ? allForCheck(checkId) : []);
  }, [checkId]);
  useEffect(() => {
    if (online) void syncPending(lang).then(() => setMade(checkId ? allForCheck(checkId) : []));
  }, [online, lang, checkId]);

  if ((role !== "teacher" && role !== "judge") || !profile || everyFound.length === 0) return null;
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
      const codes = found.map(([c]) => c).filter((c) => picked.includes(c));
      for (const code of codes) {
        // one cohort for each mistake picked; the typed name is for the first, the others are named after their own mistake
        await create({ checkId, name: code === codes[0] ? name : nameFor([code]), errors: [code], counts: { [code]: profile?.counts[code] ?? 0 }, childrenChecked: profile?.childrenChecked ?? 0, simulated: Boolean(profile?.simulated), language: lang }, online);
      }
      setMade(allForCheck(checkId));
      setOpen(false);
    } catch (e) {
      setMsg(e instanceof CohortError ? tr("cohort.mine.error") : tr("cohort.mine.error"));
    } finally {
      setBusy(false);
    }
  }

  const madeCards = made.map((m) => (
    <section key={m.id} className="card stack" data-testid="class-cohort-made" aria-labelledby={`cc-made-${m.id}`}>
      <h2 id={`cc-made-${m.id}`}>{tr("cohort.mine.section")}</h2>
      <p>
        <strong>{m.name}</strong>
      </p>
      <p>
        <span className="chip" data-testid="class-cohort-label">
          {tr("cohort.mine.label")}
        </span>
      </p>
      <p>{tr("cohort.mine.errors_line", { names: m.errors.map((c) => tr(`err.${c}` as Key)).join("; ") })}</p>
      {!m.synced ? <p className="muted">{tr("cohort.mine.saved_here")}</p> : <p className="muted">{tr("cohort.mine.created")}</p>}
      <a className="btn btn-primary" href={href("/cohort")} data-testid="to-class-cohort">
        {tr("pack.title")}
      </a>
    </section>
  ));
  if (!open || found.length === 0) {
    return (
      <>
        {madeCards}
        {found.length > 0 ? (
          <section className="card stack" data-testid="class-cohort-start">
            <button type="button" className="btn btn-primary" onClick={start} data-testid="class-cohort-open">
              {tr("cohort.mine.cta")}
            </button>
          </section>
        ) : null}
      </>
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
      <label className="cohort-name-field">
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
