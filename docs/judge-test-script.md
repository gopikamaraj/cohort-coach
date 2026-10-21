# Judge test script (v3.1, 21 Oct 2026)

The final English script is written in P12 from this table. It is the written form of the guided tour in `docs/design/addendum-v3.1.md` §B (about 5 minutes on a laptop). Each phase updates the "Status" column as its step is built, so the script is never written from memory at the end.

Start at the landing page (`#/roles`) and press **Guided tour (5 min)**, or open a step directly.

| Step | Deep link | Role | Time | What the judge does | What to notice | Built in | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | `#/roles` | any | 15 s | Open the web app: judge mode, no login; pick a language; read a role card and its scope dialog | Who holds each role in the field; what each role cannot do | P08 | built (`e2e/landing.spec.ts`) |
| 1 | `#/tour/1` | Teacher | 45 s | "Use sample sheets" → reading → confirm one unsure box → error card with counts by stage | Guardrails: she confirms the unsure reads; counts only; "simulated" | P08 | built: sample sheets, stage lines (`e2e/stages.spec.ts`) |
| 2 | `#/tour/2` | Officer | 20 s | Approve a proposed cohort | Guardrails: a human gate; nothing auto-approves | P12 | pending |
| 3 | `#/tour/3` | Coach | 30 s | Approve a mentor recording; open the content library | The loop: next cohort's content comes from a teacher, approved by a person | P11, P12 | pending |
| 4 | `#/tour/4` | Teacher | 2 min | Press "Hear it done well"; watch an experienced and a struggling run, side by side; then try with hints; switch on "Show the machinery" | AI use in layers: what code decided, which AI call ran, which validators passed | P06, P07, P08 | built: Watch (two styles, recorded runs), hints, machinery panel; the model run arrives in P09 |
| 5 | `#/tour/5` | Officer | 45 s | "Advance to Term 2"; read the funnel and the track verdicts; read the stage mix | Evaluation: honest statistics and source labels; a failed track counts against the track | P12 | pending |
| 6 | `#/tour/6` | Teacher | 30 s | Open the AI map and the audit trail; press "Try to break it" chips | Ten calls, five layers; adversarial lines stopped, with the reason | P06, P08 | built: AI map, audit trail, Try to break it |
| Extra | | Teacher | | Run the same teacher flow in Telegram with `/start judge` | One back end, two channels | P05, P10 | Telegram onboarding and T1 built; check and lessons pending |
