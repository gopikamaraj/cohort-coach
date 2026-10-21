# Decisions log

Newest first within each section. Every entry: date, decision, why, alternatives considered, who confirmed. A newer entry here overrides `CLAUDE.md`, the build prompts and the design doc; update `CLAUDE.md` in the same commit when a rule changes.

## Open decisions (defaults apply until someone changes them)

| ID | Question | Default | Needed by | Owner |
| --- | --- | --- | --- | --- |
| OD-1 | Licence for the public repo: MIT or Apache-2.0? | MIT (applied in P00) | P00 | Gopi |
| OD-2 | Reuse finguru code? Voice: **decided, no** (see 2026-10-16 entry). Telegram bot: paths not given | Build fresh | P00 (used in P07, P10) | Gopi |
| OD-3 | Hosting: API, database, storage, PWA | An always-on small API instance on a managed host (e.g. Render, Railway or Fly.io); managed Postgres (e.g. Neon or Supabase); S3-compatible storage (e.g. Cloudflare R2); static PWA hosting (e.g. Cloudflare Pages, Vercel or Netlify). No plan that sleeps during 1–10 Nov | P06 staging | Gopi |
| OD-4 | Accounts: who creates the Telegram bot and the Sarvam account (with voice cloning) | Gopi, both | P07, P10 | Gopi |
| OD-5 | Curriculum alignment for items and techniques | NCERT Grade 3 (the Delhi pilot); Tamil Nadu's Ennum Ezhuthum mapping goes in the roadmap | P04, P09 | Seema |
| OD-6 | Which language leads the demo video | Hindi teacher audio with one Tamil segment; English narration and burned-in English subtitles | P16 | Shivani |
| OD-7 | Voice-lesson languages in the prototype | Hindi and English required; Tamil if time (cut-list item 14) | P09 | Gopi |
| OD-8 | Demo mentor | Seema nominates a real primary teacher by 25 Oct with written consent; until then a consenting team member's recording, labelled as such | P11 | Seema |
| OD-9 | Answer-reading eval data | Seema or Shivani photograph the unmarked pilot Form A sheets; the header band (class code, roll number) is masked locally before any upload; Shivani hand-keys the truth | P08, P13 | Seema, Shivani |
| OD-10 | Backup if Week 2 slips | Apply the cut list in order; Gopi decides anything beyond it | Any | Gopi |
| OD-11 | How judges see the teacher flow | They run the real teacher flows in the PWA's judge mode on simulated data, and the same flows in Telegram with `/start judge` | P05 | Gopi |
| OD-12 | Time caps | Teacher ≤ 20 min a week, mentor ≤ 30, coach ≤ 30 (was reviewer ≤ 15; changed 20 Oct, see OD-15); revisit with round 4 data | P10 | Seema |
| OD-13 | Who holds the coach (reviewer) and officer roles in the pilot | Seema holds both; a DIET faculty member or head teacher takes one if they agree | P12 | Seema |
| OD-14 | Pilot roll numbers | Every child has a unique roll number in the register that won't change between tests; the teacher writes it on each sheet from the register (children write nothing at the top). Seema confirms with each school | Pre-test day | Seema |
| OD-15 | Who is the coach, and the 30-minute weekly cap | The coach is the reviewer role extended: a BRC, CRC, DIET faculty member or head teacher assigned per cohort by the programme officer; one person may be coach and officer; cap 30 minutes a week | P11 | Seema |
| OD-16 | Post-moderation or pre-moderation of the cohort thread | Post-moderation: posts are visible at once after the PII and pre-filter checks; a Report button holds a post until the coach decides | P11 | Gopi |
| OD-17 | Thread retention | Thread text deleted 30 days after the cohort closes and never later than 90 days after the last post or cancellation; voice 30 days after posting; held, hidden or rejected posts lose their body within 7 days of the decision; audit rows hold a closed field list with no free text | P11 | Gopi |
| OD-18 | Live demo-teacher runs in judge mode, with recorded runs as the fallback | Live runs while under the hourly cap and the budget; recorded runs (labelled, with date, model versions and seed) when a call fails, a turn takes over 8 s, or the cap is reached | P08 | Gopi |
| OD-19 | Live-run cap per hour in judge mode | Set from the cost per run measured in P04 (`docs/evidence/practice_session_live.json`) and recorded here before the public staging URL | P08 | Gopi |
| OD-20 | Order of the guided tour | Check first (teacher, officer, coach, teacher, officer, teacher), as in `docs/design/addendum-v3.1.md` §B | P12 | Gopi |
| OD-21 | The PV-REVERSE stage rule | Input (test) when confined to items 1–2; Output when computed answers are also reversed | P08 | Shivani |
| OD-22 | The stage-routine threshold and length | A stage affecting ≥ 25% of children checked (≥ 10 checked) adds a routine of ≤ 60 seconds to each lesson | P09 | Seema |
| OD-23 | Hindi terms for borrowing or regrouping, and for decomposition and compensation | English terms with `TODO-HUMAN(Shivani)` placeholders in content until confirmed | P08 | Shivani |
| OD-24 | Whether the state textbook teaches decomposition and compensation | Assume not; the library labels them "added strategies" until Shivani checks the textbook | P08 | Shivani |
| OD-25 | Programme officer weekly time cap | None set: the dialog says "one weekly batch; no minute cap set yet"; measure in round 4 and propose a cap (raising or adding a cap needs a human-confirmed entry) | P12 | Seema |

## Settled decisions

### 2026-10-22 · Addendum v3.1: how the first build differs from the spec
- **Decision:** (1) Stage of breakdown is computed **on the phone** from signature answers the engine writes into the answer keys, with a parity test against `engine/stages.py`; the per-child rows never leave the phone. `POST /api/stages` also exists (stateless, no storage, no logging, 300-child cap) for the bot's check flow in P08/P10 and is not called by the PWA. (2) The simulator's mishearing kinds (other operation, swapped digits, one digit off) are code in `engine/simulator.py`, not `content/personas/mishear.yaml` (the addendum lists simulator behaviour as not configurable). (3) The default seating of three core, one input-test and one output child applies to the two subtraction scenarios first (`stage_mix` in their scenario files); PV-HEARD and ADD-NOCARRY seat every child as core until Seema reviews the stage routines. (4) Sample sheets are made-up Form A rows in `content/demo/sample_sheets.v1.yaml`; they are the one file the no-check-items scan exempts. (5) Watch runs are played back on the client from a run the server returns whole; the live cap is `WATCH_LIVE_PER_HOUR` (default 6), measured at about USD 0.02 to 0.04 a run (OD-19 still open for Gopi to set). (6) Call 1 prompt v3 and the call 10 prompt are new versions; eval 2 and the labeller eval are re-run in P13. (7) Conflicts with the addendum text resolved here: the judge flag is server-side (JUDGE_MODE), the missed-teaching count is a class-level count, and the stage routines and officer stage view wait for P09 and P12.
- **Why:** (1) the existing privacy test says only counts leave the phone, and the rule must hold offline; (2) rule 14 and the addendum's own boundary; (3) limits churn in the recorded fixtures; (4) the validator must still catch real content; (5) a run is a plain transcript, and recorded runs keep the demo up inside the budget.
- **Alternatives rejected:** sending rows to the server for staging (breaks the counts-only test); a mishear file read by the engine (engine is pure, no I/O); seating stages in every scenario at once.
- **Confirmed by:** pending Gopi.

### 2026-10-21 · Stage of breakdown
- **Decision:** error cards add a stage of breakdown in teacher language, always "most likely": Input (teaching), Input (test), Core, Output. New signatures (CORE-OFF1, IN-OP, IN-OPND, IN-NEAR, OUT-REV, OUT-REC, NO-METHOD) are generated by code from each form's items and are disjoint from each other and from the correct answer (the designed PV-HEARD and PV-REVERSE overlap is the only exception). Confirm-step tags stay in memory with the per-sheet reads; only class counts per (error, stage) are stored. A stage reaching 25% of children checked (≥ 10 checked) adds a routine of ≤ 60 s to each lesson. The simulator gains persona stages and `spoken` and `written` answers. Spec: `docs/design/addendum-v3.1.md` §F; sheets: `docs/build/synthetic-sheets-stage-addendum.md`.
- **Why:** a count of one wrong method does not tell a teacher whether to reteach, re-read the question aloud or check the writing; a stage with a one-minute probe is the smallest next step. The wording stays honest about what final answers can show.
- **Alternatives rejected:** naming a cause as fact; showing a stage to a child; storing per-child stage or tags (breaks rule 2); an AI call to assign stages (it must be code, rule 1); a per-stage significance test in the officer view without adequate n.
- **Confirmed by:** Gopi.

### 2026-10-21 · Teaching strategies and the no-check-items validator
- **Decision:** decomposition and compensation become approved moves for SUB-SFL and SUB-NODEC; "check by adding back" is the Output routine (ADD-NOCARRY children check with bundles); an order probe "Is 2 − 6 the same as 6 − 2?" for SUB-SFL; two practice levels per track (without, then with regrouping). A validator blocks any lesson, practice set, script, model run, hint option or worked example that contains a Form A or Form B item (either order, either operation, plus the dictation numbers), at the content gate and in CI. We use the strategies, never the source worksheets' wording or items.
- **Why:** the strategies come from the team's own subtraction materials and give teachers alternatives to try; teaching with the check items would invalidate the next check.
- **Alternatives rejected:** copying the worksheets' items; trusting reviewers to spot a check item by eye; a one-off list of forbidden numbers (it is derived from the golden file instead, so it cannot drift).
- **Confirmed by:** Gopi.

### 2026-10-21 · Content library and its configuration boundary
- **Decision:** coach and officer get a content library. Configurable (versioned data): approved strategies and their order, scenario descriptions, persona seating mix, stage routines on or off, practice levels, and thresholds marked `configurable` with a safe range in code. Not configurable (code and files, changed by review): error functions, item generator, scoring, the two-item rule, signature and stage rules, simulator behaviour, validators, prompts, guardrails, and anything that computes a number users see. Two keys: the coach approves (gate 3), the officer switches it on for the block; every change makes a new track version and results stay per version. New topics are not created there.
- **Why:** coaches and officers need to see and steer content without being able to change anything that computes a number; the boundary is what makes the guardrails credible.
- **Alternatives rejected:** a free editor for prompts or rules; one key (approval and activation by the same person); creating new topic packs in the library now (parked, `docs/build/PARKING.md`).
- **Confirmed by:** Gopi.

### 2026-10-21 · Guided tour and Practice Class demo modes, with call 10
- **Decision:** a six-step, five-minute guided tour in judge mode (check, cohort, content, Practice Class, Term 2, under the hood) that switches roles as it goes. The Practice Class gains scenario picker, Watch (an AI teacher in an experienced or a struggling style, ending in the normal feedback card), Try with hints, Free, always-on subtitles (call 1 returns the scenario-language line and the English line), move tags, a confusion meter, a "Show the machinery" panel, speed controls and "Try to break it" chips. New **call 10, Demo teacher** (`MODEL_DEMO_TEACHER` → `claude-haiku-5-5`), judge mode only, labelled "AI playing the teacher (demo only)", with code validators and a template-line fallback; recorded runs (labelled, with date, model versions and seed) take over on a failed call or a turn over 8 s; live runs are capped per hour with a visible cost meter. New **eval 11**: 20 runs per style, 100% approved move ids, 0 numbers outside the allowed set, experienced beats struggling on the rubric in ≥ 18 of 20 pairs. Call 1 gets prompt v2; eval 2 re-runs.
- **Why:** a judge who does not teach cannot tell a strong rehearsal from a weak one by trying it; watching both, with the machinery visible, shows the AI layers and the guardrails in five minutes. Recorded runs keep the demo inside the budget and up during the judging window.
- **Alternatives rejected:** offering the demo teacher to real teachers (they hear the reviewed model run); live-only runs (cost and outage risk); a microphone-required demo; a score for the teacher (the eval's rubric coverage is internal and never shown); running call 7 on call 10 (the line never reaches a real teacher, the label and the judge-only rule replace it).
- **Confirmed by:** Gopi.

### 2026-10-21 · Landing page and roles
- **Decision:** the web app opens on a landing page with four role cards (Teacher, Mentor, Coach, Programme officer) and a "Guided tour (5 min)" card. Picking a role opens a scope dialog (You can, You can't, Data you'll see, Also on, weekly time cap) with Enter dashboard, 60-second walk-through and Back. The dialog is generated from `services/api/roles/permissions.yaml`, the same config the server enforces through one `require()` guard; a test asserts every "can" and "can't" line maps to an enforced permission, and the reverse. In demo and judge mode every role is selectable with a header switcher; in production only the roles recorded for her pseudonymous id appear (assigned by the officer with consent, no passwords). Teacher and mentor render in a phone frame on wide screens. Spec: `docs/design/addendum-v3.1.md` §A.
- **Why:** judges should see who holds each role in the field and what each role cannot do before they see any data; one config avoids a dialog that promises more or less than the server allows.
- **Alternatives rejected:** a hand-written dialog (it drifts); a separate demo UI per role; passwords or accounts (rule in section 14); a role cap for the officer invented now (OD-25).
- **Confirmed by:** Gopi.

### 2026-10-20 · P05 flow engine: re-entry, erasure, replay
- **Decision:** the home menu re-shows its status line whenever the flow is re-opened (`Node.reentry`). A replayed answer key returns the current step only, not the earlier auto messages. Deleting a teacher also deletes her consent history (keyed by her device ids), not just her record; `/stop` in Telegram asks first. Webhook send errors are swallowed so the bot token in the URL never reaches a log.
- **Why:** privacy review of P05 (erasure must be complete; token must not leak). Replay returns the current step because the earlier auto messages are not state.
- **Alternatives:** keep consent history as an audit record (rejected: erasure means erasure).
- **Confirmed by:** pending Gopi.

### 2026-10-20 · Cohort space, mentor pages, coach pages
- **Decision:** each cohort gets a small thread (a code-chosen weekly prompt, and replies from teachers, the mentor, the coach and the system), a mentor page set and a coach page set. The thread is relayed by the bot in Telegram and shown at `/cohort` in the PWA, so teachers on either channel see one conversation. Display names are chosen by the teacher; handles and phone numbers are never shown. Every post passes the PII validator (child names, roll numbers) and the call 7 pre-filter; moderation is after the fact with a Report button; a flagged post is held until the coach decides. AI never writes a post. Mentor recordings and method-card steps move draft → submitted → awaiting_coach → approved (or changes requested, or rejected) and are "in use" only once a published track version includes them; nothing a mentor records reaches a teacher before the coach approves it. Cohorts move proposed → active → closing → closed, each transition audited. The **coach** is the reviewer extended (assigned per cohort by the programme officer, 30-minute weekly cap; one person may be coach and officer). Thread text is deleted 30 days after the cohort closes (and in every case within 90 days of the last post or cancellation). The filter is best-effort and local; no thread text goes to Claude; joining is a separate consent; coaches and mentors see pseudonyms and cohort medians only. Built as P11 steps 7–16; P12 renames the reviewer role to coach and adds "Posts and replies" to the funnel as a system-labelled engagement count, never as adoption.
- **Why:** peers matter to how teachers pick up tools (36% of EdTech-using teachers find tools through peers: BaSE 57, EdTech users only; BaSE 67 is not in `docs/design/evidence-digest.md`, so it is not used); support posts are overloaded or vacant (FLN 58 for one State, FLN 59, 110; NITI 145, 147: see the digest for scope); and the institution cannot see what reaches teachers (G4): the approval queue and cohort status make it visible. These support the design; they do not show a moderated thread works, which the pilot tests.
- **Alternatives rejected:** a Telegram group per cohort (exposes handles and phone numbers); an unmoderated chat; AI answering in the thread (rule 1, rule 15).
- **Confirmed by:** Gopi for the design. Raising this role's weekly cap from 15 minutes (reviewer) to 30 (coach) is a cap change under rule 12: Gopi confirmed it in this entry; OD-15 stays with Seema for the pilot. This entry supersedes the wording in the "Roles, profile, backup" entry that the "officer" label is replaced by coach: the programme officer remains a separate role, and the coach is the reviewer extended.

### 2026-10-20 · Roles, profile, backup, multiple classes, consent, feedback and admin
- **Decision:** at Gopi's request: (1) roles are now **teacher, coach, mentor, admin** (plus **judge** for the demo); the old "officer" label is replaced by **coach** (a DIET-like person who holds the reviewer and programme-officer duties of `CLAUDE.md` section 5; one person may still hold both); the mentor is one of the teachers and sees the teacher screens as well. Each role has its own home and menu; the role switcher is a demo mechanism until real sign-in exists. (2) **My profile** holds classes (add, rename, switch, delete: several classes per teacher), storage (the app asks the browser for persistent storage and shows the answer), backup (export and restore a file, optionally sealed with a passphrase: AES-GCM, PBKDF2 200,000 iterations), **data used** (bytes of the app's own calls counted on the phone, a cost from a price per GB she types, and a Clear button), privacy and feedback. (3) **DPDP**: a notice in three languages, four consent switches all off by default (counts, AI in the Practice Class, sharing rehearsals, feedback), versioned consent records on the phone and on the server under a random device id, withdrawal in one tap, erase-everything (phone plus `DELETE /api/classes/{id}`), class counts and feedback sent only with consent. (4) **Feedback**: anonymous app, content, simulation and card-flag feedback stored in the `feedback` table (text up to 500 characters, refused if it holds a phone number, email or ID number); the **admin** page lists feedback and the teachers' simulation observations, filters them and marks them reviewed with a note. Admin endpoints need `ADMIN_KEY` when it is set; with it unset they are open (judge demo and local dev) and the page says so. (5) **UI**: an icon set, toasts, tiles and panels (`docs/ui-guidelines.md`); the card's speaker icon answers with a toast. Flags now go to the admin instead of staying on the phone.
- **Why:** teachers could not carry their work to a new phone, keep two sections, see what the app costs them, control what is shared, or tell the team what they think; the admin had nowhere to read it.
- **Constraints kept:** no per-child data or photo on the server; feedback and observations are anonymous; nothing is sent before the matching consent; counts only, no percentages; simulated data labelled.
- **Not done (listed in `docs/privacy.md`):** grievance contact, nominee and breach processes (placeholders), named admin accounts, server retention periods, a legal review. The Hindi and Tamil wording is a draft for native review.
- **Alternatives:** syncing backups to the server (rejected: children's answers); named accounts now (deferred: P05 identity work).
- **Confirmed by:** Gopi (request); details pending Gopi and legal review.

### 2026-10-20 · Responsive layout, "What I entered", "My programme", classroom observation
- **Decision:** at Gopi's request: (1) the phone frame is gone on wide screens; the app is a fluid column from 320 px up to a centred 1000 px, with a scrolling bottom menu, tested at 320, 360, 768 and 1280 px for sideways scrolling; (2) **What I entered** lists every check on the phone (children, how many came from a photo, class counts sent or waiting) and shows the answers on request; photos stay unstored, answers stay on the phone; (3) **My programme** (`GET /api/programme/{class_id}`) shows check, track, cohort, mentor and lessons status in counts only; a real class not yet placed is told "waiting"; a simulated class sees a labelled example placement from the simulated block; lessons and the model-lesson script show "none published yet" until the content pipeline (P09/P10) exists; a mentor invitation is said to follow the next check; (4) **Class observation**: after trying it in class she answers "were the children like the pretend ones" and picks what differed from six fixed choices; stored on the phone and sent as choices only (no free text, no class id) to `sim_observations`; the summary endpoint hides anything under 5 reports. The Practice Class sub-tabs were renamed so they no longer overwrite the bottom menu styles.
- **Why:** the teacher could not see her own inputs, her placement or how to feed back on the simulation. Rules 2, 3, 5, 11 hold: no per-child data leaves the phone, counts only, no percentages, self-report labelled.
- **Alternatives:** syncing history to the server (rejected: privacy); free-text observations (rejected: could carry names); a real cohort lookup for real classes (waits for P09/P10).
- **Confirmed by:** Gopi (request); details pending Gopi. Hindi and Tamil strings are drafts for native review.

### 2026-10-19 · Practice Class: review tab, her own impact tag, cue card, language follow-through
- **Decision:** at Gopi's request the Practice Class screen gained (1) a **Review** tab: every rehearsal is recorded in IndexedDB on the phone (turns with the move she used, language, seed, feedback card), listed newest first, replayed turn by turn, with the moves she used counted, and deletable one by one or all at once; (2) an **impact tag** she sets herself on a rehearsal (It helped, No difference, It did not help), shown as counts in the Review summary: it is her own private note on the phone, it is not a score, it is not sent anywhere, and nothing in the product reads it as a judgement of her (rules 3, 11); (3) a **cue card** ("What can I say?"): the move list's example lines in her language, with the example child's name swapped for one of her five children, plus four generic delivery tips (a move that silences children is never cued); (4) **language follow-through**: the session is created in the app's current language, the goal, tips, cues and feedback arrive in it, and if she changes language mid-rehearsal a banner offers a restart in the new language with the same children.
- **Why:** the teacher asked for ways to replay and improve, to mark whether practice helped, and to know what to say. All of it stays on her phone (rule 2, rule 3).
- **Constraints kept:** no AI computes anything here; counts only, no percentages; the cue lines and the four delivery tips are drafts for Seema to review (`TODO-HUMAN(Seema)`), and the Hindi and Tamil wording needs native review.
- **Alternatives:** syncing impact tags to the server for officers (rejected: private, and rule 3); cueing by AI at runtime (rejected: cost, latency, safety; the lines are reviewed content).
- **Confirmed by:** Gopi (request); build details pending Gopi.

### 2026-10-19 · Photo reading in the v1 Check page (first slice of P08)
- **Decision:** Gopi asked for a photo option in the Check page: the teacher photographs one child's sheet, call 8 reads it blind on the server, the boxes fill in, she checks and corrects them and goes to the next child. Built now in the v1 PWA as an interim slice of P08 (`POST /api/sheets/read`, `ai/calls/c08_answer_reading.py`, `docs/answer-reading.md`). The photo is held in server memory for the call only (never on disk or in logs, capped at 800 KB), is not stored on the phone, and the reads go back to the phone; nothing about them is stored on the server. Code judges the reads (confidence at least 0.8 and an answer the item recognises, else "check"); every box is still the teacher's to confirm. P08 replaces this with the two-channel check flow (queued photos, confirm steps, in-memory reads with a 30-minute TTL, Telegram message deletion) and the eval 9 accuracy run; until then no accuracy is claimed.
- **Why:** it is the biggest time-saver in the check and the user asked for it; it fits CLAUDE.md rule 2 (photos deleted right after reading, class counts only stored) and is listed in BUILD_PROMPTS P08.
- **Alternatives:** wait for P08 (rejected by Gopi); keep the reads on the server for the confirm step (deferred to P08: the teacher confirms on the phone here).
- **Confirmed by:** Gopi (request); the build details pending Gopi.

### 2026-10-19 · Kit v3 adopted; how it sits with the 16 and 17 Oct build entries
- **Decision:** the v3 kit (CLAUDE.md, BUILD_PROMPTS, DECISIONS, agents, evidence digest) is the spec from 19 Oct. Where a build entry conflicts, v3 wins: (1) "P05 PWA decisions" items 1 to 4 and 6 to 8 (on-device check entry with `checks`, `profiles` and `syncQueue` in Dexie, a phone-made class id, judge mode as a role strip) describe the v1 build and stay in force only as the interim typed fallback; the flow engine, adapters, one pseudonymous teacher id and photo checks replace them in P05 and P08, after which Dexie keeps only transcripts, the outbox and settings. (2) P05 is reopened for the v3 rewrite (its v1 code is the base). (3) P04 steps 11 (model-run renderer) and 12 (`mixed_level`) are done at the start of P06. (4) The build's Sarvam, P03 API and voice entries are unaffected; the build's Speech line in CLAUDE.md is kept. (5) `MODEL_POINTER` is registered in config and `.env.example` now; call 9 itself is built in P10. (6) README and `docs/practice-class.md` now say simulated practice is a hypothesis the pilot tests (rule 13).
- **Why:** the v3 entries are newer and Gopi confirmed them; the v1 code is not wrong, it is superseded.
- **Alternatives:** keep v1 as final (rejected: contradicts the two-channels decision); delete the v1 entries (rejected: history is kept).
- **Confirmed by:** pending Gopi (this reconciliation); the v3 entries it relies on were confirmed by Gopi on 19 Oct.

### 2026-10-19 · Two channels, one back end
- **Decision:** teacher and mentor flows run on both Telegram and the PWA. Each flow is defined once in a channel-neutral flow engine as steps (message, choice, photo batch, number grid, voice, media, link), and thin adapters render them per channel. A teacher has one pseudonymous id across channels and can use either or both. The Practice Class and the officer and reviewer screens stay web only. WhatsApp will be a third adapter. Privacy is the same on every channel: per-sheet reads in server memory only, photos deleted after reading, class counts stored.
- **Why:** some teachers live in Telegram, others prefer an app icon. One back end keeps rules, numbers and guardrails identical on every channel and turns WhatsApp into an adapter rather than a rebuild.
- **Cost control:** the PWA uses generic step components, not one screen per flow; a golden-transcript test runs every flow through every adapter; an import rule keeps logic out of channels. If behind, cut-list item 11 trims PWA web push and PWA voice reflections first.
- **Supersedes:** the "small web app" part of the Telegram-first entry and the judge-mode replay (OD-11).
- **Confirmed by:** Gopi.

### 2026-10-19 · Telegram-first teacher channel; small web app (superseded in part by "Two channels, one back end")
- **Decision:** every teacher and mentor flow runs in the bot: T1 Home, T2 check by photo with in-chat confirmation (typed fallback), T3 error cards, T4 track, T6 next term, M1–M2. The web app keeps the Practice Class (one stable link from the bot; it opens in the browser, or in the installed PWA if she added it; installing is optional), judge mode and the officer and reviewer screens. Per-sheet reads stay in server memory, keyed by sequence number with a 30-minute TTL, until confirmation; only class counts are stored; photos are deleted from our server and from the chat.
- **Why:** teachers already juggle several apps, and installing one more is the main adoption risk. Telegram queues messages offline on its own.
- **Alternatives:** the full PWA (install friction); Telegram only, with a voice-note Practice Class (loses the materials tray and the pacing).
- **Supersedes:** the PWA parts of design §Screens by role, and the "only her phone links a sheet to a child" mechanism (she still holds the roll order).
- **Confirmed by:** Gopi.

### 2026-10-19 · Changes from the Challenge 3 evidence review
- **Decision:** (1) reviewer and programme officer are roles that a BRC, CRC, DIET faculty member or head teacher can hold, each working from one weekly batch; nothing auto-approves. (2) A model run (audio of the move done well with the same simulated class, built from approved content and reviewed) plays before rehearsal. (3) An officer funnel, Delivered → Tried → Practised → Changed, with source labels; no completion figure alone. (4) Call 9, the reflection pointer: one approved next step after a voice reflection. (5) An optional CRC visit brief, opt-in, with no numbers. (6) Time caps. (7) A mixed-level persona flag.
- **Why:** support posts are overloaded or vacant (FLN 58, 59, 110; NITI 145, 147); training rarely demonstrates or lets teachers practise (FLN 56; NITI 147); monitoring tracks inputs (FLN 54, 72, 73); classroom feedback is rare (AIC 74; NITI 147, 148); teacher time is scarce (FLN 25, 27; NITI 146, 185); most schools are multigrade (FLN 35; NITI 139, 150). Sources: `docs/design/evidence-digest.md`.
- **Rejected:** recording real lessons for AI feedback (one 50-teacher pilot where 68% were comfortable recording, AIC 75; children's voices would enter the data); video exemplars (data cost); grouping by teacher age or experience (the BaSE splits are about EdTech adoption; IDR 3 is anecdote); teacher-chosen courses or credits (opinion only, IDR 4–6); CRCs as coaches; admin automation (off-challenge).
- **Bets where sources disagree:** training alone doesn't change practice (FLN 136, 140), but practice plus feedback plus follow-through might (FLN 64; AIC 39, 75), and the next check decides. The problem is too much of the wrong training, so tracks are targeted and capped. We attack quality and sidestep access with teachers' own phones (BaSE 53, 56). Simulated practice is untested in every source and is presented as a hypothesis.
- **Confirmed by:** Gopi.

### 2026-10-19 · Pilot sheets reach Seema as photos
- **Decision:** Seema doesn't meet teachers. Each class teacher runs the test from a one-page teacher guide (dictation numbers inside, no answer key), photographs every sheet in roll-number order and sends the photos to Seema on WhatsApp or email, with the class code, date, children present, minutes taken and dictation language. Photos stay on Seema's device and in the local import; the header band is masked before any upload (OD-9). Roll numbers: OD-14.
- **Why:** Seema's time.
- **Confirmed by:** Gopi.

### 2026-10-17 · P07 live check: the replaced Sarvam key works; voice latency over target
- **Decision:** after Gopi replaced the key, `scripts/check_voices.py` synthesised all 36 clips (twelve children in en, hi, ta), so the twelve speaker names are accepted; `scripts/voice_latency.py --live` timed 24 voice turns: median 7515 ms, p90 9938 ms against the 5 s target (`evals/results/voice_latency.json`). The target stays at 5 s; the plan is to shrink the text pipeline first, then stream the reply audio. This supersedes "the Sarvam key in `.env` is rejected" below.
- **Why:** the numbers are real and the bar is not relaxed.
- **Alternatives:** relax the voice bar (rejected: needs a human-confirmed entry).
- **Confirmed by:** pending Gopi.

### 2026-10-17 · P07 limits on the voice endpoint, found in review
- **Decision:** `/voice-turn` refuses a finished rehearsal before any speech call, refuses audio over 2 MB or 30 s, turns any unexpected speech error into `text_mode`, and has a daily speech budget (`SPEECH_BUDGET_INR_DAILY`, default 200 INR, in memory per process). A per-IP rate limit stays parked until the staging URL is public. Audio length is read from the decoded samples, because ffmpeg's piped WAV header carries no length (found while adding the 30 s check).
- **Why:** the privacy review found one request could trigger many paid speech calls and that finished sessions still paid for transcription; CLAUDE.md section 4.10.
- **Alternatives:** a database-backed budget (later, with Postgres in P15).
- **Confirmed by:** pending Gopi.

### 2026-10-17 · P07 verified Sarvam facts
- **Decision:** the speech layer is built on these facts, read from Sarvam's docs on 2026-10-17 (nothing here was confirmed with a live call: the key in `.env` is rejected, see the next entry).
  1. **Auth:** header `api-subscription-key`. Errors have the shape `{"error": {"request_id", "message", "code"}}`; codes include `invalid_api_key_error`, `rate_limit_exceeded_error`, `insufficient_quota_error`. 429 and 503 are retried with backoff. Source: https://docs.sarvam.ai/api-reference/authentication and https://docs.sarvam.ai/api/getting-started/ratelimits
  2. **Speech-to-text:** `POST https://api.sarvam.ai/speech-to-text`, multipart `file`, `model` (`saaras:v4` default and recommended, `saaras:v3` available; `saaras:v2.5` is deprecated and uses a different endpoint), `language_code` (BCP-47: `hi-IN`, `ta-IN`, `en-IN`, or `unknown` to detect), `input_audio_codec` (only for raw PCM, 16 kHz), `with_timestamps`, `keyterms` (up to 50, v4 only). **Real-time limit 30 seconds**; the batch API takes up to 2 hours. Accepted formats include WAV, MP3, AAC, OGG, OPUS, FLAC, MP4, AMR, WMA and **WebM**, so the phone's Opus-in-WebM could be sent as is; we still transcode to 16 kHz mono WAV so chunking at silences is exact. Response: `request_id`, `transcript`, `language_code`, `language_probability` (only when the language is detected), `timestamps` (only with `with_timestamps`). Source: https://docs.sarvam.ai/api-reference/speech-to-text/transcribe
  3. **Text-to-speech:** `POST https://api.sarvam.ai/text-to-speech`, JSON `text` (2,500 characters on v3 and v4-flash, 1,500 on v2; use commas in numbers over 4 digits), `language_code` (the field is `language_code`, not `target_language_code`), `speaker` (case-sensitive, must match the model), `model` (`bulbul:v3` is the default if omitted; `bulbul:v4-flash` is the new recommended model with the same contract; `bulbul:v2` is legacy), `pace`, `speech_sample_rate`, `output_audio_codec`, `temperature`, `dict_id`. **`pitch` and `loudness` exist on `bulbul:v2` only.** **`opus` is a validation error on v3 and v4-flash**: use `mp3` or `wav`, then encode to OGG/Opus ourselves. Response: `{"request_id", "audios": [base64]}`. Source: https://docs.sarvam.ai/api-reference/text-to-speech/convert and https://docs.sarvam.ai/api/getting-started/models/bulbul
  4. **Voices:** v3 has 30+ named speakers (Shubh default; Aditya, Ritu, Priya, Neha, Rahul, Pooja, Rohan, Simran, Kavya, Amit, Dev, Ishita, Shreya, Ratan, Varun, Manan, Sumit, Roopa, Kabir, Aayan, Ashutosh, Advait, Anand, Tanya, Tarun, Sunny, Mani, Gokul, Vijay, Shruti, Suhani, Mohit, Kavitha, Rehan, Soham, Rupali). v4-flash has 200+ persona voices named like `simran_en_customer`; v3 names are not valid on it. The v2 speaker list is not published.
  5. **Voice cloning (beta):** `POST /voices/create` (multipart: `file` 10 to 15 s recommended and up to 50 MB, `name`, `language`; returns `data.voice_id`) then `POST /voices/clone` with the `voice_id` (its request fields are not documented). Voice count is capped by plan tier. No licence terms are published on the page. Source: https://docs.sarvam.ai/api-reference/voice-cloning
  6. **Pronunciation dictionary:** `POST /text-to-speech/pronunciation-dictionary` (multipart `file`, a `.json` with a `pronunciations` object keyed by language code; the entry shape is in the guide, not the reference), returns `dictionary_id`, passed as `dict_id` in TTS. Only v3 and v4-flash. Limits: 10 dictionaries, 100 words each, 1 MB. Source: https://docs.sarvam.ai/api-reference/pronunciation-dictionary
  7. **Rate limits (Starter):** speech-to-text REST 60 requests a minute; text-to-speech REST 60 (30 on v3); voice cloning 10 sustained. 429 body `{"error": {"message": "Rate limit exceeded", "code": "rate_limit_exceeded_error"}}`.
  8. **Prices (INR):** speech-to-text 30 per hour of audio (billed per second); Bulbul v3 30 per 10,000 characters; instant voice cloning 30 per 10,000 characters; new accounts get 100 in credits. Stored in `services/speech/pricing.yaml`. Source: https://docs.sarvam.ai/api/getting-started/pricing
- **Why:** CLAUDE.md section 8 requires verification before coding. Three of these differ from CLAUDE.md or the design: the TTS field is `language_code`; Opus output is refused on v3, so OGG/Opus is made with ffmpeg; and `bulbul:v4-flash` now exists (Voice Agents on v3 end on 10 Nov 2026, per Sarvam's landing page; the REST API is not said to end).
- **Alternatives:** the finguru voice server (decided against on 2026-10-16).
- **Confirmed by:** pending Gopi (facts only).

### 2026-10-17 · P07 the Sarvam key in `.env` is rejected
- **Decision:** a text-to-speech request with the key in `.env` (44 characters, `sk_` prefix, no stray spaces or quotes) returns 403 `invalid_api_key_error`, with the header spelled `api-subscription-key`, `API-Subscription-Key` and as a Bearer token. The code is built and tested against mocked HTTP, real ffmpeg and a stub; live checks, the voice latency evidence and the real-phone check wait for a working key.
- **Why:** the key may be revoked, mistyped or not yet activated; only Gopi can check it on Sarvam's dashboard.
- **Alternatives:** none: a live call cannot work with it.
- **Confirmed by:** n/a (a blocker, not a decision).

### 2026-10-17 · P07 voice design
- **Decision:** (1) Child voices use stock Bulbul v3 speakers whose pitch is raised with ffmpeg (`asetrate`, `aresample`, `atempo`: pitch up, speed unchanged), because v3 has no pitch control and v2's speaker list is unpublished; each of the 12 personas has a fixed speaker and pitch ratio in `content/voices/children.v1.yaml`, so a child sounds the same every session and five children in a session sound different. Cloned voices are built behind `SARVAM_CLONES=1`, off by default and untested live. Licence policy: licence-cleared AI-designed voices or a consenting adult; never a real child. (2) Speech goes out as OGG/Opus mono at 24 kbps (about 3 KB a second), returned inline as base64 in the voice-turn response. (3) Speech-to-text gets 16 kHz mono WAV chunks of at most 28 seconds, cut at silences. (4) Text-to-speech runs in parallel with call 7; audio is released only if the check passes, otherwise the template line is synthesised. (5) A circuit breaker opens after 3 consecutive speech failures for 30 seconds; the client also falls back to text after 2 failures or on a 2g connection. (6) `SPEECH_MODE=stub` makes speech-to-text return scripted lines and text-to-speech a generated tone, for tests and demos; it is not speech recognition and says so. (7) Speech calls are logged in a `speech_calls` table (stage, latency, bytes, characters, seconds, cost in INR, error kind), never the audio or text.
- **Why:** the smallest build that meets P07 and keeps what a teacher says off the server.
- **Alternatives:** v2 with its pitch parameter (speaker list unknown); streaming synthesis (later, if latency needs it).
- **Confirmed by:** pending Gopi.

### 2026-10-17 · P06 Practice Class UI decisions
- **Decision:** (1) The API creates a session with the class's counts (class-level only) and returns the seed, so "try again with the same children" reuses it; `?seed=` in the deep link makes a demo repeatable (the Playwright tests use seed 5 to replay the recorded rehearsal). (2) The AI-layers overlay, AI map and audit pages are judge-role only; they show metadata and the trace, and the audit page never shows what anyone typed. (3) When the day's budget is spent the screen says "Practice is paused for today" and offers a recorded sample rehearsal (`apps/pwa/public/sample-practice.json`, made by `scripts/make_sample_practice.py` from the committed live session); a slow or failed model call shows a template line with a "slow connection" notice; offline shows "Practice needs a connection". (4) "Share this session" is a stored choice only, off by default; no sharing endpoint exists yet. (5) Thumbs up or down per feedback point are saved on the phone with the transcript. (6) CORS: the API answers browsers from `PWA_ORIGIN` only (no wildcard, no credentials); the PWA reads `VITE_API_BASE` for a separately hosted API. (7) Playwright starts the API on port 8011 in recorded mode with its log in `e2e-api.log`, so tests never meet a dev server on 8000 and can check the server log holds no transcript text. (8) The staging deploy is a written recipe (`docs/deploy.md`, `Dockerfile`), not yet run: it needs hosting accounts and secrets from Gopi.
- **Why:** the smallest build that meets P06 and keeps what a teacher says on her phone.
- **Alternatives:** a server-side transcript store for sharing (rejected for now: needs the opt-in flow of P11); a service-worker cache for practice replies (rejected: the Practice Class is the one live feature).
- **Confirmed by:** pending Gopi.

### 2026-10-17 · P05 PWA decisions
- **Decision:** (1) No router or state library: a 40-line hash router (deep links work on a static host and offline) and React context. (2) Judge mode is the default role and its strip (role and language) is always on screen; a real teacher build will hide it in P15. (3) Answer keys now carry each item's operands (`a`, `b`), so the app can show a class's own example ("52 − 29 → 37"); still lookups only, regenerated by `python tasks.py export-keys`. (4) The profile that syncs is counts only and the server schema forbids every other field (`extra=forbid`); the class id is a random id made on the phone. (5) The untracked pattern is counted per answer, not per child, so its card says "answers" not "children". (6) Autosave writes one after another, so the last key typed is the last thing saved. (7) The simulated class is generated on the phone from the answer keys (28 children, term 1 and term 2 counts set in `src/lib/demo.ts`) and is labelled simulated wherever it shows. (8) A teacher's "this is wrong" tap on a T3 card is kept in the phone's queue for now; no server endpoint stores flags yet (T3 cards are made by code, not AI). (9) Lighthouse 12 and later have no PWA category, so installability and offline behaviour are asserted by Playwright and Lighthouse supplies performance, accessibility and best-practices. (10) `fake-indexeddb` is a dev dependency, for Vitest only.
- **Why:** the smallest build that meets the P05 brief and keeps per-child data on the phone.
- **Alternatives:** react-router (extra dependency for five routes); sending per-child answers for server diagnosis (rejected: privacy).
- **Confirmed by:** pending Gopi. Hindi (Shivani) and Tamil (Gopi) wording are build drafts for native review.

### 2026-10-17 · P04 Practice Class decisions
- **Decision:** (1) The simulator is `engine/simulator.py`, pure and seeded per turn from (session seed, turn number), so a session replays exactly. (2) Move ids are shared across the four tracked errors (`pose_problem`, `ask_explain`, `show_bundles`, `exchange_ten`, `check_back`, `tell_rule`, `praise`, `scold`, plus `show_chart` and `regroup_ten` where they fit); effect values follow CLAUDE.md section 5, and the two not listed there (`exchange_ten` -0.3, `regroup_ten` -0.3, `show_chart` -0.3) are placeholders for Seema. (3) The PV-HEARD scenario uses the design's 2-digit dictations (forty-three, 403) although the check items are 3-digit; both are valid for the bug functions. (4) If she names no child, the child she was talking to continues; a line to the class lets the engine choose the speaker by engagement. (5) A tap on the materials tray is a move without a labeller call and counts as evidence for the rubric ("[tapped bundles]"). (6) A scolded child is quiet for 2 turns; scolding changes engagement, never strength. (7) The Tamil number-word list leaves out ஒன்று, பத்து and நூறு, because they are also the Tamil place-value words a child's working must say. (8) Child-line readability allows 20 words per sentence (was 12), because a child's step-by-step working is one sentence; the 30-word cap is unchanged. (9) `AI_MODE=stub` and `CallContext(mode="stub")` run a rule-based stand-in for the model with no spend; audit rows say `stub`. (10) Live result files are separate from code-only ones (`redteam_live.json`, `sim_fidelity_live.json`). (11) The red-team seed set grew from 12 to 22 (10 injection lines typed to the Practice Class); the bar (0 unsafe reach a teacher) is unchanged.
- **Why:** each is the narrowest reading of the P04 brief that keeps the engine testable and the children faithful.
- **Alternatives:** per-error move ids (more files, same behaviour); letting the model choose who speaks (drifts).
- **Confirmed by:** pending Gopi; Seema reviews the move lists, rubrics, scenario values and personas (`TODO-HUMAN(Seema)`).

### 2026-10-17 · P04 AI settings found by live runs
- **Decision:** (1) Thinking is switched off for the short rule-bound calls where the API allows it: Haiku 5.5 takes `{type: disabled}`, Sonnet 5.5 takes `{type: between_tools}` (it rejects `disabled`), Opus 5.5 cannot switch it off; `ai/config.py::thinking_param` spells it per model. Call 3, 4, 5 and 8 keep adaptive thinking. (2) Token limits rose (call 7 to 800, call 3 to 2500) after thinking tokens made call 7 return nothing. (3) Call 7 prompt v4: for a simulated child line it never judges maths or fit (code checks every number against the engine) and keeps its reasons short; call 2 prompt v3 adds off-task examples in four languages; call 1 prompt v2 and call 3 prompt v2 carry the turn plan and feedback shape. (4) Timeouts: calls 1, 2 and 7 allow 12, 10 and 12 s, because live latency spikes of 8 to 20 s were seen; a timeout still falls back to a template. (5) Haiku 5.5 for call 1 was slower in an A/B and is not adopted.
- **Why:** live runs showed the checker rejecting valid lines and returning nothing; these are the fixes, each re-tested live.
- **Alternatives:** relax the checker's pass rule (rejected: it must still fail closed).
- **Confirmed by:** pending Gopi.

### 2026-10-17 · P04 latency target not met in text mode
- **Decision:** the median text turn measured above the 3 s target (`evals/results/practice_latency.json`), because three network calls run in series. The bar stays at 3 s (text) and 5 s (voice); the plan is the check-then-release overlap with speech in P07, a server near the Claude endpoint in P15, and re-measuring then. Nothing was relaxed.
- **Why:** the number is real; lowering effort and thinking were already tried.
- **Alternatives:** release the line before call 7 passes (rejected: gates before teachers).
- **Confirmed by:** pending Gopi.

### 2026-10-16 · P03 verified API facts (Claude API)
- **Decision:** the AI platform is built on these facts, checked on 2026-10-16 against the bundled Claude API reference (cached 2026-10-06) and, for prices, the live pricing page.
  1. Model IDs: `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5` (no date suffixes). Source: https://platform.claude.com/docs/en/about-claude/models/overview
  2. Structured output: `client.messages.parse(model, max_tokens, system, messages, output_format=PydanticModel)` returns `.parsed_output`; the raw form is `output_config={"format": {...}}` on `messages.create`. We use `output_format=` as CLAUDE.md says and re-validate with Pydantic. Installed SDK: `anthropic` 1.15.0 (`parse` accepts `output_format`, `output_config`, `thinking`, `timeout`). Source: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
  3. Thinking and effort on the 5.5 models: thinking is adaptive by default and cannot be set to `disabled` on Opus 5.5 or Sonnet 5.5 (400). Effort is `output_config={"effort": "low|medium|high|xhigh|max"}`; defaults are `medium` on Opus 5.5 and Haiku 5.5, `high` on Sonnet 5.5. We set effort explicitly per call in `ai/config.py`. Forced `tool_choice` any/tool is a 400 on Opus 5.5 and Sonnet 5.5, so we use structured outputs, not forced tools. No assistant prefill. Sampling parameters (temperature, top_p) are rejected on Sonnet 5.5 and Haiku 5.5, so we send none.
  4. Prompt caching: minimum cacheable prefix is 512 tokens on all three models; cache reads cost 0.1x input (Opus 5.5 0.05x). A stable system block put first with `cache_control: {"type": "ephemeral"}` caches only if it reaches 512 tokens, so each prompt file must be long enough or `cache_read_input_tokens` stays 0 (checked in logs by `run_call`, reported by `python tasks.py budget`).
  5. Message Batches API: `client.messages.batches.create(requests=[{custom_id, params}])`, results in any order keyed by `custom_id`, 50% discount. Used by call 5 in P09.
  6. Image input: base64 `image` content blocks (JPEG/PNG). Used by call 8 in P08.
  7. Prices (USD/MTok, input / 5m cache write / cache read / output): Opus 5.5 4 / 5 / 0.20 / 20; Sonnet 5.5 2 / 2.50 / 0.10 / 10; Haiku 5.5 0.10 / 0.125 / 0.01 / 0.50. Batch is half. Stored in `ai/pricing.yaml` with source URL and date.
- **Why:** CLAUDE.md section 8 requires verification before coding.
- **Alternatives:** none.
- **Confirmed by:** pending Gopi (facts only, no policy change).

### 2026-10-16 · P03 design choices
- **Decision:** (1) The audit trail stores metadata only for every call: ids, hashes, token counts, cost, validator codes. It never stores prompt or output text; reviewed content lives in `review_items`. (2) Judge-mode traffic ignores `AI_BUDGET_USD_TOTAL` and `AI_BUDGET_USD_DAILY` (the judging reserve) but stops at a new hard ceiling `AI_BUDGET_USD_HARD` (default 500). (3) Recorded mode with no recording counts as a failed call and goes to the deterministic fallback, so tests show the fallback path rather than crash. (4) Schemas for calls 1 to 8 are minimal and may grow in P04 to P09; prompts for calls 1, 2, 3, 4, 5, 6, 8 are v1 drafts until their phase. (5) Hindi and Tamil number-word lists and profanity lists are first drafts for native review (`TODO-HUMAN(Shivani, Gopi)`).
- **Why:** narrowest reading of the P03 spec; privacy-first audit.
- **Alternatives:** store output text in the audit row (rejected: teacher text must not reach storage).
- **Confirmed by:** pending Gopi.

### 2026-10-16 · P02 clarifications and deviations
- **Decision:** (1) Same-term candidate mentors need at least 10 children checked (the check's own floor); the spec gave none. (2) The comparison-group improver drops the "beats the comparison group's average" rule: she is in the comparison group. (3) A pilot with no untrained error at p of at least 10% at pre-test has no baseline, so extra fall is undefined and the verdict is inconclusive. (4) Bootstrap estimate and interval are rounded to 9 places before comparing with a threshold, so float noise cannot flip a verdict at exactly -10. (5) Cohorts follow the spec literally (15 to 20, at most 2 per school); where the pool cannot fill a cohort of 15, it is flagged undersized rather than padded, and teachers who do not fit are returned as unplaced. (6) The simulated block uses 3 Grade 3 sections per school and one block, so demo cohorts are small. (7) Planted effects are set as `extra_fix` (extra chance a child's error is fixed): SUB-SFL v1 0.36 for about 20 points, SUB-NODEC v1 0.00. The value was chosen to match the design's "about 20 points", not to reach a verdict. (8) Eval 8 simulates classes with binomial child counts rather than the full answer-sheet model, for speed; effects vary class to class (sd 5 points). (9) Tables are created with `create_all`; the first Alembic migration waits for a stable API schema (P03 or P09). (10) Hypothesis deadlines are off (timing flake on a loaded machine; logic unchanged).
- **Why:** each is the narrowest testable reading of the spec; none changes a threshold or a bar.
- **Alternatives:** pad undersized cohorts with out-of-block teachers; add a migration now.
- **Confirmed by:** pending Gopi. Seema reviews the simulated teacher names (`TODO-HUMAN(Seema)` in `content/personas/teachers_simulated.yaml`).

### 2026-10-16 · P01 spec clarifications
- **Decision:** (1) The eligibility boundary "p = 0.25 with 10 checked" cannot occur (2.5 children); the engine compares `count × 4 ≥ checked` with integers and tests 3 of 12 and 4 of 16 (eligible) and 3 of 13 (not). The 10-children minimum is tested separately. (2) `class_profile(children)` takes no `form` argument (it was unused). (3) Numbers with a zero digit have no heard or reversed answer. (4) Normaliser keeps a leading-zero string as its number ("034" → 34); more than 9 digits or any non-digit is unreadable. (5) Children checked counts every diagnosed child, including ones with blank or unreadable boxes. (6) Answer sheets crossed out and rewritten ("use the last answer") is a reading-step rule (P08), not an engine rule.
- **Why:** each is the narrowest reading of the spec that is testable; none changes a threshold or bar.
- **Alternatives:** treat leading zeros as unreadable (more teacher taps).
- **Confirmed by:** pending Gopi; Seema to confirm the heard-and-reversed variants and NCERT mapping (placeholder in `docs/engine.md`).

### 2026-10-16 · Voice uses Sarvam directly, no finguru voice server
- **Decision:** `services/speech/` calls the Sarvam APIs (STT and Bulbul TTS) itself. The finguru voice server is not reused. The Telegram bot is still built fresh unless Gopi supplies paths.
- **Why:** Gopi's call: one fewer dependency and a simpler demo to explain to judges.
- **Alternatives:** reuse finguru's WebSocket + VAD server.
- **Confirmed by:** Gopi.

### 2026-10-16 · P00 defaults applied: MIT licence, finguru built fresh
- **Decision:** `LICENSE` is MIT (OD-1). No finguru paths were given, so voice (P07) and Telegram (P10) are built fresh (OD-2). Tooling: no `uv` or `ffmpeg` on Gopi's machine; `tasks.py` falls back to venv + pip, and ffmpeg is needed from P07 (`winget install Gyan.FFmpeg`). Python deps are listed unpinned in `pyproject.toml` and pinned in `requirements.lock`; `package-lock.json` pins the PWA.
- **Why:** the starter prompt says to use defaults for anything unanswered.
- **Alternatives:** Apache-2.0; reuse finguru if Gopi supplies paths (reversible before P07).
- **Confirmed by:** pending Gopi (defaults in force).

### 2026-10-16 · Build calendar recompressed
- **Decision:** the build starts 16 Oct; the calendar in `CLAUDE.md` §1 replaces the design doc's 12 Oct plan. Gates: Gate 1 on 19 Oct, staging on 21 Oct, Gate 2 on 26 Oct, freeze on 28 Oct, submit on 31 Oct.
- **Why:** the design finished later than planned; the deadline didn't move.
- **Confirmed by:** Gopi.

### 2026-10-16 · Pilot tests run by class teachers
- **Decision:** the hackathon team does not conduct the tests. Seema arranges them with each school's HM; each class's own teacher runs the pre-test and the post-test with the scripted instructions. Seema keeps the answer key.
- **Why:** school access and appropriateness; the same tester for pre and post keeps results comparable.
- **Confirmed by:** Gopi.

### 2026-10-16 · Pilot sheets carry roll numbers; product sheets do not
- **Decision:** pilot sheets have a roll-number box so each child's pre and post sheets can be paired for McNemar. Pairing runs only on a device or in a local script; raw pilot files never enter git; only counts and 2×2 tables leave the machine. Product sheets keep the design: no name, no roll number, roll order known only to the teacher's phone.
- **Why:** paired analysis needs a link; privacy needs it to stay local.
- **Alternatives:** fully anonymous pilot sheets (lose the paired test).
- **Confirmed by:** Gopi.

### 2026-10-16 · Two impact methods
- **Decision:** pilot scale uses extra fall (trained error's fall minus the average fall of untrained errors with pre-test p ≥ 10%) plus an exact McNemar test; Working = extra fall ≥ 10 points and p < 0.05; Not working = extra fall < 5 points or a rise; else Inconclusive. Block scale keeps the design's difference in differences with a 95% bootstrap CI and the ≥ 15 classes per arm rule.
- **Why:** a handful of pilot classes can't support a comparison group; the block design can.
- **Confirmed by:** Gopi.

### 2026-10-16 · Telegram, with tap feedback
- **Decision:** Telegram is the channel (no WhatsApp Business API account). After each lesson the bot asks two taps: "Tried it in class?" (yes / not yet) and "How did it go?" (worked / partly / didn't work). Voice reflections are optional. Real impact is confirmed by the next check, not by self-report.
- **Why:** low friction over three weeks; a few rich voice notes can still be gathered by hand for the deck.
- **Confirmed by:** Gopi.

### 2026-10-16 · Two kinds of mentor
- **Decision:** *same-term candidate*: a class with p ≤ 5% on an error while the block average is ≥ 25%, in the same batch; the cause is unverified, so a method interview comes first and the label stays "candidate" until a term confirms. *Track-proven*: from a previous term, post-test confirmed the error fell after her track. These match the design's cold-start and proven rules; the comparison-group improver rule also stays.
- **Confirmed by:** Gopi.

### 2026-10-16 · Two-tier mentor lookup, no vector database
- **Decision:** tier 1 is an exact database query (error, grade, medium, verified status). Tier 2 passes up to 3 approved method cards for that error, whole, into call 5. Vector search over method cards waits until there are enough of them (roadmap).
- **Why:** at pilot scale exact match is enough, and embeddings add moving parts without signal.
- **Confirmed by:** Gopi.

### 2026-10-16 · Knowledge graph and lesson videos are roadmap only
- **Decision:** the graph of approach × analogy × child profile × region × outcome is a later phase, gated on data volume; until then each verdict record keeps flat fields. Lesson videos, when needed for large cohorts, are a templated slideshow synced to the same script and Sarvam audio, with no video model.
- **Confirmed by:** Gopi.

### 2026-10-16 · Judging extras in scope
- **Decision:** Checked ✓ / Reviewed ✓ badges (including one line in each Telegram lesson caption); structured rejection reasons fed back into call 7 as examples; a confidence note on every small-sample number; cost per teacher per track in cents; a rule-based pre-filter before call 7; a reading-level check (Grade 3 for child-facing lines, plain spoken language for teacher-facing lessons); an injection category in the red team; one shared audit trail; one-line explanations wherever a decision is shown; a stated target phone; the Practice Class connectivity trade-off stated openly.
- **Confirmed by:** Gopi.

### 2026-10-16 · Teacher-facing explanations use counts
- **Decision:** explanations shown to teachers use counts ("11 of 28 children"), consistent with the T3 rule; the design doc's "40% SUB-SFL" example applies only to officer views.
- **Confirmed by:** Gopi.

### 2026-10-11 · Core design
- **Decision:** everything in `docs/design/cohort-coach-design.md` (slice, four errors, eight calls, model routing, four gates, privacy, offline matrix, evals and bars, screens, submission kit) unless a later entry here changes it.
- **Confirmed by:** team.
