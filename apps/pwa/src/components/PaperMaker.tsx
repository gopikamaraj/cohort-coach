// Make a paper for a check (inside Start a check). Every paper is made by code from the approved
// rules and the class profile: the last check's counts when there is one, else the short intake form
// she fills in the first time (or the standard paper if she skips it). She picks the language and the
// server builds the paper; a pre-test's post-test twin is made with it. The demo makes its paper the
// same way, and keeps its id for the steps that follow.
import { useState } from "react";
import type { Key } from "../i18n";
import { activeClass, type CheckKind, type ProfileRow } from "../lib/db";
import { LANGS, layoutOf, pcall, PaperError, pastUsable, profileFrom, SKILLS, type Lang, type Paper, type ProfileSpec, type Skill } from "../lib/papers";
import { Busy } from "./Busy";
import { useApp } from "../state";
import { PaperView } from "./PaperView";

export function shortClass(name: string): string {
  const s = name.replace(/\(.*?\)/g, "").replace(/^class\s+/i, "").trim();
  return (s || "class").slice(0, 12);
}

export function PaperMaker({
  checkId,
  className,
  term,
  kind,
  form,
  latest,
  onMade,
}: {
  checkId: string | null; // null on a fresh phone: the class is made when she makes a paper
  className: string;
  term: number;
  kind: CheckKind;
  form: string;
  latest: ProfileRow | null;
  onMade?: (paper: Paper) => void;
}) {
  const { tr, lang, reload } = useApp();
  const [first, setFirst] = useState<Lang>((LANGS as string[]).includes(lang) ? (lang as Lang) : "en");
  const [second, setSecond] = useState<Lang | "">("");
  const layout = layoutOf(first, second);
  // With no past check there is nothing to build the paper from yet: ask about the class up front.
  const [intakeOpen, setIntakeOpen] = useState(!pastUsable(latest));
  const [intake, setIntake] = useState<ProfileSpec | null>(null);
  const [struggles, setStruggles] = useState<Skill[]>([]);
  const [taught, setTaught] = useState<Skill[]>(["C1", "C2", "C3"]);
  const [strength, setStrength] = useState("");
  const [similar, setSimilar] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [made, setMade] = useState<{ paper: Paper; twin: Paper | null } | null>(null);

  const profile = profileFrom(latest, intake);
  const toggle = (list: Skill[], s: Skill) => (list.includes(s) ? list.filter((x) => x !== s) : [...list, s]);

  function saveIntake() {
    setIntake({ source: "intake", struggles, taught, strength: /^\d+$/.test(strength) ? Number(strength) : null, similar_test: similar });
    setIntakeOpen(false);
  }

  async function make() {
    setBusy(true);
    setMsg("");
    try {
      let id = checkId;
      if (id === null) {
        id = `${(await activeClass(false)).id}:${term}`;
        await reload(); // every screen now knows the class
      }
      const body = {
        check: { id, kind, form, class_label: shortClass(className), term },
        profile: { ...profile, language: layout },
        blueprint: "standard_10_5",
        language: layout,
      };
      const out = await pcall<{ paper: Paper; twin: Paper | null }>("/api/papers/generate", "teacher", { method: "POST", body });
      setMade(out);
      if (localStorage.getItem("cc.demo.session")) {
        localStorage.setItem("cc.demo.paper", out.paper.id);
        localStorage.setItem("cc.demo.paper.code", out.paper.check_code);
      }
      onMade?.(out.paper);
    } catch (e) {
      if (e instanceof PaperError && e.status === 422) setMsg(tr("papers.cannot", { why: e.explanation || e.rule }));
      else if (e instanceof PaperError && e.status === 409) setMsg(tr("papers.conflict", { why: e.explanation }));
      else if (e instanceof PaperError && e.status === 403) setMsg(tr("papers.forbidden"));
      else setMsg(tr("papers.error"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="stack" aria-label={tr("papers.make_title")} data-testid="paper-maker">
      <p data-testid="paper-profile-source">
        {tr(`papers.source_${profile.source}` as Key)}
        {profile.source === "past" ? ` · ${tr("papers.past_detail", { n: profile.checked ?? 0 })}` : ""}
      </p>
      {latest && latest.childrenChecked > 0 && !pastUsable(latest) ? (
        <p className="muted" data-testid="past-too-few">
          {tr("papers.past_too_few", { n: latest.childrenChecked })}
        </p>
      ) : null}
      {profile.source === "baseline" && !intakeOpen ? <p className="muted">{tr("papers.no_data_note")}</p> : null}
      {profile.source !== "past" && !intakeOpen ? (
        <button type="button" className="btn btn-secondary" onClick={() => setIntakeOpen(true)} data-testid="intake-open">
          {intake ? tr("papers.intake_edit") : tr("papers.intake_open")}
        </button>
      ) : null}
      {intakeOpen ? (
        <fieldset className="stack card" data-testid="intake-form">
          <legend>{tr("papers.intake_title")}</legend>
          <p className="muted">{tr("papers.no_data_note")}</p>
          <p>{tr("papers.intake_struggles")}</p>
          {SKILLS.map((s) => (
            <label key={`s-${s}`} className="choice">
              <input type="checkbox" checked={struggles.includes(s)} onChange={() => setStruggles(toggle(struggles, s))} data-testid={`intake-struggle-${s}`} />
              <span>{tr(`papers.skill.${s}` as Key)}</span>
            </label>
          ))}
          <p>{tr("papers.intake_taught")}</p>
          {SKILLS.map((s) => (
            <label key={`t-${s}`} className="choice">
              <input type="checkbox" checked={taught.includes(s)} onChange={() => setTaught(toggle(taught, s))} data-testid={`intake-taught-${s}`} />
              <span>{tr(`papers.skill.${s}` as Key)}</span>
            </label>
          ))}
          <label className="field">
            <span>{tr("papers.intake_strength")}</span>
            <input inputMode="numeric" maxLength={3} value={strength} onChange={(e) => setStrength(e.target.value.replace(/\D/g, ""))} data-testid="intake-strength" />
          </label>
          <p>{tr("papers.intake_similar")}</p>
          <div className="row">
            <label className="choice">
              <input type="radio" name="intake-similar" checked={similar === true} onChange={() => setSimilar(true)} />
              <span>{tr("papers.yes")}</span>
            </label>
            <label className="choice">
              <input type="radio" name="intake-similar" checked={similar === false} onChange={() => setSimilar(false)} />
              <span>{tr("papers.no")}</span>
            </label>
          </div>
          <button type="button" className="btn btn-secondary" onClick={saveIntake} data-testid="intake-save">
            {tr("papers.intake_save")}
          </button>
        </fieldset>
      ) : null}
      <div className="row">
        <label className="field">
          <span>{tr("papers.language")}</span>
          <select
            value={first}
            onChange={(e) => {
              const v = e.target.value as Lang;
              setFirst(v);
              if (second === v) setSecond("");
            }}
            data-testid="paper-language"
          >
            {LANGS.map((l) => (
              <option key={l} value={l}>
                {tr(`papers.lang.${l}` as Key)}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>{tr("papers.language2")}</span>
          <select value={second} onChange={(e) => setSecond(e.target.value as Lang | "")} data-testid="paper-language-2">
            <option value="">{tr("papers.language2_none")}</option>
            {LANGS.filter((l) => l !== first).map((l) => (
              <option key={l} value={l}>
                {tr(`papers.lang.${l}` as Key)}
              </option>
            ))}
          </select>
        </label>
      </div>
      <p className="muted">{tr("papers.language_note")}</p>
      <button type="button" className="btn btn-primary" disabled={busy} onClick={() => void make()} data-testid="paper-make">
        {busy ? tr("papers.making") : tr("papers.make")}
      </button>
      {busy ? <Busy text={tr("papers.making_detail")} testId="paper-busy" /> : null}
      {msg ? (
        <p role="alert" data-testid="paper-msg">
          {msg}
        </p>
      ) : null}
      {made ? (
        <>
          <PaperView paper={made.paper} role="teacher" />
          {made.twin ? (
            <p role="status" data-testid="paper-twin-note">
              {tr("papers.twin_made")}
            </p>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
