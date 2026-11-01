// My programme: where she stands, step by step. Her check, her track, her cohort, her mentor, and where
// the lessons and the model-lesson script will appear. Counts only; nothing names another teacher.
import { useCallback, useEffect, useState } from "react";
import { API_BASE } from "../lib/api";
import { SimulatedBanner } from "../components/parts";
import { href } from "../lib/router";
import { useApp } from "../state";
import type { Key } from "../i18n";

interface Programme {
  simulated: boolean;
  placement: { status: "waiting" | "this_term" | "next_term"; track?: string };
  cohort: { size: number; mentor_slot: boolean; undersized: boolean } | null;
  mentor: { status: string };
  lessons: { status: string; items: { id: string; title: string; text?: string; audio?: string }[]; script: string | null };
}

type Step = { key: string; title: string; body: string; done: boolean };

export default function ProgrammeScreen() {
  const { tr, klass, profile, online } = useApp();
  const [data, setData] = useState<Programme | null>(null);
  const [failed, setFailed] = useState(false);

  const load = useCallback(async () => {
    if (!klass) return;
    setFailed(false);
    try {
      const track = profile?.track ? `?track=${encodeURIComponent(profile.track)}` : "";
      const res = await fetch(`${API_BASE}/api/programme/${klass.id}${track}`);
      if (!res.ok) throw new Error(String(res.status));
      setData((await res.json()) as Programme);
    } catch {
      setFailed(true);
    }
  }, [klass, profile?.track]);

  useEffect(() => {
    if (online) void load();
  }, [online, load]);

  const errorName = profile?.track ? tr(`err.${profile.track}` as Key) : null;
  const p = data?.placement.status;
  const cohortBody =
    p === "this_term" ? tr("prog.s3.this", { n: data?.cohort?.size ?? 0 }) : p === "next_term" ? tr("prog.s3.next") : tr("prog.s3.wait");
  const steps: Step[] = [
    { key: "check", title: tr("prog.s1"), done: Boolean(profile), body: profile ? tr("prog.s1.done", { n: profile.childrenChecked }) : tr("prog.s1.none") },
    { key: "track", title: tr("prog.s2"), done: Boolean(errorName), body: errorName ? errorName : tr("prog.s2.none") },
    { key: "cohort", title: tr("prog.s3"), done: p === "this_term" || p === "next_term", body: cohortBody },
    { key: "mentor", title: tr("prog.s4"), done: false, body: data?.cohort?.mentor_slot ? `${tr("prog.s4.has")} ${tr("prog.s4.later")}` : tr("prog.s4.later") },
    {
      key: "lessons",
      title: tr("prog.s5"),
      done: (data?.lessons.items.length ?? 0) > 0,
      body: (data?.lessons.items.length ?? 0) > 0 ? tr("prog.s5.some", { n: data?.lessons.items.length ?? 0 }) : tr("prog.s5.none"),
    },
  ];

  return (
    <section aria-labelledby="pg-title" data-testid="programme">
      <h1 id="pg-title">{tr("prog.title")}</h1>
      <p>
        <a className="btn btn-secondary" href={href("/cohort")} data-testid="to-cohort">
          {tr("cohort.title")}
        </a>
      </p>
      {data?.simulated || klass?.simulated ? (
        <>
          <SimulatedBanner />
          <p className="muted">{tr("prog.simulated_example")}</p>
        </>
      ) : null}
      {!online || failed ? (
        <p role="status" data-testid="prog-offline">
          {tr("prog.offline")}{" "}
          {online ? (
            <button type="button" className="btn btn-secondary" onClick={() => void load()}>
              {tr("prog.retry")}
            </button>
          ) : null}
        </p>
      ) : null}
      <ol className="steps prog">
        {steps.map((s) => (
          <li key={s.key} data-testid={`prog-${s.key}`} data-done={s.done ? "true" : "false"}>
            <strong>
              <span aria-hidden="true">{s.done ? "✓ " : "○ "}</span>
              {s.title}
            </strong>
            <span>{s.body}</span>
          </li>
        ))}
      </ol>
      {data && data.lessons.items.length > 0 ? (
        <ul className="plain" data-testid="prog-lessons">
          {data.lessons.items.map((l) => (
            <li key={l.id} className="card">
              <strong>{l.title}</strong>
              {l.text ? <p>{l.text}</p> : null}
              {l.audio ? <audio controls src={l.audio} /> : null}
            </li>
          ))}
        </ul>
      ) : null}
      <h2>{tr("prog.where")}</h2>
      <p>{tr("prog.where_body")}</p>
      {!profile ? (
        <a className="btn btn-primary" href={href("/check")}>
          {tr("home.action.check")}
        </a>
      ) : null}
    </section>
  );
}
