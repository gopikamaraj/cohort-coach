# Addendum v3.1 (21 Oct 2026): roles, tour, demo modes, content library, strategies, stages

Specification for the changes agreed on 21 Oct. It sits after the design doc in the source-of-truth order (`CLAUDE.md` §2) and before `DECISIONS.md`, which wins on conflict. Build tasks are in `BUILD_PROMPTS.md` (blocks headed "Added 21 Oct"); decisions are in `DECISIONS.md` (21 Oct entries and OD-18 to OD-25).

Nothing here is built yet. Where a change is aimed at a phase that is already done, its tasks sit in the next open phase (P08) and say which earlier phase they extend.

| Section | Change | Tasks live in |
| --- | --- | --- |
| A | Landing page, role cards, scope dialog, role switcher | P08 (shell and config), P11 (mentor, coach), P12 (officer, production roles) |
| B | Guided tour (6 steps, judge mode) | P12 |
| C | Practice Class demo modes, call 10, recorded runs, eval 11 | P08 (build), P13 (eval 11) |
| D | Content library for coach and officer | P09 (versions and gates), P12 (screens) |
| E | Teaching strategies and the no-check-items validator | P08 (data, validator), P09 (track content) |
| F | Stage of breakdown | P08 (engine, simulator, error card), P09 (routines), P12 (officer view) |
| G | Synthetic sheets for the stages | P08 |

---

## A. Landing page and roles

### The landing page

Four role cards and one tour card. In demo and judge mode every card is selectable; in production only the roles the signed-in person holds appear (see "Production").

| Card | Who holds it in the field | One line on what they do |
| --- | --- | --- |
| Teacher | A Grade 3 teacher | Checks her class, rehearses the fix in the Practice Class, follows a 3-week track. |
| Mentor | A teacher whose class fixed the same error | Records how she fixed it so the next cohort can learn it. |
| Coach | A BRC, CRC, DIET faculty member or head teacher | Approves recordings and lessons, and keeps the cohort chat safe. |
| Programme officer | Block or district programme staff | Approves cohorts and reads results across the block. |
| Guided tour (5 min) | Marked "Start here if you're judging" | Walks all four roles in six steps (section B). |

One person may hold coach and officer (`CLAUDE.md` §5); the landing page then shows both cards.

### The scope dialog

Picking a role opens a dialog before the dashboard. It has five blocks and three buttons.

| Block | Content |
| --- | --- |
| You can | What the role does here, as short lines |
| You can't | The boundaries, as short lines |
| Data you'll see | What is shown; in demo it says "simulated" |
| Also on | "Telegram" for teacher and mentor; nothing for coach and officer (web only) |
| Weekly time | The role's cap: teacher 20 min, mentor 30, coach 30. Officer: "one weekly batch; no minute cap set yet" (OD-25) |

Buttons: **Enter dashboard**, **60-second walk-through** (the role's slice of the tour, section B), **Back**.

Starting content for the "You can't" lines (final wording is copy in `strings/`):

| Role | You can't (boundary) |
| --- | --- |
| Teacher | See any class but your own. Be scored: the AI never scores a teacher. |
| Mentor | See cohorts you are not mentoring. See any teacher's class numbers. |
| Coach | Act on a cohort you are not assigned to. See a number about one teacher's class. |
| Programme officer | See a teacher's class: aggregates only, and nothing covering fewer than 5 classes. Approve content (the coach does that). |

### One config, enforced and displayed

The dialog text is not written separately from the rules. One file, `services/api/roles/permissions.yaml`, lists per role:

- `can`: permission ids, each with a string key for its dialog line;
- `cannot`: boundary ids, each with a string key;
- `data`, `also_on`, `weekly_minutes`, `field_holders` (string keys).

The server enforces `can` ids through a single `require("<id>")` guard on every route and flow step. `cannot` ids are negative guarantees, each enforced by a named check (a denied route, a query that returns nothing, or a suppression rule). `GET /api/roles` returns the config and the dialog renders from it, so there is no second copy to drift.

Tests (first):

- every `can` id is used by at least one `require()` call, and every `require()` id appears in `can` of some role (both directions);
- every `cannot` id names a test that proves the denial (403, empty result or suppression), and a test that finds no `cannot` id without one;
- every dialog string key exists in `en`, `hi` and `ta`;
- the dialog shows no percentage to a teacher or mentor, and the officer lines never offer a per-teacher view.

### Dashboards by role

| Role | Dashboard |
| --- | --- |
| Teacher | T1 home; check with a "Use sample sheets" button (judge mode); error cards; the track; Practice Class; results; cohort chat |
| Mentor | Cohort dropdown; recordings and their statuses; link to the cohort chat |
| Coach | Cohort table; approval queue; content library (section D); moderation |
| Programme officer | Error map; cohort approval; funnel; track results; "Advance to Term 2" (judge mode); role assignment; content library |

These reuse the P11 and P12 screens; the landing page and the dialog are the only new surfaces.

### Behaviour

- **Demo and judge mode.** Every role is selectable. A role switcher stays in the header. The dialog shows the first time a role is entered in that browser (a flag in `localStorage`, no server state).
- **Production.** The landing page lists only the roles recorded for her pseudonymous id (assigned by the officer, with her consent, in the role-assignment screen; no passwords). A single-role person goes straight to the dashboard and sees the dialog once.
- **Layout.** Teacher and mentor dashboards render inside a phone frame at 768 px and wider (both are phone-first and also run in Telegram). Coach and officer use the full width.
- **Deep links.** `#/roles` (landing), `#/role/<teacher|mentor|coach|officer>` (dashboard), `#/role/<role>/walkthrough`, and `#/tour/<1-6>` (section B). The hash router already serves deep links offline.

### What changes elsewhere

- `BUILD_PROMPTS.md` P05 step 6 (J1 judge mode) is superseded by this section and section B; the "role switcher" item there becomes the header switcher.
- `CLAUDE.md` §3 (demo link) mentions the landing page; §6 lists `services/api/roles/`.
- Rule 3 is untouched: the officer card says "aggregates only", and a test enforces it.

---

## B. Guided tour (judge mode)

Six steps, about 5 minutes on a laptop. A progress bar runs along the top; each step shows a **What to notice** line that names the judging criterion. The tour switches roles as it goes, with a short banner such as "Now you're the coach". Every step has **Skip** and **Back**. The tour can be left and resumed from its deep link `#/tour/<n>`; progress is the step number in the URL, kept in `localStorage`, with no server state.

| # | Step | Role | Time | What happens | What to notice (criterion) |
| --- | --- | --- | --- | --- | --- |
| 1 | Check | Teacher | 45 s | "Use sample sheets" → reading → one confirm → error card with counts by stage; "simulated" label | Guardrails: she confirms the unsure reads; counts only; no child data kept |
| 2 | Cohort | Officer | 20 s | Approve a proposed cohort | Guardrails: a human gate; nothing auto-approves |
| 3 | Content | Coach | 30 s | Approve a mentor recording; the content library then lists the approved strategy | Guardrails and the loop: the next cohort's content comes from a teacher, approved by a person |
| 4 | Practice Class | Teacher | 2 min | Watch two runs (experienced, struggling), then try with hints | AI use in layers: every turn shows what code decided and what the AI did |
| 5 | Term 2 | Officer | 45 s | "Advance to Term 2" → one track works, one does not; funnel with source labels; change in the stage mix | Evaluation: honest statistics, source labels, a failed track counts against the track |
| 6 | Under the hood | Teacher | 30 s | AI map, audit trail, "Try to break it" | AI use in layers and guardrails: ten calls, five layers, adversarial lines stopped |

Total 290 s. Step 4 is the only long one; its "Watch" mode runs from recorded runs unless live runs are available (section C).

Rules:

- Every step works on simulated data and says so (rule 6).
- Switching role goes through the same role config and scope dialog as the landing page, but the tour suppresses the dialog and shows the banner instead.
- The tour uses the same screens and API as the roles; there is no separate demo UI. Steps that need Term 2 data use "Advance to Term 2", which already computes verdicts at request time.
- Each role's "60-second walk-through" button (section A) is the tour step for that role, started from that step.
- `docs/judge-test-script.md` is the written version of this table and is kept in step with it.
