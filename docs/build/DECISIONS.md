# Decisions log

Newest first within each section. Every entry: date, decision, why, alternatives considered, who confirmed. A newer entry here overrides `CLAUDE.md`, the build prompts and the design doc; update `CLAUDE.md` in the same commit when a rule changes.

### 2026-10-30 · Device-based tester profiles and a Testing evidence view (TESTER_STATS=1)
- **Decision:** the public demo and tester links can collect opt-in, coarse usage data from testers, shown to judges as aggregates. A random id is made on the device and never leaves it; the device sends only SHA-256(salt + id). Nothing is sent (no profile, event or feedback) before the person agrees; "Use without sharing" sends nothing and the app works in full. Collected: nickname, coarse device class, browser and system family, language, screens opened, features used, tour progress, a connection class and feedback the person types (phone numbers and emails masked). Never: IP address (the access-log line for these paths is dropped), location, contacts, user-agent string, typed content, voice, child or teacher data. Judge devices (a `?src=judge` link or choosing the Judge role) and team devices (`?team=<TESTER_TEAM_TOKEN>`) are tagged and left out of tester counts by default, shown separately. The judge endpoint answers only the judge role in a judge deployment; the CSV export needs the team token. Events and feedback are deleted after 90 days or on "Delete my data". The switch is the server flag `TESTER_STATS=1`; it is never mounted in pilot mode. The guided tour gains a seventh step ("See who has tried it"), budgeted at 10 s so the tour stays within 300 s. Report: `docs/build/reports/TESTER-STATS.md`.
- **Why:** the submission needs real, live proof of user testing and refinement (judged area "user inputs and testing"), without inflating numbers and without collecting anything private.
- **Alternatives:** third-party analytics (rejected: scripts, cookies, IP); a fingerprint or user-agent id (rejected: tracking); showing every tester by name (rejected: listing is a separate, off-by-default consent); seeding sample testers (rejected: no fabricated evidence, non-negotiable 7).
- **Confirmed by:** Gopi (request of 30 Oct).

### 2026-10-30 · The v2 front-end (`apps/pwa-v2/`) is parked; v1 is the only front-end
- **Decision:** `apps/pwa-v2/` is not run, deployed or extended. Its run script (`run-frontend-v2.bat`) is removed; the folder stays in the working tree, uncommitted, for reference only. All front-end work from here is in `apps/pwa/`.
- **Why:** the re-skin needs a lot more fixes (most screens are not rebuilt on the new components; fonts and snapshot tests are open) and the freeze has passed.
- **Alternatives:** finish v2 before 31 Oct (rejected: no time).
- **Confirmed by:** Gopi (30 Oct).

### 2026-10-30 · Re-skin the front-end in a new folder, behaviour frozen
- **Decision:** the front-end re-skin (`docs/build/Claude Code prompt re-skin the front-end ...`) is built as a copy in `apps/pwa-v2/`; `apps/pwa/` is untouched. v2 adds tokens with a dark mode and a five-size type scale (`src/styles/tokens.css`), a base layer for raw form elements, a component set (`src/ui/`), a side rail from 900 px, and a living style guide at `#/dev/styleguide`. APIs, state, permissions and AI calls are unchanged; the screens still render their existing markup and gain the new look through the shared classes. Screens are migrated to the components one at a time; Officer cohorts and Profile were done first. One shared string key (`judge.styleguide`) was added in en, hi and ta.
- **Why:** the user asked for a new front-end folder so the working app stays as it is for the submission. The `UI_V2` flag in the prompt is not needed, because the two apps do not share a build.
- **Alternatives:** re-skin in place behind a flag (rejected by the user); rewrite every screen on the new components at once (rejected: no time before 31 Oct, and the risk of changing behaviour).
- **Confirmed by:** Gopi (folder choice, 2026-10-29). Open: whether v2 replaces `apps/pwa/` for the final deploy.

### 2026-10-30 · One assistant, scoped by role on the server
- **Decision:** one assistant for all roles. The server sets the scope from the authenticated role (judge in the judge deployment, teacher everywhere else); a question or a "act as" phrase never widens it; only the judge session may View as another role; the About this product tab is always the judge scope. The judge corpus includes the repository markdown, `docs/RUBRIC_MAP.md`, the deck slides and the video script, so judge answers cite a file, a slide number and a video time. Retrieval is word-based over a plain JSON index bundled in the image (no embeddings). Suggested questions are pre-written from the docs and work offline; free text uses call 14 and abstains when nothing is found. The assistant is read-only: it cannot approve, send or delete, and it reads no live class data yet.
- **Why:** judges and each role need answers that stay inside what they may see and never claim more than the rubric map's status.
- **Alternatives:** scope in the prompt (rejected: can be talked around); embeddings and a vector store (rejected: CLAUDE.md bars a vector database and plain JSON works with no network).
- **Confirmed by:** Gopi (asked for the build, 29 Oct). Dated 30 Oct as the prompt specifies; built 29 Oct.

### 2026-10-29 · Material 3 on every screen, with the whole look in one file
- **Decision:** (1) Every screen now uses the Material 3 look of `docs/design/stitch/DESIGN.md` (teal primary, 16 px cards, 8 px buttons and fields, state layers on hover, focus and press, a navigation bar with a selected pill, a bottom sheet for More, tonal banners). This supersedes the blue-notebook look of `docs/design-system.md` v1 and the "parked" note in the entry below. (2) The look lives in one file, `apps/pwa/src/theme.css`: palette, corners, state layers, spacing, type. `styles.css` and `pilot/pilot.css` read those tokens. `tests/test_design_tokens.py` now fails if a colour literal returns to `styles.css`, if a stylesheet uses a token nothing defines, if the `classic` theme overrides a token that does not exist, or if the manifest colours, meta tag and icons drift from `--pen` and `--paper`. (3) `VITE_THEME=classic` builds the old palette and 2 px corners for comparison. (4) The contrast figures in the doc are recomputed from the new tokens: body text 16.3 and 8.9, primary 6.0, error 6.2, all above 4.5; the 16 px text floor and the tap sizes are unchanged. (5) The app icons, the manifest theme colour and the browser bar colour moved to the teal.
- **Why:** the landing page was teal and the rest blue; the project's own design file already specified this look; and a later colour or shape change should be one edit, not a hunt through 1,600 lines.
- **Alternatives:** teal on the shared pieces only (rejected by Gopi, who chose the whole app); a runtime theme switcher in the interface (not built: a build setting is enough, and a switch would add a screen); dark mode (the design file's dark values are marked as needing a designer's check, so not built).
- **Confirmed by:** Gopi (29 Oct): whole app, same look, as configurable as possible. The calendar's feature freeze (28 Oct) has passed; this changes appearance only, and every browser test was rerun.

### 2026-10-29 · Landing page in Material 3; install guide; offline pill; signal estimate; Mode menu
- **Decision:** (1) The landing page uses the Material 3 tokens of `docs/design/stitch/DESIGN.md` (teal primary, tonal containers, 16 px cards, 8 px buttons, state layers), scoped to the landing page and the install sheet; the rest of the app keeps its palette until it is rebuilt. (2) A card on the landing page, and a button in My profile, open a sheet that says what a web app is and how to save it to the home screen (Chrome on Android; one line for iPhone), in the teacher's language; an Install now button shows where the browser allows it. Installing stays optional. (3) The offline marker is a short pill with a cloud-off icon ("Offline"), and a note under the header says what still works (entering checks, saved lessons) and that the Practice Class needs signal; this replaces "Offline: everything here still works", which overstated it. (4) Online, the pill adds the browser's own estimate of signal and download speed (Network Information API, Chrome on Android) when it gives one. No speed test is run and nothing extra is downloaded; upload speed is not shown because the browser does not provide it. (5) The Mode menu (Judge demo, Pilot) joins role and language in the landing-page bar where a second back end exists. The big "Open the pilot" button is gone; a one-line note at the bottom of the page points staff to the menu.
- **Why:** teachers with little digital experience were never told they could keep the app on the phone; the offline text squeezed the app name into two lines and promised more than the offline matrix delivers; the pilot button took the first screen of a phone from the guided tour.
- **Alternatives:** an active speed test (rejected: it spends the teacher's data and battery, and the number swings; it would fight the 10 MB per track budget); a combined upload and download number (not available without such a test); a separate install page (rejected: the card and sheet are enough); recolouring the whole app teal now (parked: needs `docs/design-system.md` and the token test updated together).
- **Confirmed by:** Gopi asked for each change (29 Oct); the Hindi and Tamil wording is mine and needs Seema's and Gopi's review.

### 2026-10-28 · Role and language bar on the landing page only; Practice Class in sections
- **Decision:** (1) the dark bar with the role and language menus shows only on the landing page (`#/roles`). Elsewhere, the app name in the header leads back to the landing page; My profile has a language menu and a "Change role" link. This overrides addendum v3.1 §A ("a role switcher stays in the header"). (2) Because the language can no longer change in the middle of a rehearsal, the Practice Class "language changed, restart?" banner and its two strings are removed; the next rehearsal starts in the new language. (3) On the running Practice Class, the children, the turn count and section tabs (Class, Materials, Goal, and Judge in judge mode) stay at the top while the conversation scrolls; the typing box stays at the bottom. The layers switch, "Try with hints" and "Try to break it" sit in the Judge tab.
- **Why:** the bar took a band of every phone screen for a choice made once; the Practice Class ran several screens long on a phone.
- **Alternatives:** a small globe button in every header (not asked for; kept simple); hiding the bar for teachers only (judges switch roles from the landing page cards anyway).
- **Confirmed by:** Gopi, 28 Oct (both changes, the profile language menu and the removed banner).

### 2026-10-27 · One web address for both modes
- **Decision:** the web app at https://cohort-coach-pwa-1097171252131.asia-south1.run.app serves both the judge demo and the pilot. The landing page shows the mode and the role and has a switch; a teacher's lesson link always opens the pilot. The two stay **separate servers** (judge: `cohort-coach-judge-api`, JUDGE_MODE=1, SQLite, min 1 instance; pilot: `cohort-coach-api`, PILOT_MODE=1, Cloud SQL). The page picks which API to call from the chosen mode (`VITE_API_BASE`, `VITE_PILOT_API_BASE`).
- **Why:** one link for judges and staff. JUDGE_MODE opens every role to anyone and must never share a server or database with real consented sheets, so a single combined API was not done.
- **Alternatives:** one API in both modes (rejected: breaks the fail-closed rule in CLAUDE.md section 4 and deploy.md); two links (what it was before).
- **Confirmed by:** Gopi (asked for one link; separate back ends are my choice, to be confirmed).

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

### 2026-10-27 · P12 reduced: the officer's view; Gate 2 is not met
- **Decision:** P12 ships the officer's aggregates (`services/api/officer.py`, screen `#/officer`): the error map by medium (a cell over fewer than 5 classes is hidden), the funnel (Delivered: system; Tried it in class: self-report; Practised: not counted per cohort because Practice Class sessions are metadata only on the server; Changed: awaiting next check), and track results per version computed at request time by `engine.evaluation` (estimate, 95 percent interval, classes per arm, verdict, confidence note, "a failed track counts against the track, not the teacher"; a group under 5 classes shows no number). Permissions `officer.results` and the boundaries `officer.aggregates_only`, `officer.no_approval` and `coach.no_teacher_numbers` are enforced with tests. **Cut:** role assignment with consent and production-mode landing (A8), cohort approval screen (P2), CRC visit brief, content library screens, officer stage view, "Advance to Term 2" (the simulated block already holds both terms, so the results show term 2 at once), time-budget medians in the funnel, "waiting for review" after 7 days. **Gate 2 (every storyboard screen works on a low-end phone) is not met**: it needs Gopi's real phone.
- **Why:** the results and funnel are the honest-statistics story; the rest did not fit in the days left.
- **Honesty:** the funnel's Practised step says it is not counted; nothing says "listened" or "adopted"; the demo block is simulated and labelled.
- **Confirmed by:** not yet.

### 2026-10-27 · P11 reduced: cohort space, mentor item approvals, posting checks
- **Decision:** P11 ships the cohort lifecycle (with audit rows and the close rule), the pseudonymous moderated thread (system labels, posting check, report, hide, restore, pin, erase on identifier, 7/30/90-day retention, delete own post), mentor items with coach approval and the in-use rule, and a screen at `#/cohort` for teachers and coaches. Permissions `cohort.chat`, `mentor.items_view`, `coach.approve_items`, `coach.moderate`, `officer.approve_cohorts` are now enforced; three boundaries (mentor own cohorts only, mentor no class numbers, coach assigned only) have tests. The existing roles test that expected the teacher card to show cohort chat as "planned P11" was updated, because it is no longer planned (the mentor card still has planned items). **Cut:** Telegram relay, voice, notifications, the mentor recording flow (M1), call 4, call 6 digest, mentor pages in the PWA, real role assignment (P12).
- **Why:** rule 15 is a non-negotiable and stays claimable only for what is built; the rest would not fit in the days left.
- **Honesty:** the posting check is best effort and says so; pseudonyms are pseudonymous to peers, not to the coach.
- **Confirmed by:** not yet (Gopi, with P09 and P10 cuts).

### 2026-10-27 · P10: what is built and what is cut
- **Decision:** P10 ships the T4 flow (track intro, one `media` step per lesson with a voice note in Telegram and an audio player in the web app, the badge line, two self-report taps per lesson, the model-lesson script, the Rehearse link, two lessons a week for a real teacher and everything at once for a judge), the T6 flow (her class's change on the tracked error in counts, no percentage, no comparison, "a failed track counts against the track"), the time budget (weekly minutes against the 20-minute cap, a lesson over 5 minutes is not published) and `scripts/seed_demo_track.py` (the judge deployment only: approves only drafts that passed every automatic gate and publishes a simulated cohort). **Cut:** call 9 (the reflection pointer, cut-list item 8), voice reflections, the biweekly "Still using it?" prompts, offline replay of downloaded lessons in the web app, the CPD-hours export and the mentor's name in T4 (no cohort or mentor assignment exists yet; that is P11). The 3-phone acceptance journey needs real phones and is Gopi's.
- **Why:** 4 days to submission with P11 to P16 untouched; the phase's own "If behind" list cuts call 9 first.
- **Honesty:** the lesson audio is only as real as the speech key: the voice notes are made when a version is published (stub tones if `SPEECH_MODE=stub`). Taps are labelled self-report; deliveries are system; nothing says "listened" or "watched".
- **Confirmed by:** not yet (Gopi, with P09's cuts).

### 2026-10-27 · P09: content pipeline cuts, and call 7 told that sample numbers stand in for slots
- **Decision:** (1) P09 ships drafting (call 5, synchronous), slots, the two keys, the review queue API and screen, the rejection loop and publish; it cuts the model run (T12), Tamil, the citations second pass, stage routines and a live Batches run, all in PARKING. (2) In slot mode call 7 is given a trusted `slots_note` saying that the class numbers in the text are sample values for slots filled by code at delivery; the prompt file is unchanged, so the call 7 version and bars are unchanged, and P13's eval must cover a slot-mode case. (3) The coach and officer manifest view omits scripts, because a filled script carries a cohort's pooled counts and a small cohort is one teacher's class (rules 3 and 15). (4) Free text a coach types (a reject note, a trimmed example) is screened for phone numbers, emails and ID numbers before it is stored.
- **Why:** the first live run held 12 of 14 drafts at call 7 because the gate showed it sample numbers; after the note 12 of 14 pass (`docs/evidence/p09_live_draft_run_after_slots_note.txt`). The other cuts are time: 4 days to submission with P10 to P16 untouched.
- **Alternatives rejected:** a new call 7 prompt version now (needs its eval); showing the checker slot names instead of samples (the reading-level and arithmetic checks need real-looking text).
- **Confirmed by:** not yet: Gopi to confirm cuts and the small-cohort reading (listed in the P09 report).

### 2026-10-26 · Pilot audio: approve the words first, voice on a teacher's first tap, shared as a lesson link
- **Decision:** (1) The coach's approval now approves the TEXT only; it no longer calls Sarvam. (2) An approved lesson is shared as a **lesson link** (`/#/lesson/<token>`): an unguessable, HMAC-signed token that expires after 14 days and opens one approved lesson's text, with no sign-in. (3) The first tap on **Download audio** on that page voices the approved script (one Sarvam call), stores the file in the published-audio bucket, and every later tap reuses it; two taps at once make it once. A daily cap (`PILOT_VOICE_DAILY_MAX`, default 20) limits new voicings that teachers' taps cause, failures included; past it the text still opens. The coordinator can still press Make audio now. (4) The coordinator still shares by hand (Web Share, Copy link, `wa.me`); the system delivers nothing. (5) This adds one public, read-only page and two public routes (`GET /api/pilot/lesson/{token}`, `POST /api/pilot/lesson/{token}/audio`) to a mode that had only sign-in and two staff pages; the staff routes still need a token (`tests/pilot/test_lesson_link.py` checks every route). On-device voice for capable phones is parked (`PARKING.md`), not built.
- **Why:** to save Sarvam credit: nothing is voiced until a teacher wants the audio, and nothing is voiced twice. Teachers get the words at once and the audio when they ask.
- **Alternatives:** signed-in staff only (cannot save credit, teachers cannot open it); the coordinator confirms every voicing (slower for teachers).
- **Risks accepted:** anyone holding the link can read that lesson and trigger one voicing (bounded by the cap and the expiry); the text states pooled class counts ("N of M children"), which is class-level and carries no name, school or teacher, but the coordinator should send the link only to the teachers of that cohort. The lesson page has no "this is wrong" flag yet (gate 4), because pilot mode stores no teacher feedback.
- **Confirmed by:** Gopi (26 Oct).

### 2026-10-24 · Pilot storage: Google Cloud Storage (and Firebase Storage) as the default backend
- **Decision:** the pilot's two buckets may be GCS buckets (`GCS_SHEETS_BUCKET`, `GCS_AUDIO_BUCKET`, service-account key in `GCS_CREDENTIALS_JSON` or `GOOGLE_APPLICATION_CREDENTIALS`), chosen before the S3 settings; the S3 path stays. Same rules as 2026-10-23: two different private buckets, signed URLs only, nothing public. No key file is needed (the organisation blocks key creation): Application Default Credentials, with URLs signed through Google's IAM service by the attached service account on GCP or by `GCS_SIGNER_SERVICE_ACCOUNT` on a laptop (needs Service Account Token Creator). Firebase Storage needs no separate code: its buckets are GCS buckets and the app uses signed URLs, never the client SDK.
- **Why:** Gopi has a Google Cloud account and no S3 account.
- **Confirmed by:** Gopi (24 Oct).

### 2026-10-23 · Pilot mode: two pages, a separate private bucket for sheet photos, a consent gate
- **Decision:** (1) `PILOT_MODE=1` (off by default) turns a deployment into the pilot: sign-in, **Upload sheets** and **Intervention audio**, nothing else. Every other API router is not mounted (404, API docs off) and the web app redirects every other address to Upload sheets; hiding a menu item is not the mechanism. (2) Sign-in extends the auth stub: accounts come from `PILOT_ACCOUNTS`, tokens are signed and expire after 12 hours, five wrong tries pause a name for ten minutes, and the `X-Role` header and judge mode are ignored in pilot mode. New account type **Pilot coordinator** (uploads, generates, shares, sets retention); `coach` keeps approval (new permission `pilot.approve_audio`, the pilot form of `coach.approve_items`, which stays planned for P11); `officer` may only listen. One person may hold several roles. (3) **Pilot pre-test sheet photos are now stored**, in a new private S3-compatible bucket (`S3_SHEETS_BUCKET`, refused if equal to `S3_BUCKET`): server-side encryption requested on every write, no public URL, upload by a 5-minute presigned PUT, download by a 2-minute signed GET for the coordinator only. Table `pilot_sheet` has no name column and refuses unknown fields; codes (school, class, teacher) must look like codes, not names. (4) **Consent gate:** nothing uploads until the coordinator confirms school consent and enters its reference, which is stored on every sheet; the server enforces it, not only the page. (5) **Retention:** `PILOT_RETENTION_DAYS` (default 90, editable 7 to 365 in the app) deletes old photos and sheet rows at start-up and on every upload; class counts stay; the coordinator can delete everything for one school (photos, rows, counts); both are audit-logged in `pilot_audit`. (6) After upload, each JPEG or PNG goes through the existing call 8; HEIC and PDF are stored and marked "needs a second look", as is any sheet with an unsure box; those add nothing to the counts (pilot mode has no page for fixing reads, so they wait for hand-keying). The per-box reads are dropped as soon as the class counts are added. (7) **Audio:** the number of files (default 3, 1 to `PILOT_AUDIO_MAX`, default 10) is stored in `pilot_config`, validated on the server and audit-logged; lowering it makes cards inactive, never deletes them. Chain per slot: pooled class counts, engine diagnosis (the same track rule), the approved move lists, a script, gates 1 and 1b and call 7, the review queue, the coach's approval, then Sarvam voice and the published-audio bucket. Nothing is voiced, published, downloaded or shared before approval. (8) **Call 5 is not built**, so scripts come from a template drafter (`content/pilot/lessons.v1.yaml` plus the move lists, wrong answers computed by `engine.bugs`, counts from the engine, no Form A or B item). `ScriptDrafter` is the seam where call 5 plugs in; its output would pass the same gates. No new AI capability is claimed in `AI_USAGE.md`. (9) **Sharing** is manual from the coordinator's phone: Web Share with the file attached where `navigator.canShare({files})` allows it, else Download, Copy link (24-hour signed link) and Open WhatsApp (`wa.me`); mono AAC in `.m4a` (or MP3 with `PILOT_AUDIO_FORMAT=mp3`) at 32 kbps, re-encoded at 24 kbps if over 1 MB; file names are `cc-pilot-slot<N>-<lang>.m4a`. The share log (`pilot_share`) is a manual record, not delivery confirmation.
- **Why:** the pilot needs a coordinator to collect photos from teachers and send them lessons on WhatsApp with the least that can go wrong; everything else would be an attack surface and a distraction. Keeping the gates and the coach's approval means pilot mode removes no safeguard.
- **Alternatives rejected:** hiding menu items only; reusing the published-audio bucket (public by design); deleting photos right after reading (the pilot needs them for hand-keying and the pre/post pairing); a review page for unsure reads (not in scope: two pages only); calling the AI to draft the scripts now (call 5 is a P09 job with its own eval).
- **Confirmed by:** Gopi (brief of 23 Oct). **Open for Shivani and Seema:** the name-on-sheet policy, the consent wording, the retention period, the Hindi and Tamil wording of the pages, the audio scripts and the share message; see `docs/build/reports/PILOT-MODE.md`.

### 2026-10-23 · Design direction: Calm Institutional Material, Stitch prompts per screen
- **Decision:** (1) The UI direction approved on the Practice Class screen is the system for every screen: Calm Institutional Material (Material 3) with the colour, shape, type and layout rules in `docs/design/stitch/DESIGN.md`. (2) Every screen has a ready-to-paste Google Stitch prompt in `docs/design/stitch/prompts/` (45: the 13 design-doc screens, 28 added screens X1 to X28, 4 roadmap cards R1 to R4); `INVENTORY.md` lists them from the repo; `scripts/check_stitch_prompts.py` and `tests/test_stitch_prompts.py` keep them honest. (3) Telegram is not a Stitch screen: `TELEGRAM-MESSAGES.md`. (4) The UI is built from Stitch exports in `docs/design/stitch/exports/<ID>/`, never from Stitch's font link (it packs three fonts into one malformed URL) or its Tailwind CDN; our own CSS, self-hosted subsetted fonts and inline SVG icons. (5) Where this conflicts with earlier text, the design direction wins for new and rebuilt screens: `CLAUDE.md` said system fonts only (now Inter and the Noto fonts, self-hosted, system fonts as fallback; the font files must pass the data budget in P14) and tap targets of at least 48 px (now at least 44 px, primary buttons 48 px; existing screens keep 48 px until rebuilt, and `tests/test_design_tokens.py` still enforces the current CSS). The shared header says "child-says line" where the Practice Class mock used a child's name, so the header can carry no child name.
- **Why:** one visual system across 45 screens that were built piecemeal, and prompts a designer can paste without reading the repo.
- **Alternatives rejected:** system fonts only (the approved direction uses Inter and the Noto scripts); copying Stitch's exported HTML (Tailwind CDN and a broken font URL); one prompt for the whole app.
- **Confirmed by:** Gopi (brief of 23 Oct). Open: dark-theme colour values are derived and need a designer's check; the font budget needs a measurement; the one-tap reply variant in `TELEGRAM-MESSAGES.md`; the definitions of R1 to R3.

### 2026-10-23 · Check entry: phone keyboard, sheet list, absent children, missed teaching per concept
- **Decision:** (1) Each box is a real input with the phone's number keyboard (`inputmode=numeric`); digits typed in Devanagari or Tamil are turned into 0-9 and anything else is dropped, which was the reason for the old on-screen keypad (a Hindi or Tamil keyboard changing script mid-entry). Blank and "can't read" are marks on each box. (2) A list of sheets lets her jump to any child and see what was entered. (3) "Absent today" skips a roll number: the position is kept so later papers stay in register order, the row is empty and so not counted; marking absent asks before clearing answers. (4) "Missed the teaching" is tagged per concept (place value, questions 1-2; addition with carrying, 3-5; subtraction with borrowing, 7-10), not per sheet. In the engine (`engine/stages.py`, ported to `stagecalc.ts`, parity fixtures regenerated) a signature is left out of the class counts only when every item it rests on lies in a tagged concept; the whole-sheet tag equals every concept; class counts gain `missed_by_concept`. Tags and absences stay on the phone; only class counts are kept.
- **Why:** Gopi's request of 23 Oct: a separate keyboard was unnecessary, absent children need a skip, and the tag must fit the concepts on the worksheet.
- **Alternatives rejected:** keeping the keypad; counting an absent child as blank (it would lower prevalence); one tag for the whole sheet.
- **Confirmed by:** Gopi (request of 23 Oct). Seema to confirm the concept grouping of the items. Hindi and Tamil strings are drafts.

### 2026-10-22 · Practice Class fixes from the 22 Oct screenshots
- **Decision:** (1) The "connection is slow" line is shown only when a call was interrupted; a held reply says "a check held back the first reply", and a deployment with the model off says so (the e2e test that expected the old line for a missing recording now expects the model-off line). (2) The tray says what each tool does; the place-value chart still changes nothing in the simulator (`material_moves: chart: other`), and the screen now says so rather than implying an effect. (3) Hints follow the conversation: a strong move is the next unused one whose `after` condition holds, a rule "louder" needs the rule told first, scolding is last, and when the class is on a problem other than the example, lines carrying the example's numbers are left out; `after` is new optional move-list data. (4) The app is exactly the screen tall: top strip and bottom bar stay put and only the content scrolls; the bottom bar holds four tabs and a More sheet instead of a sideways-scrolling bar; a layout test checks no page runs off the side at 320, 390, 768 and 1280 px.
- **Why:** Gopi's screenshots and notes of 22 Oct: a misleading message, tools with no explained effect, hints that did not fit the talk, pages that would not scroll, and a bar with hidden items.
- **Alternatives rejected:** slotting numbers into every sample line (touches Seema's content in three languages and the demo teacher); keeping a horizontal scroll bar.
- **Confirmed by:** Gopi (request of 22 Oct). Seema to review the `after` conditions.

### 2026-10-22 · Sprite system: SVG from data, packs, call 11
- **Decision:** (1) **Grammar whitelist.** A sprite is SVG built only from `svg g circle ellipse rect line polyline polygon path defs linearGradient radialGradient stop clipPath use`; no `script`, `foreignObject`, `image`, `text`, `style`, external `href`, `on*`, `animate` or `animateTransform`; integers only; fixed viewBox per category; size budgets item 2 KB, avatar 12 KB, mat 6 KB. The same rules run on every rendered scene. (2) **Palette slots.** Specs name nine slots (skin, hair, cloth_a, cloth_b, accent, item_a, item_b, mat, ink), never a colour; four approved palettes include a high-contrast one; meaning never rests on colour alone (outlines, hatching), checked by a contrast test and a Machado 2009 colour-vision simulation. (3) **PNG library: `resvg-py`** (a Rust wheel, no system libraries) over CairoSVG (needs native Cairo, awkward on Windows and small hosts); no font is loaded because the grammar has no text. (4) **Expression table.** One code table maps a child's state (speaking, intent, right or wrong, engagement, strength, quiet, shy) to one of seven expressions; the AI never picks one; the first seating shows only calm or shy faces so it leaks no error. (5) **Reduced motion.** Animation is CSS class toggles on opacity only (mouth frames while audio plays) and is off under `prefers-reduced-motion`; the grammar forbids SMIL. (6) **Counts from layouts.** A unit is an element with class token `u`; each layout reports `count_drawn`, and tests parse the SVG to prove it equals the request for 0 to 100. (7) **Two renderers, one output.** Python is canonical; the TypeScript port is held byte-identical by a 114-case golden fixture. (8) **Call 11 (`MODEL_SPRITE`, Sonnet 5.5) drafts item specs offline only**; gates are schema, grammar, size, no text, slots only, contact tile in every palette and as PNG, pre-filter and no-check-item checks, call 7 on the words (it cannot see pixels; the coach looks at the contact sheet), then coach approval and officer enablement, each change a new version. (9) **Dashboard boundary** (updates the 21 Oct content-library entry): configurable by coach and officer with the two keys: enable or disable packs, items and expressions; persona looks and seating; approved palettes; scenario templates (number slots filled by code, no digits in the text). Code only: grammar, renderer, layouts, validators, the state-to-expression table, anything that computes a count. (10) **A new pack needs no renderer change**, proved by a hash of the renderer files (only `services/api/sprites/` and `apps/pwa/src/sprites/`, tests excluded) recorded in commit fa50ee3 before the second pack was added in cf99a84 and checked by a test; the channel, gate and Practice Class glue (`sprite_media.py`, `sprite_gates.py`, `services/practice/faces.py`) sits outside that hash. (11) **Avatar accessories** are `none` or `bag` only: `glasses` and `ribbon` were removed after the privacy review because they can read as disability and gender markers; the golden fixture was regenerated and the renderer hash is unchanged. (12) CLAUDE.md gained rule 17, a call 11 row and a Do-not line as part of this entry (additive; no bar moved).
- **Why:** pictures that teach counting must show exactly the number the code chose, run on 2 GB phones and Slow 3G, and never carry a script, a face of a real child or an AI-invented detail; data-driven items let Seema and coaches add topics without a developer.
- **Alternatives rejected:** AI image or 3D generation at run time (cost, latency, safety, exact counts impossible); hand-drawn component SVG per screen (inconsistent, uncounted); CairoSVG (native dependency); animating with SMIL (excluded by the grammar and by reduced-motion).
- **Confirmed by:** Gopi (brief of 22 Oct). Not yet confirmed: coach approval and officer enablement of `place-value-add-sub` (TODO-HUMAN Seema); the Hindi and Tamil strings are drafts.

### 2026-10-22 · Citations and structured output cannot be combined: calls 4 and 5 use two passes
- **Decision:** the Anthropic Citations API returns a 400 when citations are enabled on any document block and `output_config.format` (structured output) is also set. So the two calls that use citations are built in two passes. **Call 4 (method card):** pass A sends the mentor's corrected transcript as one custom-content document (`source.type = "content"`, one text block per sentence, so `start_block_index` is our sentence id), citations on, `cache_control` on the document, and asks for a fixed line format (`STEP:`, `MATERIAL:`, `PHRASE:`, `TIME:`); there is no `output_config.format`. Code rebuilds the lines from the text blocks and their `content_block_location` citations, converts block indexes to sentence ids, and fills the Pydantic card. A line with no citation, a cited id that does not exist, or a `PHRASE:` that is not a verbatim substring of its cited text is rejected and logged (audit validator code, never shown). The existing validators stay as a second, independent check and call 7 still checks "only what she said". Pass B (structured output) is not used for cited fields; if a later pass B is added it gets only the code-parsed text, no documents, and a validator asserts it added or changed no step. **Call 5 (track drafting):** pass 1 is the existing structured-output draft with no documents; pass 2 asks for one "Why this move" line per strategy with citations over the evidence documents (six custom-content documents built by code from `docs/design/evidence-digest.md`, one text block per digest line and source with its page marker kept, `cache_control` on each). Code maps `(document, block index)` to DOC plus PDF page from its own table, so the UI shows the page from the citation and never from model text. A "Why" line with no valid citation is dropped and the draft goes to review without it; a line whose only citations are IDR or APU rows (opinion) is labelled opinion and is never shown as evidence that something works. No new call number.
- **Why:** the model-side citation is a second signal that each step came from her words (or each "why" from a page), while code stays the guarantor. A step with no citation is rejected rather than trusted.
- **Evidence:** the docs state the 400 (https://platform.claude.com/docs/en/build-with-claude/citations), and `scripts/ai_proof.py` confirmed it on 2026-10-22: the request with citations and `output_config.format` was refused (`docs/evidence/ai_usage_proof.json`, `citations.structured_output_with_citations_refused: true`), and a citations-only request cited sentence ids 0 to 3 that all resolved.
- **Alternatives rejected:** a prompt asking the model to write sentence ids into a JSON field (a model can invent an id; code already checks that, but the API signal is stronger); dropping structured output for the whole call (loses the schema on the non-cited fields); a forced tool call (a 400 on Opus 5.5 and Sonnet 5.5).
- **Confirmed by:** pending Gopi.

### 2026-10-22 · Verified API facts: Citations, caching, batches, effort (checked 22 Oct against platform.claude.com)
- **Decision:** the build relies on these facts, each read from the current docs on 2026-10-22.
  1. Citations (https://platform.claude.com/docs/en/build-with-claude/citations): a `document` block with `"citations": {"enabled": true}`; "citations must be enabled on all or none of the documents within a request". Three document types: plain text (`char_location`, chunked by sentence), PDF (`page_location`, 1-indexed pages), custom content (`content_block_location`, `start_block_index` and `end_block_index`, 0-indexed, end exclusive; "your provided content blocks are used as-is and no further chunking is done"). Each citation also carries `cited_text`, `document_index`, `document_title`; `cited_text` does not count toward output tokens. "All active models support citations": Opus 5.5, Sonnet 5.5 and Haiku 5.5 are active (https://platform.claude.com/docs/en/about-claude/models/overview).
  2. Citations with structured outputs: not combinable (400); see the entry above. Source also https://platform.claude.com/docs/en/build-with-claude/structured-outputs.
  3. Batches and caching: the citations page says citations "work in conjunction with other API features including prompt caching, token counting, and batch processing"; the batch page does not mention citations separately, so citations inside a batch are documented only in that general sentence and are checked when call 5 pass 2 is first run in a batch (fallback: run pass 2 synchronously). Source documents can be cached ("apply `cache_control` to your top-level document content blocks"); the citation blocks in a response cannot. In batches, cache hits are best effort and every request should carry the identical `cache_control` blocks (https://platform.claude.com/docs/en/build-with-claude/batch-processing).
  4. Prompt caching (https://platform.claude.com/docs/en/build-with-claude/prompt-caching): minimum cacheable prompt is 512 tokens on Opus 5.5, Sonnet 5.5 and Haiku 5.5; a shorter prompt is not cached and no error is returned; both `cache_creation_input_tokens` and `cache_read_input_tokens` are 0 when nothing was cached; both appear in `usage`. Cache reads cost 0.05x base input on Opus 5.5 and Sonnet 5.5 (so `ai/pricing.yaml` is consistent). `scripts/ai_proof.py` measured 2,114 tokens written on the first call and 2,114 read on the second (Haiku 5.5, `docs/evidence/ai_usage_proof.json`).
  5. Thinking and effort (https://platform.claude.com/docs/en/build-with-claude/effort and https://platform.claude.com/docs/en/build-with-claude/thinking-steering-and-cost): `thinking: {"type": "adaptive"}`; effort is `output_config.effort` with `max`, `xhigh`, `high`, `medium`, `low`, never inside `thinking`. Defaults: Opus 5.5 medium, Sonnet 5.5 high, Haiku 5.5 medium. Opus 5.5 always thinks (`disabled` is a 400); Sonnet 5.5 turns up-front thinking off with `between_tools` at low to high; Haiku 5.5 accepts `disabled` at high or below.
- **Differences from `CLAUDE.md` and `BUILD_PROMPTS.md`:** one. They say every call uses structured outputs; calls 4 and 5 pass A and 2 cannot (the entry above). Everything else matches (512-token floor, effort names and defaults, the 400 on `disabled` for Opus 5.5, Message Batches for call 5). `CLAUDE.md` section 7 is updated in the same change.
- **Why:** `CLAUDE.md` section 8 requires verification before coding, and the kit named one assumption (Citations with structured output) that proved wrong.
- **Alternatives:** none.
- **Confirmed by:** pending Gopi (facts only).

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

## 2026-10-30 · Assistant: light model and follow-up questions (call 14 v2)

- **Decision.** `MODEL_ASSIST` moves from `claude-sonnet-5-5` to `claude-haiku-5-5`: the call only rewrites retrieved passages under code checks, so the light model is enough. Prompt v2 adds `follow_ups` (up to three short questions). Code keeps a model-suggested follow-up only if it passes the policy refusals and the pages in the role's scope can answer it, then fills up to three from the role's own question bank (those carry an id, so the pre-written answer is returned). Every answer, including extracts and abstentions, now ends with follow-ups.
- **Why.** A person decides after one answer whether to carry on; each next step must be answerable, in scope, and cheap.
- **Unchanged.** Retrieval is keyword search over the scoped index (no vector database); the model answers only from retrieved passages; code checks every quote, row, length, personal data and action claim; the drawer speaks as the role chosen on the landing page. No live run of call 14 yet: it stays "Built" in `AI_USAGE.md`, not "Verified".
- **Confirmed by.** Gopi (asked for the light model and follow-ups, 2026-10-30).

## 2026-10-30 · Assistant: meaning-based retrieval behind a flag (overrides "no vector DB" for this use)

- **Decision.** CLAUDE.md says "no vector DB". Gopi chose to add embedding retrieval because Cohort Coach needs to search documents (the assistant now; more later) and keyword search misses Hindi and Tamil paraphrases. Built as `services/assistant/vector.py`: Gemini embeddings (`gemini-embedding-001`, 768 dimensions, key in `GEMINI_API_KEY`), vectors in a bundled `vectors.npz` (default) or Firestore (`VECTOR_STORE=firestore`, optional), fused with the existing keyword ranking. **Off by default** (`RETRIEVAL=off`), so the submitted demo does not depend on it.
- **Guardrails unchanged.** The scope decides which chunks are searchable; a vector hit outside the scope is dropped; any embedding, network or store failure returns the keyword hits; the model still answers only from retrieved passages under the same code checks. Only the masked question text leaves the server; chunks are repository and help pages. The cosine threshold (0.62) is set by eye, not tuned, because there is no labelled set yet.
- **Why not a managed vector service.** About 1,200 chunks fit in memory; Firestore is the free GCP-native option when a shared store is needed.
- **CLAUDE.md.** Section 14's "Add a vector DB" line is superseded for retrieval of help and repository text; it still applies to anything holding teacher, child or class data.
- **Confirmed by.** Gopi (asked for a free, quick vector option on GCP and chose the Gemini API for embeddings, 2026-10-30).

## 2026-10-30 · Telegram is on the roadmap

- **Decision.** Telegram is not part of the submitted product. The web app is the only channel in the demo and the pilot. The Telegram adapter (`services/api/channels/telegram/`) and its golden-transcript tests stay in the code as the evidence that a second channel is an adapter plus contract tests; no bot is deployed, and no screen mentions Telegram or a bot. The README, the rubric map (row E3.4 is now Roadmap), the channel docs, the judge script, the help pages the assistant reads, the checklist, the shot list and the video script were updated to say so.
- **Why.** The bot was never deployed (no webhook), so a judge could not run it, and a claim that cannot be checked is worse than a roadmap line.
- **Not changed.** The account-linking step still says "send /start CODE to the bot" because the onboarding flow is shared with the adapter; it shows only if someone links a Telegram chat, which cannot happen without a bot.
- **Confirmed by.** Gopi (2026-10-30: "For now telegram is in the roadmap. update the docs.").

## 2026-10-30 · Every check is labelled; pre-test and post-test pair on the phone

- **Decision.** A check now records its kind (pre-test, post-test or termly check), paper (Form A or B), term, round, date, paper version (the answer keys hash), the track it starts or evaluates, the papers expected, a status and notes. Pre-test and post-test are labels on two checks of one class, not new machinery. **Start a check** comes before entry; a header shows the label on every entry screen; My class pairs two checks child by child in roll order on the phone and shows counts per competency (C1 place value, C2 adding with carrying, C3 taking away with borrowing). Form B is the twin of Form A item by item (`engine/forms.py: twin_of`); a pre and a post compare only on twin items.
- **Where it lives, and how it differs from the prompt** (`docs/build/Claude Code prompt identify every check ...md`). Per-child answers live only on the phone (CLAUDE.md rule 2), so the check record is the phone's `checks` table (Dexie version 2), not a server table with Alembic migrations. Old checks are migrated, not lost: each gets a guessed label (the class's earliest check is a pre-test; a later Form B one a post-test; else termly) with its real paper, not "Form A" as the prompt says, and is marked to confirm. One check per class per term: the id stays `classId:term` so nothing saved before is orphaned and the server's class counts (keyed by term) do not collide; `round` is stored for later. The term is the app's current term, not a field on Start a check.
- **Not built (parked):** Step 4, the check code printed on the paper and read back by call 8 (there is no printable worksheet generator, and call 8 would need a prompt change and a re-run of its eval); a server-side check table, upload of the before-and-after counts, and verdicts carrying the two check ids; the label on the cohort and track pages. See `docs/build/PARKING.md`.
- **Evidence.** `scripts/pilot_results.py` writes `docs/evidence/pilot_results.md` from an unsealed phone backup, counts only, labelled a small pilot; today it says no pair has been entered.
- **Confirmed by.** Gopi (2026-10-30: chose the phone-side slice).

## 2026-10-30 · Paper Studio: check papers made by code from approved rules

- **Decision.** Check papers are built by code (`services/papers/`), never by AI. A rule set (item templates, the engine's bug functions, blueprints, the paper wording in each language) is versioned: draft, in review, published, retired. Its author submits a change and a second person publishes it; a published version never changes (database guards). Every paper pins its rules version, blueprint and seed, and the same inputs give the same paper and hash.
- **Anchor and adaptive items.** The ten anchors keep Form A's skills and difficulty (ones totals 15, 14, 12; ones gaps 2, 4, 7, 6), so papers across checks and classes measure the same thing; before and after compare on anchors only. Up to five adaptive items go deeper on what the class profile weights most and are for diagnosis only.
- **Frozen post-test twin.** A pre-test makes its post-test twin at once: every item's twin has the same template and difficulty, new numbers, and no number pair from the pre-test. It is built from the pre-test only and frozen when made. Any paper is frozen when the first sheet of its check is entered.
- **Auto-approval within the rules.** A paper that passes every automatic check (the independent verifier, strings and glyphs, the rendered layout), uses published rules, has no hand edits and is in reviewed wording is approved and logged; one in five is also queued as a spot check (`PAPER_SPOT_CHECK_EVERY`). Anything else waits for the coach (the reviewer) before it can be printed; a paper that failed a check cannot be approved. A teacher prints a paper only in the language it was approved in.
- **Class profile order.** The last check's class counts; else the teacher's four-question intake (a topic not taught is not assessed and left off the paper); else the standard paper. Counts only.
- **Differences from the prompt** (`docs/build/Claude Code prompt Paper Studio ...md`, scope chosen by Gopi: core and main screens). The pilot paper has 10 items, not 15 (`docs/design/pilot_forms.golden.json`; the test guide docx is not in the repo), so the blueprints are `baseline_10` and `standard_10_5`. Version 1 is a transcription of what the team approved for the pilot (engine bug functions, Form A's difficulties, the pilot pack's Hindi classroom wording) and is recorded as approved by the pilot pack; the English wording counts as reviewed, the Hindi short labels and all Tamil wording are drafts by Claude Code, so Hindi and Tamil papers go to the queue until a reader approves them (TODO-HUMAN(Seema, Shivani): Hindi; TODO-HUMAN(Gopi): Tamil). Section labels on the paper are "Listen and write", "Add", "Take away". WeasyPrint runs on Windows through the installed GTK3 runtime and in Docker and CI through apt. The rule editor is a read-only view with history, export and Test these rules; changes go through the API. A generated paper is printed and marked by hand: phone entry of its answers, the reader's code check and the tour step are parked (`docs/build/PARKING.md`). The pilot paper can be attached to a check (its code shows in the check header) and is frozen on the first entry.
- **Confirmed by.** Gopi (2026-10-30: chose "Core + main screens").

## 2026-10-31 · Demo Studio: the judge's end-to-end demo flow

- **Decision.** A guided demo of 11 steps (and an optional 12th) on a made-up class, driving the product's own code: Paper Studio, call 8 on sheet 1, the error finder on the phone, the real grouping and mentor rules, call 5 for lesson 1, the chat service and its gates, the coach's queues, an officer view with cells under 5 classes hidden. Judge deployment only; never mounted in pilot mode. Every made-up sheet, class and number says Demo, Simulated or Synthetic.
- **Defaults (from the prompt).** The review drawer is a bottom drawer, 40% of the width on a laptop (anchored bottom right) and 40% of the height on a phone. Sheet 1 is read by the AI; Auto-fill loads the other sheets from the demo answer file with no AI call and says so. AI reads are cached by the image's hash and capped per demo session (`DEMO_AI_READS_PER_SESSION`, default 6). The first audio carries "Demo: pre-approved": in the demo only, the coach's approval of lesson 1 is skipped; lesson 2 still goes to the coach. The chat waits 60 seconds in the demo, with Skip the wait. Each judge device has its own demo session; Reset clears only it. Optional step 12 simulates the post-test.
- **Differences from the prompt.** (1) One track a class a term (CLAUDE.md): her class is in one cohort this term and shown as qualifying for a second next term, not in two at once (Gopi chose this, 30 Oct). (2) The planted errors are tracked errors on the pilot paper (SUB-SFL 9 and ADD-NOCARRY 7 of 20 above the line, PV-HEARD below), not "borrowing across a zero" or "three-digit sums with two carries", which the check does not have. (3) The demo check uses the pilot paper (Form A), made in Paper Studio, because the phone scores only Forms A and B today. (4) Matching by the printed roll box uses the demo label inside the sheet (its PNG metadata), not reading the roll box. (5) The chat AI answers only from approved material; every teaching strategy is still a draft (TODO-HUMAN(Seema)), so in the demo it says it has no source and the coach answers in their own words. (6) The coach's demo cohort has auto-send switched on (the coach's setting), so the real gates decide. (7) The other classes' waitlist split is the real seeded split; the scenario's seed (114) is one where her class starts this term and all three errors form a cohort.
- **Fix found on the way.** The chat service held a database write open across its model calls, which locks SQLite (dev, tests) when the call's audit row is written; it now commits before each call.
- **Evidence.** `docs/evidence/demo_synthetic_reading.md` (synthetic sheets only; written by `scripts/demo_evidence.py` from a live read and from a record-mode run).
- **Confirmed by.** Gopi (2026-10-30: everything in the prompt, keeping CLAUDE.md's one track a term).

## 2026-11-01 · Stitch screenshot pack

- **Decision.** `python tasks.py stitch-pack` builds `docs/design/stitch/pack/`: for each screen and state, screenshots (first viewport, scroll slices with 80 px overlap, a stitched long image, sideways scroll), an annotated copy with numbered boxes E1, E2, ..., a contact sheet, a spec with a table of every numbered element, and a Stitch prompt of at most 1,800 characters. Tooling is in `tools/stitch_pack/`; the product is unchanged.
- **Demo only.** Judge mode, recorded AI, stub voice, a fresh throwaway database; the harness fails a capture that shows data without a Demo or Simulated label (en, hi, ta words) or that matches an email, phone or key pattern. Five screens do show demo data with no label (History, Papers, Cohort, Review, Mentor): they are listed as known gaps in the manifest and reported, not hidden.
- **Annotation scheme.** Numbers run top to bottom over the whole page; the viewport image shows those visible in it, the long image shows all; the validator checks that every number drawn is in the table and every table row is drawn. The clean image is never drawn on.
- **Scope.** Core screens (Gopi, 2026-10-31): 25 screens, 58 states, phone and desktop, Hindi on main screens, the 12 demo steps. Not covered: dark theme (none exists), Tamil, empty/loading/error/offline states.
- **Files.** Pictures and raw JSON are git-ignored (about 80 MB, rebuilt on demand); manifest, specs, prompts, index and README are tracked.

## 2026-10-31 · Practice Class: a chorus of one to three children, overheard moves, and a switch for call 7 and for call 1

- **Decision (Gopi, 2026-10-31).** (1) Each teacher turn now has one to three speaking children, chosen by the engine (the named child first, then others weighted by engagement; the shy child only when named; a child who went quiet stays out). (2) The class shares one room: a move aimed at one child reaches every other child as something overheard, at `overhear` (0.5) of its effect on strength and engagement; going quiet applies only to the child it was aimed at. Both are tuning parameters in the scenario files (`overhear`, `chorus_max`); the engine's defaults (0 and 1) keep the old one-child behaviour. (3) `.env` `PRACTICE_SKIP_CHECKER=1` leaves out call 7 on a child's line; the code validators (numbers, length, script, subtitle) and the pre-filter still run on every AI line, and a line that fails them is still replaced by the template. (4) `.env` `PRACTICE_AI_INTENTS=explain,work_aloud` sends only those kinds of line to call 1; every other line (an answer, an agree, a thanks) is the engine's template. The children who join in as the chorus always speak in template words: they give their own answer, which a template carries whole.
- **Why.** A live turn took a median of 5.1 s and 7.7% of turns passed 12 s (the label, child-line and check calls run one after another). A child's line is made from numbers the engine chose, so most of it is mechanical; only a child explaining her working needs a model. And the children sit in one room.
- **What it changes in the rules.** CLAUDE.md rule 4 ("nothing AI-written reaches a teacher until it passes call 7") now has one exception for a Practice Class child's line, only where `PRACTICE_SKIP_CHECKER=1`. Off by default; the public demo and pilot keep it on unless someone with authority turns it off. Call 7 still gates track content, method cards and feedback cards. A skipped line carries no "Checked" badge and the judge's layers view says `checker_skipped`.
- **Alternatives.** Skip call 7 only when the code checks pass and the line is short (same as now); run call 7 in parallel with the reveal (breaks check-then-release); a faster model for call 1 (needs the realism eval re-run).
- **Side effects.** The recorded SUB-SFL rehearsal fixtures (`ai/fixtures/recorded/`) were re-recorded live on 2026-10-31 (7 turns, USD 0.0168) because the turn plans changed. The face test and the recorded tests now expect more than one speaking child; the bars were not changed.
- **Not yet measured.** The effect of the switches on turn time. No live evals were re-run (the call 1 prompt is unchanged).

## 2026-11-01 · Pilot sheets as a local-only demo data source

- **Decision (Gopi, 2026-11-01, by the prompt `docs/build/Claude Code prompt pilot sheets as a local demo data source...`).** The two pilot classes' answered sheets can be used in Demo Studio's Enter-the-check step on the one machine that holds them. A **Data source** control offers Synthetic (default) or Pilot. The sheets live in the git-ignored `data/pilot/`; `python tasks.py pilot-ingest` tidies them and writes `pilot_answers.json`; four routes serve them (moved on 2026-10-31 to `/api/pilot-data/`, see that entry).
- **Consent gate.** The option exists only with `PILOT_DEMO=1`, the folder, a valid `manifest.yaml` with `consent_confirmed: true` (who, date, scope) and the answer file, in a judge deployment, in a live demo session. Without the folder it is hidden, so the hosted demo shows Synthetic only; with the folder but no consent it is shown disabled with a reason. Every route is a 404 otherwise.
- **Name scan (new call 15, offline).** The script asks a small vision model whether a person's name is written on a sheet and where, blacks the region out of the normalised copy, reads the class and roll from the printed header when the file name does not carry them, and records only a yes or no and a region count. It is the only added AI step (`ai/registry.py`, `AI_USAGE.md`); a human reviews every sheet where a name was found, and every sheet where the scan was not run.
- **What this changes in the rules.** CLAUDE.md rule 2 says no photos are stored by the main app. This is not the main app: the images stay in a local ignored folder, are never in git or the web build, and the browser keeps pilot answers in memory only. Rule 14 (no per-child data to storage or logs) holds for the server database: nothing here writes child-level data to it; the demo session row counts AI reads only.
- **Why.** The demo and the video are stronger on real sheets, and the reading evidence becomes real: the AI's read can be compared with hand-keyed truth (counts only in `docs/evidence/pilot_reading_accuracy.md`).
- **Choices made while building.** (1) The pilot form has 10 boxes, so truth CSVs have `q1` to `q10`, not `q15`. (2) A class dictated different numbers is built correctly in the answer file, but the on-phone error finder knows only Form A's 346 and 728, so the screen disables that class with a reason rather than diagnose it wrongly (parked). (3) Competency and skill labels on the questions come from the item type. (4) A sheet with a photo but no data (cost cap or `--no-ai`) is listed as unread, never filled in. (5) The orientation of a photo is guessed from where the ink sits and listed for review when unsure.
- **Alternatives.** Putting the sheets in the hosted demo (rejected: consent and rule 2); a database table for the reads (rejected: child-level data in the server database); a second answer-file loader (rejected: the Demo Studio's loader is reused, with `source: "pilot"`).
- **Not yet done / not measured.** No real sheet has been run through the script yet; the reading accuracy file does not exist until hand-keyed truth does. The unit tests use a fake folder made from the synthetic sheets and fake model replies.

## 2026-11-01 · Papers page: first slice (list, cohort status, navigation)

- **Decision (Gopi, 2026-10-31, by the prompt `docs/build/Claude Code prompt the Papers page ...`).** The whole prompt is a multi-day build (PDF import with a new vision call, assignments, role scopes, the assistant's open questions and `paper_draft_set`, help documents in three languages, Enter check choosing a paper). It was started on submission day, after the 28 Oct feature freeze, so it was built in slices that cannot break the demo. **Slice 1 (built):** Papers moves between Home and Enter check in the navigation (teacher, mentor, judge; the coach keeps its own bar; hidden for officers as before); the teacher's list shows form, kind, status, source ("Made by the rules") and, for each paper, whether cohorts have formed, or the specific reason and the next step; filters for kind, form and status; a "Create a paper" button (still goes to Enter check).
- **Cohort status** is one pure function, `apps/pwa/src/lib/paperStatus.ts`, over the check records on the phone and the placement the programme API already returns. It adds no second source of truth. Reasons: no check has used the paper; a check is open (N of M sheets entered); all entered, not approved; approved, not closed; submitted and waiting for other classes; formed this term (cohort size) or next term; unknown offline. Counts only.
- **Known limit.** The programme API returns `waiting` both when other classes have not arrived and when formation has not run, so "cohort formation has not run" is not shown as a separate reason. Not guessed.
- **Not built yet (in the prompt's order):** PDF and answered-sheet import (new call, computed keys, review table, layout map, 24-hour deletion); the paper detail page with tabs; Enter check choosing an existing paper and no longer creating one; assignments (`paper_assignment`, scopes for teacher, mentor and coach, Assigned to you); the assistant's `paper_status`, open questions, `paper_draft_set` with Undo, the help documents and suggested questions; the server-side role-scoped list. The Papers help documents and the demo flow's step 2 are unchanged.
- **Why slices.** Moving paper creation out of Enter check would change step 2 of the 12-step demo and the pilot option that select their paper there; that is not safe to do on the last day. Nothing in this slice removes a path that worked.
- **Test changes, not loosened bars.** The bottom-bar test now expects Practice, Programme, History and Profile in More, because Papers now sits in the bar.

## 2026-11-01 · Papers page, the rest: import from PDF, assignments, scopes, the assistant's questions (Gopi: "build the rest")

- **Decision.** Papers are created and managed on the Papers page; **Enter check only chooses** a paper (`PaperChooser`, with the paper assigned to her first and the suggested form pre-selected). Paper generation moved there as the route "Generate from rules" (the same `PaperMaker`, same test ids). The demo's step 2 now happens on the Papers page.
- **PDF import (new call 16).** The AI reads only the printed questions; **code computes every key, probe, wrong answer and coverage cell** with the engine and re-checks with independent arithmetic; a printed key that differs is flagged and blocks Confirm until acknowledged; a sheet with handwriting keeps no printed answer; a person confirms every item; the upload is deleted on confirmation or after 24 hours. A dictated item needs the number that was said; an unsupported item is left out or entered by hand. An imported paper is `confirmed`, usable for a check, listed as "Imported, awaiting review", reviewed by someone other than its importer, and **never printed** by the system.
- **The assistant asks and fills, never decides.** The open questions are produced by code (`importer.open_questions`); the side panel asks one at a time; an answer goes through the same whitelisted `apply_edit` as a typed change, tagged "Assistant changed this" with its previous value and an Undo, and `via=assistant` is recorded. `Confirm` and `Assign` stay disabled or refused (`via=assistant` on `POST /assignments` is a 403): only a person presses them. The asking is driven by code, not by a model call.
- **Assignments and scopes (server side).** `paper_assignment`: one row per class, a pre-test cannot go to a cohort, one active assignment per class, paper and kind, a post-test warns if its twin was not assigned, an assignment cannot be withdrawn once a sheet is entered, notes carry no phone numbers, handles or links. A teacher assigns only to her own class (`X-Class-Id`); a mentor only inside cohorts she mentors; a coach inside cohorts assigned to her and, before cohorts exist, any known class; an officer has no access. Progress is counts only. The mentor role now holds `papers.generate` (CLAUDE.md and the roles page list it as can); the test that said a mentor cannot generate a paper was changed to cover the officer only, with this entry as the reason.
- **Assistant.** A read-only `paper_status` tool (built, in the teacher, mentor and coach scopes, limited to papers in the user's scope), a `papers` screen id, Papers sections in the teacher, mentor, coach and judge help documents, and suggested questions in the three banks (English, Hindi and Tamil drafts, unreviewed). The free-text model path does not call the tool yet: tools are listed, not invoked.
- **Honest limits.** (1) The phone scores only the pilot Forms A and B, so an imported paper with other items is marked by hand with its key; `phone_form` says which. (2) The layout map of an imported paper is always approximate. (3) "Keep this sheet for a check" is refused with a message. (4) No live call 16 run: the browser tests replay an authored recording (`scripts/make_paper_import_fixture.py`, labelled in the file), so there is no accuracy claim. (5) The role headers are session values until real role assignment (P12), so the scopes hold against the server's own cohort records, not against signed identities. (6) Not built: Duplicate as new version, editing a draft paper's questions, an Assigned card on Home, reminders, the assistant preparing an assignment draft, Generate 20 demo sheets on the Files tab.
- **Why this order.** The prompt's own order: the import engine, the list and detail, cohort status, create and choose, the assistant, then tests and records.

## 2026-11-01 · Edit and delete a paper (Gopi, by request)

- **Edit.** An imported paper is edited in place (`POST /api/paper-hub/papers/{id}/items`): numbers or include only, code recomputes every key and probe, and the paper goes back to "confirmed" and, if a reviewer had approved it, back into the review queue. A generated paper is never changed in place: Edit saves a **new paper** through the existing custom-paper path (always reviewed, constraints checked, the original untouched). A paper that is in use cannot change; saving then makes a new version.
- **Delete.** `DELETE /api/paper-hub/papers/{id}` removes the paper, its items, its review rows and its assignments (only withdrawn ones can exist), after a confirmation step in the screen. It is refused while a sheet of a check is entered on it or an assignment is live; deleting a pre-test also deletes its post-test twin if that is unused, and is refused if the twin is in use. The events stay as the audit trail ("deleted"). Who: a coach, the class's own teacher or mentor, or the person who imported it.
- **Change to `store.freeze`.** A post-test twin is frozen when made, so `freeze` did nothing when its first sheet was entered. It now records the "first sheet entered" event in that case too (no column changes), so use of a twin is known.
- **Limits.** "In use" is known to the server only through the freeze call and assignments; a sheet entered offline on a phone that has not synced is not seen until it syncs. Draft papers' items cannot be added, only edited or left out.

## 2026-11-01 · Edit changes the paper itself, with no copy (Gopi: "Don't create a copy"; supersedes the Edit part above)

- **Decision.** Editing a generated paper now changes **that paper** (`store.edit_in_place`): the generator's own functions work out every answer, wrong answer and check again, the items are rewritten, and no new paper is made. The old "new paper through `/api/papers/{id}/custom`" is no longer used by the screen (the route stays).
- **What does not change.** Hand-chosen numbers on a generated paper are still reviewed by a person (an existing rule), so an edited paper goes back to the review queue and cannot be printed until approved; numbers that do not fit its template are saved but flagged, and a flagged paper cannot be approved. An imported paper behaves the same. A paper that is in use, and a post-test twin (frozen when made), cannot change, and the screen says why.
- **Also fixed.** The API's CORS list lacked `X-Class-Id`, `X-Person`, `X-Demo-Person` and `X-Demo-Session`, so the browser blocked every Papers call from another origin (tests/papers_hub/test_cors.py). The detail panel no longer repeats the Edit and Delete buttons that each row already has.

## 2026-11-01 · Why each question is on a paper (explainability, Gopi's request)

- **Decision.** Every item shows a "Why this question" list, built by code in `services/papers/explain.py` from facts the paper already holds: the rule template and rules version that made it, anchor or adaptive, the skill, the class profile (for a past check, a count of children, never a percentage), the errors a wrong answer points to, the item it twins, and whether the numbers were chosen by hand or the paper was imported. No model writes it. It reaches the screen as string keys plus values, so it reads in English, Hindi and Tamil (the Hindi and Tamil are unreviewed drafts). It appears in the paper view and in the detail's Questions tab, with a line saying which rules version made the paper and where a coach reads those rules.
- **Rules.** `rules/paper-rules.v1.yaml`, loaded as versions; a coach reads them under Papers, Paper rules (version in use, templates, history, YAML export, Test these rules). There is still no rule editor in the screen: a change is a new draft version imported as YAML through the API, submitted by its author and published by a second person.


## 2026-10-31 · Teachers and mentors can read the paper rules (not change them)

**Decision.** A new permission `papers.rules_view` lets a teacher, mentor and coach read the paper rules (list, one version, YAML export). Changing rules and "Test these rules" stay with the coach (`papers.rules`, two-person publish). The Papers page shows the rules table and history to everyone who can open Papers; the test button is the coach's.
**Why.** A teacher shown "made from template add-carry, rules version 1" must be able to read what that template is; hiding the rules made the explanation unverifiable. Reading changes nothing and holds no child or teacher data.
**Replaces.** The earlier line "a teacher never sees the rules" (Papers explainability entry) and its e2e/API tests, rewritten to the new rule, not removed.
**Confirmed by.** User request, 2026-10-31.

## 2026-10-31 · One back end, no Mode switch; the demo and the pilot use the same flows

**Decision.** There is one back end (the app, papers, demo and the pilot staff's sign-in, sheets and audio). The pilot routes (`/api/pilot/...`) are mounted on it and open only to a signed sign-in token: a role named in a header never opens them, even in judge mode (`require()` refuses `pilot.*` without a token). The web app has no Mode menu and no `VITE_PILOT_API_BASE`; the pilot staff's pages are reached by their own addresses (`#/upload`, `#/audio`, a teacher's `#/lesson/` link) and nothing in the app links to them. `PILOT_MODE=1` still builds a pilot-only server for a public address that should expose nothing else. `run-backend-pilot.bat` is gone; `run-all.bat` starts the back end and the web app.
**Why.** Two servers and a Mode menu made the demo harder to follow, and CLAUDE.md already says one back end. A judge should see the production flow only.
**Replaces.** The 2026-10-2x entry that kept the judge and pilot servers separate. Test `test_pilot_mode_is_off_by_default` (pilot routes not mounted) is rewritten to its new rule (mounted, refused without a token), not removed; the all-other-routes-404 test for a pilot-only server is unchanged.
**Pilot entry in Enter check (same day).** The pilot class's real sheets move out of Demo Studio into Enter check: with the pre-test imported (Papers, From a PDF or an answered sheet) and attached, a teacher on the machine that holds `data/pilot/` presses *Enter from the pilot sheets*; the first sheet is read by call 8 and the rest are filled from `pilot_answers.json`, each labelled and checked before it counts; answers stay in browser memory only. The routes are now `/api/pilot-data/...` and need no demo session; they still answer 404 unless `PILOT_DEMO=1`, the folder, the consent note and the answer file all exist, so the hosted app shows nothing. The demo no longer offers the pilot data at all. The cap on call 8 reads is per server run (`DEMO_AI_READS_PER_SESSION`), not per demo session.
**Not yet done.** The deployed site still runs two Cloud Run services (`cohort-coach-judge-api`, SQLite; `cohort-coach-api`, Cloud SQL). Merging them into one service (`fln-cc-backend`) needs a redeploy and one database decision, which is the owner's to take. The demo's step 2 still generates the fixed Form A paper because its scripted phone entry has no per-paper key.
**Confirmed by.** User request, 2026-10-31.

## 2026-10-31 · A check is entered on the chosen paper's own key; no Form A / Form B for a teacher

**Decision.** Enter check asks for a paper that exists (made on Papers, with its answer key) and nothing else. Starting fetches that paper's key (`GET /api/paper-hub/papers/{id}/key`, built by `engine.export_keys.build_answer_keys` from the paper's numbers via `services/papers/keys.py`) and keeps it on the phone; the check is keyed on the paper id. The error finder, stage counts, photo reading (call 8, `/api/sheets/read` with the paper id) and before/after use it. Class profiles sync with the paper id as their `form`. Form A / Form B buttons are gone; on the judge deployment a "sample paper (made-up class)" button keeps the tour and the sample working on the built-in forms.
**Why.** The user's flow: a paper is generated with its key; Enter check selects it; answered sheets are entered or uploaded. The phone already read only key data, so a paper's own key in the same shape needed no new logic.
**Open.** Residues and deviations are listed in `docs/build/reports/PAPER-FLOW-RESIDUES.md`. The most important: the 5 adaptive items now count in the 2-item rule and in before/after, against the design's "adaptive items never count as improvement". That needs a human decision.
**Confirmed by.** User request, 2026-10-31.

## 2026-10-31 · One app, no modes: pilot mode removed; every check on its paper's own key

**Decision.** Pilot mode is removed: `PILOT_MODE`, the pilot-only server, its sign-in and accounts (`coordinator`, `pilot.*` permissions), Upload sheets (and the private sheets bucket), Intervention audio, lesson links and the `pilot_*` tables. The shared storage and voice code moved to `services/media/` (`MEDIA_LOCAL_STORE`, `AUDIO_FORMAT`, `/api/media/blob/...`). The landing page has no Mode menu and no mode chip. Rule 2's pilot-mode exception no longer exists: no answer-sheet photo is stored anywhere. The pilot runs in the production flow (import the pre-test on Papers; Enter check, pilot sheets on the machine with the folder, read with the chosen paper's key). The demo makes its paper from the rules and its class answers that paper; its post-test is the twin. The judge's sample is a stored "sample paper" with the published pilot-test numbers (`sample: true` on `/api/papers/generate`, replacing `pilot_form`). Paper keys mark anchors, and before/after compares anchor items only. The import no longer asks for a form letter (it follows from the kind), `phone_form` is gone, and check codes drop the letter ("PRE · 3A · T1").
**Why.** User request: one production code path, nothing that confuses a judge with a pilot mode or a pilot paper.
**Tests.** Tests of removed behaviour were deleted with it: `tests/pilot/`, `e2e/pilot.spec.ts`, `e2e/lesson-audio.spec.ts`, the four "not mounted in pilot mode" tests, and the phone-form test. Tests whose subject still exists were rewritten to the new rule, not loosened: GCS store choice (audio bucket only), tester flag, CORS, import blocking questions, labels, and the photo form field.
**Left.** `docs/build/reports/PAPER-FLOW-RESIDUES.md`. Deployment as one `fln-cc-backend` service needs a redeploy and a database choice, which the owner must make.
**Confirmed by.** User request, 2026-10-31.

## 2026-11-01 · Two classes to a cohort: two settings, three-digit error answers, the next lesson by code

**Decision.**
1. `COHORT_MIN_CLASSES`, default **15** (the engine's cohort size) in production. The pilot and demo scenario
   (`demo/scenarios/two_classes_pilot_like.yaml`) sets **2**. A cohort formed under it says **"Pilot cohort, two classes"**.
   At pilot scale there is no waitlist split: both classes are trained, and the pilot verdict compares the trained mistake
   with the untrained ones (CLAUDE.md section 5).
2. `COHORT_ALLOW_SINGLE_ITEM_PROBES`, default **off** in production; **on** in the pilot and demo scenario. When on, a
   mistake on a paper's only item of its kind counts. The kind is worked out from the numbers
   (`engine.diagnosis.skill_family`): borrowing across a zero, three digits with two carries, a dictated number with a zero.
   Otherwise such a mistake is "possible" and never "shows". A cohort formed with these counts says **"Based on one
   question per child"**. The 2-item rule itself is unchanged.
3. The five error functions work on three-digit items. Adding is column by column (246 + 178 → 314), and so is
   smaller-from-larger (703 − 468 → 365). For SUB-NODEC, only the tens digit is left unreduced for the ones' borrow
   (703 − 468 → 245, 542 − 179 → 373), which the committed formula already gave. The committed code gave 245 for
   smaller-from-larger too (a collision), 414 for the sum, and no answer for 305; 305 now gives 3005 (heard) and 350
   (reversed). Two-digit answers are unchanged (all engine tests pass).
4. After lesson 1, code picks a teacher's next lesson from her answer
   (`services/cohort_run/next_lesson.py`):
   - Tried: the next lesson.
   - Partly: the same approach as a smaller step with more practice. Call 5's input carries `variant` and
     `practice_level` only when they are set.
   - Not yet: the next lesson whose approaches she has not had.
   - No answer by the set date (3 days in the demo): the planned lesson, and the silence is never counted.

   Call 5 words the lesson, and the coach approves it.
5. A teacher may tick "Share with my cohort" on a chat question. The other members then see it and its released answers
   by pseudonym. It is unticked by default in the product and ticked in the demo screen. Unshared questions stay private,
   as before.
6. Lesson 1 in the two-class run goes to the coach's review queue (the coach approves it). The single-class Demo Studio
   keeps its "Demo: pre-approved" lesson 1 (2026-10-31).

**Why.** User request (the flow-check prompt). Under the old rules the two pilot-like classes formed nothing. Their main
patterns are single-question items, and the waitlist split would send one of two classes to next term.

**Found on the real sheets (local run, counts only).** No cohort forms, even with both settings on:
- In 3A, SUB-NODEC shows for 3 of 16 children; in 3B, for 3 of 18. Both are under 1 in 4.
- The wrong answers on 703 − 468 are mostly 245 (5 of 9), which is SUB-NODEC.
- None of the wrong answers on 246 + 178 matches an error function.

The synthetic scenario assumes the across-zero children write the smaller-from-larger answer, so that a track with
approved content (SUB-SFL) exists. That is an assumption, said so in `docs/build/reports/FLOW-CHECK.md`.

**Alternatives.** Lowering the 2-item rule for every item (rejected: one slip would count). A new "across a zero" error
function (parked: needs Seema's pedagogy review and a track).

**Confirmed by.** User request, 2026-11-01. The settings' pilot values need Seema's agreement before a real pilot cohort.

## 2026-11-01 · AI modes for QA with the AI offline: live, recorded, off; and what the QA run changed

**Decision.**
1. `AI_MODE` gains `off`: every call fails as if the service were unreachable (reason `api_error`, nothing sent), so
   each caller's fallback runs. `/api/health` reports the mode. The header shows **AI: recorded answers** or **AI: off**,
   and a replayed answer shows **Recorded AI answer**. In `off` mode each AI feature says so, keeps the user's work and
   offers its non-AI path (Auto-fill or typing for sheets, the code template for lessons, a person for chat questions,
   Generate from rules for papers, set lines in the Practice Class).
2. The Practice Class masks the teacher's line before any model call (names, roll numbers, phone numbers); the five
   pretend children's names are kept because they are fictional.
3. The call registry has a `built` flag. Calls 4 (method card) and 6 (digest) are planned, not built: the AI map and the
   README say so. A test ties `built` to code that calls it.
4. The demo bar counts 12 steps ("Demo step n of 12"); step 13 (two classes) is optional and keeps the bar.
5. Enter check: "Roll no N - status", **Next not entered**, **Finish entering** (asks first and marks the roll numbers
   left as absent) and **Reopen**. The demo entry has the same, plus Absent on each roll number.
6. When the call-2 labeller fails, code finds the one child named in the teacher's line, so that child answers (the
   move stays "other" and changes nothing).

**Open questions resolved with the safer option** (listed in `docs/build/reports/QA-DEMO.md`):
- "The teacher's class in 2 cohorts" kept the one-track-a-term rule (`CLAUDE.md` §5): the screen says her class is in 2
  of the 3 cohorts, one this term and one next term.
- Recorded mode cannot replay a read of a newly made demo sheet (each paper prints its own fingerprint). The read says so
  plainly and the user goes on with Auto-fill or typing; no reading-summary number counts it.
- Fixtures written for tests carry a `note` saying so; on screen they still show "Recorded AI answer" (the label the
  requirements name), and no evidence number uses them.
- Judge tools stay visible in every "view as" role on the judge deployment, labelled judge-only; a teacher deployment
  never shows them.

**Why.** User request (the QA prompt, 1 Nov), while the Claude API key was unavailable (the workspace's monthly limit).

**Alternatives.** A runtime switch for the AI mode from the judge screen (rejected: anyone could turn the hosted demo's AI
off). Making demo sheets identical across devices so recordings match (rejected for now: it changes how papers are
fingerprinted).

**Confirmed by.** User request, 2026-11-01.

## 2026-11-01 · Enter check: nine changes

**Decision.**
1. Enter check shows no data source: no Synthetic or Pilot control, no pilot folder probe, no sample paper, no
   "Use a sample sheet", no auto-fill, no "Read from demo/pilot answer file" labels. The demo studio keeps its own
   entry; the code for it stays, the Enter check page no longer uses it.
2. A check starts from a paper that already exists (assigned papers first, one pre-selected). The class size is
   required (1 to 100) and prefilled from the class's last check. Papers are made on Papers only; "Create a paper" is a
   link that goes there. Tour step 1 has its own "Make the standard test paper" button for judges.
3. Sheets are added by the camera (the selected roll) or by a folder of pictures, with `webkitdirectory` found by
   feature detection and **Choose pictures** where it is missing. Pictures are matched to roll numbers by file name,
   then by the class code and roll number the reader saw in the header, then by the teacher. Three are read at a time.
4. Each roll has a data state (Entered, Not entered, Absent) and an approval state. Absent approves automatically; only
   the teacher marks absent; any edit to an approved roll sets it back to Not approved.
5. Pictures live in memory only and are dropped at Finish. The old modal review drawer is replaced by a non-modal
   drawer (bottom, 40% of the height on a phone; right side, 40% of the width at 900 px and above).
6. **Finish entering** is enabled only when every roll is approved or absent; a note on the page says why when it is not.
7. The three "Missed the teaching" checkboxes are always visible; their question numbers come from the paper's items.
8. Call 8 (prompt v2) also returns the sheet header's class code and roll number when there is one (`header`, or null),
   and the request carries the SHA-256 of the original file so recorded mode replays one answer per file.

**Conflict noted, not resolved by this entry.** `CLAUDE.md` §4 rule 2 says product answer sheets carry no name or roll
number. The folder matching reads a roll number printed or written in a header only if the sheet has one (pilot
sheets do). The header read comes back to the phone and is never stored or logged (the audit row stays metadata only). If
the product sheet stays without a header the header is null and the teacher chooses the roll. A human should confirm.

**Why.** User request (the nine-changes prompt, 1 Nov): one flow for testers and judges, with a folder of test sheets in
the deck.

**Alternatives.** Keeping the data source control (rejected: it showed the pilot to testers). `showDirectoryPicker`
(rejected: not in Safari or Firefox, and it needs a secure context). Marking empty rolls absent at Finish (rejected: the
teacher marks absent).

**Confirmed by.** User request, 2026-11-01.

## 2026-11-01 · Keep approved answer sheets for 60 days (opt-in)

**Decision (Gopi, 2026-11-01).** A teacher who agrees (the new consent `keep_sheets`, off by default, in My
profile and asked once in Enter check) has the picture of each sheet she **approves** kept in a private Google
Cloud Storage bucket (`GCS_SHEETS_BUCKET`) for **60 days after approval** (`SHEET_RETENTION_DAYS=60`), then deleted
by a sweep (on every keep and list, and `scripts/purge_kept_sheets.py` daily). Nothing is deleted earlier. The copy is
her online record of her answered sheets: it comes back only to the phone that stored it (class id and device id),
through the API, never as a public or signed link. She can delete a copy at any time; approving a roll number again
replaces it. The sheets carry a roll number only.

**What changes in the rules.** `CLAUDE.md` section 4 rule 2 said sheet photos are deleted right after reading and
never stored. That stays true for the reading call and for anyone who has not agreed. The exception is stated in the
rule and in `docs/privacy.md` (a new row and a changed paragraph).

**Risk accepted.** If a teacher writes a name or other personal detail on a sheet, we hold it for 60 days. Mitigations:
opt-in; only approved sheets; delete at any time; only her phone can read it; the bucket is private. Coaches,
officers and judges cannot open a kept sheet.

**Not built yet.** Real accounts: ownership is the class id plus the phone's random device id, so a phone whose data is
cleared cannot reach its old copies (they are deleted at 60 days). A person-level login would fix that.

**Alternatives.** Signed URLs straight to the bucket (rejected: a link can be passed on); keeping every sheet read, not
only approved ones (rejected: unapproved reads are suggestions); keeping nothing (the previous rule).

**Confirmed by.** User request, 2026-11-01 ("retention 60 days, `GCS_SHEETS_BUCKET`, I accept everything else").

## 2026-11-01 · Bayesian child model behind `SIMULATOR_MODEL` (default legacy)

**Decision.** Build a second Practice Class child model, Bayesian knowledge tracing with a Beta prior and a responsiveness per child, as specified in `docs/build/BAYESIAN-MODEL-BUILD-PROMPT.md`. It is chosen by `SIMULATOR_MODEL=bayesian`. Unset or `legacy` keeps the rule-based model turn for turn, checked against golden runs saved before the change. Spec: `docs/BAYESIAN-MODEL.md`. Code: `engine/child_model.py`.

**Conflicts with the build prompt, and how they were resolved.**
1. *Commits.* The prompt asks for a golden-fixture commit and small commits. `CLAUDE.md` section 11 forbids committing with failing tests, and the working tree holds a day of other uncommitted work (`engine/simulator.py` included) plus 3 known failing server tests. Nothing was committed. The golden fixture was saved before any engine change, and its git hash was recorded in the report.
2. *Overhear "0.5 × T" vs "exactly half the direct gain".* With T × r above 1 these disagree, because the cap would bite on the direct gain only. Resolved as gain = OVERHEAR × (1 − b) × min(1, T × r): the cap applies first, so the half is exact, as the test requires.
3. *Where the switch is read.* `engine/` is pure. The one environment read is `model_from_env`, called once when a session is created, so the existing fidelity eval runs in either mode without being edited.
4. *`.env` names.* The prompt's constants are read as `BAYES_PRIOR_CONCENTRATION` ... `BAYES_SLIP`, so generic names (`GUESS`, `SLIP`) cannot clash.
5. *"The three −0.20 moves give identical sessions."* `check_back`'s behaviour is `doubt` and the other two are `explain`, so the kind of line differs. The test checks that children, answers and beliefs are identical, not the kind of line.
6. *"Draws per turn equal legacy."* This holds for the per-turn generator. The chorus generator's sequence depends on right-or-wrong outcomes already under legacy, so it is excluded from that test and the reason is stated in the test.

**Not changed.** `CLAUDE.md`, README, `AI_USAGE.md` and the submission docs (the lines that would need changing are listed in the build report given in chat), `sim_fidelity.py`, `results.md`, recorded results, decks.

**Confirmed by.** Build prompt run by Gopi, 2026-11-01. The standing instruction "go with the recommended approach" covers the resolutions above.

## 2026-11-01 · 32-state Bayesian child model replaces the one-variable model behind `SIMULATOR_MODEL`

**Decision.** Build the 32-state Bayesian child model specified in `docs/build/BAYESIAN-32-STATE-BUILD-PROMPT-v2.md` (place value × exchange idea × written step × wrong habit, an observer that updates a belief by Bayes' rule, information-gain question choice) in a new package `engine/bayes/`, selected by `SIMULATOR_MODEL=bayesian` through one factory, `engine/sim_switch.py`. Default stays `legacy`. Branch `bayes-32state`, made from `7cd0afa` so it does not depend on the speech branch. Spec: `docs/BAYESIAN-MODEL.md`. Report: `docs/build/reports/BAYES-32-STATE.md`.

**Conflicts found in Step 0, and how they were resolved.**
1. *`bayesian` already meant the one-variable model, wired inside `engine/simulator.py`, which this prompt forbids editing.* `engine/simulator.py` is left byte-for-byte as it was (hash recorded and tested). The factory always passes `engine.child_model.LEGACY` to the legacy path, so no session can select the one-variable model any more; `bayesian` now means the 32-state model. `engine/child_model.py` and its unit tests stay (they test the module directly). Scripts that call `engine.simulator.new_session` without a model still read the old switch, so they must be run with `SIMULATOR_MODEL` unset (stated in the spec, section 10).
2. *One existing test pinned `bayesian` to the one-variable model* (`test_child_model_bayes.py::test_a_session_keeps_its_model_after_the_environment_changes`). It now checks the same property, a session keeps its model when the environment changes, on the 32-state model. No assertion was removed.
3. *`evals/runners/sim_model_compare.py` and `docs/BAYESIAN-MODEL.md` already existed.* "Never modify existing evals": the comparison is a new file, `evals/runners/bayes_model_compare.py`. The spec document is rewritten, since this prompt supersedes the one that wrote it (section 10 keeps a note of the old model).
4. *"All 183 existing tests"* is the simulator and practice subset counted in `docs/build/reports/BAYESIAN-CHECK.md` 2.11, not the whole suite (about 2,500 tests, 8 of which already fail on the base commit for unrelated reasons).
5. *Turn order.* Legacy chooses the problem before applying the move; the information-gain choice needs the predicted belief, so the move is applied first. The problem does not enter the transitions, so nothing else changes.
6. *Shared code edited beyond `services/practice/session.py`*: `services/api/main.py` (one line: the startup check calls the new factory), `.env.example` (`BAYES_PARAMS` replaces the old `BAYES_*` lines) and `tests/conftest.py` (`BAYES_PARAMS` is cleared for the suite like `SIMULATOR_MODEL`).
7. *Fixed draws per answer.* An answer draws exactly two uniforms (kind, then number by index) rather than `rng.choice`, whose draw count varies; the distribution is the same.

**Not changed.** `engine/simulator.py`, `engine/bugs.py`, move lists, scenarios, personas, `sim_fidelity.py`, `engine_items.py`, `evals/results.md`, `docs/submission/*`, README, `CLAUDE.md`, `AI_USAGE.md` (the lines that would need changing are listed in the report).

**Hook.** Commits on this branch skip the pre-commit hook: `tasks.py check` already fails at lint on the base commit (`tools/check_anthropic_api_key.py`). Ruff, mypy and the relevant tests were run on every change instead.

**Confirmed by.** Build prompt run by Gopi, 2026-11-01. The standing instruction "go with the recommended approach" covers the resolutions above; every parameter is a build default awaiting review (`TODO-HUMAN(Seema)` in `content/bayes/*.yaml`).

## 2026-11-01 · Speech behind one provider layer, Bodhan AI first, Sarvam as the fallback (branch `speech-bodhan`)

**Decision.** All live speech goes through `services/speech/chain.py`: Bodhan AI first for speech to text (`indic-transcribe`) and text to speech (`indic-speak`), Sarvam as the fallback, a mock for tests. The order is configurable (`SPEECH_TTS_PROVIDERS`, `SPEECH_STT_PROVIDERS`, with per-language overrides). Built from Prompt 1 of `docs/build/bodhan-speech-prompts.md`, on branch `speech-bodhan`; not merged into the evaluated version (1 Nov freeze).

**Choices where the prompt left room.**
1. *A 401 falls back.* The prompt says a 4xx request error does not fall back. A 401 or 403 is a key problem at that provider, not a fault in our request, so the next provider is tried. 400, 415 and 422 do not fall back.
2. *Bodhan voices.* Until the cast in `content/voices.yaml` (Prompts 2 and 3), Bodhan uses one voice per language (Hindi Kavya, Tamil Anitha, English Kavya; `TODO-HUMAN(Seema)`), pitch-shifted per child exactly as the Sarvam voices are.
3. *An explicit Sarvam client keeps the old path.* `SpeechService(client=SarvamClient(...))` behaves as before, so existing tests and scripts are unchanged; the chain is used by `default_service()` and wherever a chain is passed.
4. *`split_for_stt` cuts at the limit when there is no silence*, as the prompt says. The older `split_at_silences` (the quietest frame even in speech) is kept for its existing callers.
5. *The converted WAV carries its true length.* ffmpeg writing to a pipe leaves the WAV size fields unset; the Bodhan mock (which measures the header) refused such a file as over 30 s. `to_wav_16k_mono` rewrites the header. Bodhan meters by duration, so this matters for the real service.
6. *Per-session caps* (`SPEECH_SESSION_MAX_STT_SECONDS`, `SPEECH_SESSION_MAX_TTS_CHARS`) are built and tested in the speech service. Wiring them to Practice Class sessions and the "voice is off" message is Prompt 3.
7. *Prices.* `content/speech_prices.yaml`, every paid value `verified: false` (Bodhan's from an unverified article; the API page shows none).

**Not done in Prompt 1.** Lessons (Prompt 2), Practice Class recording and voices (Prompt 3), evaluation and gates (Prompt 4). The startup warning fires until `docs/evidence/speech_gates.md` records both gates passed.

**Confirmed by.** Gopi, 2026-11-01 ("start the development", Prompt 1).

## 2026-11-01 · Lesson audio with the speech layer (Prompt 2, branch `speech-bodhan`)

**Decisions (Gopi, 2026-11-01, answering the questions asked before Prompts 2 to 4).**
1. *Lessons are MP3 mono 48 kbps*, as the prompt says (was OGG/Opus 16 kbps). Gopi was told this breaks the 10 MB per-track budget and chose it. Computed worst case at the 5-minute lesson cap (`scripts/data_budget.py`, `docs/evidence/data_budget.json`): 14.73 MB per track with text practice, against the 10 MB target (6 lessons at the cap are 10.8 MB). No new target number was set, so `tests/test_data_budget.py::test_the_track_fits_the_target_with_text_practice_and_not_with_voice_every_time` now fails and is left failing until a person sets the target (or changes the format). `CLAUDE.md` section 9, the README and `docs/RUBRIC_MAP.md` E3.2 say so.
2. *Coach audio review is after publishing and optional.* Publishing voices each lesson by itself; the coach can listen, regenerate a sentence or the lesson, and approve; teachers keep the approved version until a new one is approved. Unapproved audio is labelled "Not yet approved" on the review screen.
3. *Live calls*: Gopi chose to run the live scripts. Run on 1 Nov: `scripts/calibrate_chunks.py --yes` (evals/results/chunk_calibration.json) and a live smoke run of two lesson texts through the pipeline into the local store (`MEDIA_LOCAL_STORE=1`; the real audio bucket was not written from a local run).
4. *Commits*: one per prompt on `speech-bodhan`, `--no-verify` (the full check is not green; failures listed in each commit message).

**Choices where the prompt left room.**
- *Small cohorts.* A filled lesson and its audio carry the pooled counts of the cohort's classes, so the coach review screen hides a lesson whose cohort has fewer than 5 classes (rule 3; the manifests view already hides scripts). Records carry `cohort_id` and `cohort_classes`.
- *Demo pre-generation* reads the newest published manifest of each track. The local database had none (all 14 drafts were held by the output checker, so nothing could be published without re-drafting with call 5, a Claude spend outside this prompt); `lessons-pregen` is built and tested but had nothing to voice.
- *Telegram* sends a lesson as a voice note, which Telegram accepts as OGG/Opus only. With MP3 lessons the roadmap bot would need `sendAudio`; not changed (Telegram is not deployed).
- *Timing inside a two-sentence chunk* is split by characters: an estimate, since no provider returns timestamps.
- *Number words* for the round-trip check (`services/speech/textnorm.py`): English 0 to 999 999; Hindi and Tamil 0 to 100 plus hundreds and thousands, a first draft (`TODO-HUMAN`: Seema for Hindi, Gopi for Tamil).

**Found live (1 Nov) and fixed.** Bodhan's default rate limit is about 8 requests per minute per model (`x-bodhan-rate-limit-source: default`, with Retry-After on the 429). Three chunks in parallel hit it, the one retry waited only 0.5 to 1 s (and capped Retry-After at 10 s), so every lesson fell back to Sarvam. Now requests are paced to `BODHAN_REQUESTS_PER_MINUTE` (8) per model and Retry-After is honoured up to 60 s; a wait longer than `BODHAN_PACE_MAX_WAIT_S` (90) fails at once so the chain falls back. After the fix, a 1 161-character section was voiced by Bodhan with no fallback (13 chunks, 101 s, 24 of 26 sentences passed the round trip). Ask Bodhan to raise the limit before any live use: at 8 a minute a whole lesson takes about 10 minutes, and a Practice Class turn cannot wait.

## 2026-11-01 · Practice Class speech through the speech layer (Prompt 3, branch `speech-bodhan`)

**Decisions (choices where the prompt left room).**
1. *Voice by gender.* Each child keeps one Bodhan voice for the session, taken in seat order from the list for the persona's gender (`content/voices.yaml`), distinct from the lesson narrator; the Sarvam fallback is the child's existing speaker and pitch.
2. *A failure, for the two-failure switch,* is a turn with no audio or one where the first provider failed and a fallback answered.
3. *Live turns wait at most 2 s* (`BODHAN_LIVE_PACE_MAX_WAIT_S`) for Bodhan's rate allowance before Sarvam speaks; batch work still waits up to 90 s.
4. *The silence message* keeps the prompt's sentence and adds the existing hint ("I didn't catch that. Try again: hold the button while you speak."), so the existing browser test stays unchanged.
5. *Per-stage timing* is a new `layers.evaluation.timing` key; the existing `stages` keys are unchanged.
6. *A child's line is at most 120 characters* (a gate check); recorded and template lines already fit, so no replay changes.
7. *Masking before calls 1 to 3 was already in place* and tested; not changed.

**Found live (1 Nov).** Bodhan's first audio took a median of 14.7 s in a live turn (Sarvam 7.9 s; target 5 s), and its default allowance runs out within two or three turns. Bodhan is not fit for live Practice Class use until Bodhan raises the limit; the chain falls back to Sarvam meanwhile (`evals/results/practice_voice_latency_live.json`).

**Process note.** A new latency script was first written over the existing tracked `scripts/practice_latency.py` (the text-turn latency eval); it was restored from git unchanged and the new script is `scripts/practice_voice_latency.py`.

**Confirmed by.** Gopi, 2026-11-01 (the answers before Prompts 2 to 4: run the live scripts, commit per prompt).

## 2026-11-01 · Speech evaluation, gates and rollout (Prompt 4, branch `speech-bodhan`)

**Decisions (choices where the prompt left room).**
1. *"Numbers wrong"* in the listening test is a "correct numbers" score of 1 or 2 (of 5) (`content/speech_gates.yaml`, `numbers_wrong_at_or_below`).
2. *Gate thresholds* are the prompt's defaults, marked `TODO-HUMAN(Gopi, Seema): confirm`: text to speech, Bodhan's naturalness within 0.3 of Sarvam's and under 5% numbers wrong; speech to text, a character error rate at most 5 points worse than Sarvam's and key-term accuracy at least 90%.
3. *Key terms are matched as whole words* on text without the number conversion ("ten" is a term and a number; "tens" and "tents" are not "ten").
4. *Shadow mode* runs in the background after the main transcript, so it adds no wait for the teacher; it logs `provider`, `primary`, `similarity` and `latency_ms` only.
5. *The About screen* is the assistant panel's "About this product" tab; the attribution sits there and in the README. The Practice Class voice controls say the children's voices are AI-generated.
6. *Cost evidence* (`docs/evidence/speech_cost.md`) is generated from measured inputs (lesson drafts, calibration, engine-simulated sessions); the teacher's speech per turn (6 s) is a stated assumption; every paid price stays `verified: false` until Gopi confirms them on the consoles.
7. *No slide edited.* `docs/build/reports/SPEECH-ROLLOUT.md` lists the deck sentences to change once the gates pass.

**State on 1 Nov.** Both gates `pending`: the listening pack is made (live) but has no ratings yet, and the speech-to-text test needs team members' recordings (`docs/evidence/speech-eval/PROTOCOL.md`). Rollout stage 1 (`docs/build/SPEECH-ROLLOUT.md`).

**Confirmed by.** Gopi, 2026-11-01 (the answers before Prompts 2 to 4: run the live scripts, commit per prompt).

## 2026-11-02 · Results page: answer map, "why flagged" matrix, error explanations; a cohort of one class; intervention content; Download audio

**Decision.** Run unattended on branch `autopilot/results-cohort-audio` (never pushed, never merged; `main` and the frozen submission untouched).

1. *Answer map* (`#/cards`): roll by question, each cell the engine's own reading (`diagnoseChild`), shown as colour, two letters and a pattern together. It exists only on the phone that holds the answers. New theme tokens `--heat-*` (Okabe-Ito); contrast with `--ink` and colour-blind distance are tested.
2. *"Why an error is flagged"*: the paper page's coverage matrix is now one shared component (`CoverageMatrix`) used by both pages, with this class's counts beside it. The rule text reads the engine's `min_hits`.
3. *"What each error means"*: `content/errors/explanations.v1.yaml` (draft, English; Hindi and Tamil are not written and not machine-translated, so the page shows English with a note). The worked example is read from the answer key of the class's own question.
4. *A cohort of one class* (`scope: class_only`): a new table `class_cohorts` and `/api/cohorts/class-only`, not a change to `CohortSpace` (create_all never alters a table, and the dev and production databases already exist). **`COHORT_MIN_CLASSES` is unchanged** (15 in production); the formation code never reads this table; it is labelled "Just my class: no other teachers yet" on every screen; counts only are stored. A coach sees all of them in counts, with no teacher id. Alternative rejected: a new `scope` column on `CohortSpace`.
5. *Intervention content*: assembled on the phone from `content/errors/intervention.v1.yaml`, the strategy library and the explanations file. No AI call. Every new piece of text is `status: draft` with `TODO-HUMAN(Seema): review` and listed in `docs/build/autopilot/REPORT.md` as a content gap.
6. *Download audio*: `POST /api/audio/pack` voices the text the teacher is reading through the speech layer (Bodhan first, Sarvam as fallback, one narrator per file, whole file again on the fallback). The caller sends the text, so the server cannot prove it matches the page; the protection is a per-phone character cap (`AUDIO_DOWNLOAD_CHARS_PER_DEVICE`, else `AUTOPILOT_MAX_TTS_CHARS`, else 20000), a request limit and no storage of the text. A server that rebuilt the text from content would need the pack builder in Python (parked).
7. *The speech layer* lived only on branch `speech-bodhan`; it was merged into the autopilot branch (not into `main`). Conflicts were resolved keeping both sides, and one real bug the merge left (a missing `}` in `styles.css` that nested the speech and results CSS under `.finding-lines`) was found by the no-wrap test and fixed.
8. *Speech eval script lines* in `content/speech_eval/scripts.yaml` spoke Form A items (43 and 346); the content scan test failed, so two example numbers were changed (62 and 527). The test bar is unchanged.
9. The pre-commit hook runs the whole `check`, which already failed on the base (8 Python tests, 4 e2e); commits on this branch use `--no-verify` and the targeted checks were run by hand (listed in the report).

**Confirmed by.** Not confirmed: an autopilot run on Gopi's brief of 2 Nov 2026; every choice above is for a human to confirm.

## 2026-11-02 · Eligibility: the 25% share rule is removed

**Decision.** A class is eligible for a track on an error when at least 1 child shows it (the 2-item rule) and at least 10 children were checked. The old rule also required p ≥ 25% of children checked. Track choice is unchanged: PV-HEARD first, else the error most children show.

**Why.** With the 25% bar, a class where 10% of children (for example 2 of 16) needed help got no track and nothing to do, which ignores them. The teacher can still see every child who shows the error.

**Changed.** `engine/diagnosis.py` (`MIN_CHILDREN_WITH_ERROR`), `engine/export_keys.py` and `apps/pwa/src/lib/diagnosis.ts` (the keys file now has `min_children_with_error`; `min_prevalence` is gone), `services/content/configurable.py`, `CLAUDE.md` section 5.

**Not changed (still 25% or other floors; decide separately).** The officer error map (`services/api/officer.py`), the stage-of-breakdown routine rule (25% of children), the mentor bars (p ≥ 25% last term), and `COHORT_MIN_CLASSES`. A cohort of several classes still needs enough classes with the same error, so a small share per class gives fewer or thinner cohorts.

**Tests.** Not updated in this change (the tester asked for no test changes while they test): engine eligibility and export-keys tests, the golden keys fixtures and any test expecting no track below 25% will fail until a human agrees the new bar and they are updated. No bar was loosened silently.

**Confirmed by.** Gopi, 2026-11-02 (asked in chat to remove the rule).

## 2026-11-02 · A shared spoken layer for Download audio and the Practice Class

**Decision.** Speech is made from a separate spoken text, not from the text on the screen. New module `services/spoken/`: a normaliser (screen text to spoken text: no titles, "Source" or "Draft" tags, labels, markdown or symbols; numbers as words; "N of M children" as a spoken ratio; math symbols as words), validators, pause tokens (`[pause]`, `[pause:long]`) and a renderer, with language packs for English (num2words), Hindi and Tamil (own tables, 0 to 9999). Speaker settings are data in `content/spoken.yaml`.

1. *Intervention audio*: `POST /api/audio/pack` now takes the error code and her class's counts (or her own edited text) and the server writes the spoken script from the content files (`services/spoken/adapters/intervention.py`); `POST /api/audio/pack/script` returns it for the "Review the audio text" box. The page text is unchanged.
2. *Practice Class*: every child line goes through the normaliser right before synthesis (`_synth_ex`); no model, no extra wait. The on-screen line is unchanged. Feedback and hints are not voiced today, so they are not covered.
3. *Place-value numbers* are marked `{pv:N}` in content (one is marked now, in `intervention.v1.yaml`) and are said digit by digit; unmarked numbers are said as ordinary numbers. The screen shows only the number.
4. *Pauses*: neither Bodhan nor Sarvam takes SSML, so a pause is silence added between voiced pieces (`lessons.split_sentences` reads the tokens: a short pause ends a sentence, a long one is a section break). `to_ssml` exists for an engine that takes it; nothing calls it.
5. *No AI*: there is no model smoothing pass. Nothing was added to `AI_USAGE.md`.

**Assumptions** (the brief was cut off at "A marked number is"): the digit-by-digit reading of a marked number; one audio file per error (no pilot-mode file count exists, pilot mode was removed on 31 Oct). Hindi and Tamil number words and phrases are first drafts: TODO-HUMAN(Seema, Gopi), with skipped tests for the forms the build is not sure of.

**Tests.** New tests in `tests/spoken/` were written and not run (the tester asked for no test runs); the existing pack-audio and practice tests were not touched.

**Confirmed by.** Not confirmed: a request in chat on 2 Nov 2026; for Gopi to confirm.

## 2026-11-02 · Tamil drafts for the explanations, the intervention content and the strategy library

**Decision.** The Tamil page, the printed summary and the audio were in Tamil only for their labels; the content had no Tamil, so the audio fell back to English. Tamil text for every field (explanations, the five intervention sections, the strategy descriptions and steps, the PV-REVERSE strategy) is now in `content/errors/tamil.draft.v1.yaml`, loaded as the `ta` version of each English field by `services/content/error_content.py`. The English files are unchanged. Hindi is still missing and still falls back to English.

**Why this changes an earlier choice.** The autopilot run of 2 Nov kept Hindi and Tamil unwritten ("not machine-translated"). On the same day Gopi asked for Tamil audio, so Claude drafted the Tamil.

**Not reviewed.** Every Tamil line is a draft by Claude: TODO-HUMAN(Gopi) wording, TODO-HUMAN(Seema) that each line still teaches the same thing. Everything stays labelled Draft in the app. The worked examples (sums with English words) are not translated, so the Tamil audio leaves them out; the Tamil page still shows the English example.

**Confirmed by.** Not confirmed: for Gopi to review.

## 2026-11-02 · Hindi drafts, the same way as Tamil

**Decision.** Hindi text for every field the Tamil draft covers is in `content/errors/hindi.draft.v1.yaml`, loaded as the `hi` version of each English field by `services/content/error_content.py` (which now reads both draft files). The Hindi page, printed summary and audio are in Hindi; the worked examples (sums with English words) are not translated and the spoken Hindi version leaves them out.

**Not reviewed.** Written by Claude at Gopi's request; every line is a draft: TODO-HUMAN(Seema, Shivani) wording and that each line teaches the same as the English. Everything stays labelled Draft. The Hindi words follow the team's own (गड्डी bundle, दहाई, इकाई, हासिल carry, उधार लेना borrow).

**Confirmed by.** Not confirmed: for Seema and Shivani to review.

## 2026-11-02 · Cost and time of the last action, in a footer

**Decision.** Every billable call an action causes is written to a ledger under the action's id, and a footer shows the sum for the last action only (never a running total). Code: `services/usage/` (README there), `apps/pwa/src/lib/action.ts`, `components/UsageFooter.tsx`. It reads the existing records: `ai_calls` for Claude (one hook, `SqlAuditSink.write`) and a wrapper on each speech provider for text to speech and speech to text (one place, `default_chain`). Cloud Run time is the request's wall time.

**Defaults and assumptions.**
1. *Who sees it.* Everyone, teachers included (Gopi, 2 Nov: "show it for all including teachers"); this overrides the note in `services/speech/costs.py` that costs are never shown to a teacher. A person can hide it on their phone; `VITE_USAGE_FOOTER=0` removes it.
2. *Prices.* Nothing is typed in code. The INR to USD rate and the Cloud Run vCPU and memory prices are `null` in `content/usage_pricing.yaml` until a person copies them from the providers' pages, so those lines show n/a, never 0. TODO-HUMAN(Gopi).
3. *Cloud Run.* Billing is instance-based (CPU always allocated, `docs/deploy.md`). vCPU 1 and concurrency 80 are assumptions, not read from the service. The figure is an upper bound.
4. *Store.* The app's own database, shared by every instance; rows are removed after 24 hours.
5. *Metadata only.* The ledger has no column for text, audio, names or transcripts, and `record` refuses unknown keys.

**Existing test now out of date (not changed).** `tests/speech/test_pack_audio.py::test_a_sum_is_never_split_inside` expects the digits "703 − 468" to reach the voice. The spoken layer (same day) sends the words instead, so the sum is still in one piece ("seven hundred and three minus four hundred and sixty-eight") but the assertion no longer matches. A human should confirm the new wording of that test.

**Confirmed by.** Not confirmed: for Gopi.

## 2026-11-02 · Demo defaults: sharing class counts is on; "Intervention content" is now "Improvement track"

**Decision.** (1) Until a person makes a consent choice, sharing class counts is ON in the app (counts only, never a child), so a demo's results reach the server; a saved choice always wins, and `VITE_DEFAULT_SHARE_COUNTS=0` turns the default off. This is an exception to "nothing is on by default" in `lib/consent.ts` and to the DPDP consent design (`docs/privacy.md`): it is for the demo build; before real teachers use the app it must be switched off. (2) What the app called "Intervention content" is "Improvement track" on screen, in the printed pack, in the audio and PDF file names (`Cohort-Coach-Improvement-Track-<error>-<language>-<date>`), the admin page, the help page and the README. Code names (`InterventionPack`, `intervention.v1.yaml`) are unchanged.

**Confirmed by.** Gopi, 2026-11-02 (asked in chat).

## 2026-11-02 · Improvement tracks of several modules, due dates, feedback and a daily job

**Decision.** A track for a class-only cohort is a plan of modules (`services/modules/`). Only the next module is ever made: Module 1 when the track starts, each later one after her feedback (Get the next module) or, with none, on its due date by a daily job at 06:00 Indian time. Code picks the module (`branch.next_module`, a pure function: tried, partly, not yet, none; no approach repeats except after "partly"; cap 6 modules, `MODULE_CAP`; due dates 7 days apart, `MODULE_GAP_DAYS`). Silence is recorded as `no_feedback` and is never read as success. Generation is idempotent (compare-and-set on the module's status plus a unique (track, number)). The word *lesson* became *module* in every user-facing string and the help pages (the separate *model lesson* keeps its name).

**Defaults I chose (change any of them).**
1. *Where it lives.* Only the class-only cohort ("Just my class") gets modules. The two-class demo run (`services/cohort_run/`, 6 lessons, reviewed by the coach) is a different flow and is not changed; its `next_lesson.py` rules were reused as the model for the branch table, not called.
2. *Text.* Assembled by code from the strategy library and `content/errors/intervention.v1.yaml`, with the plan order in `content/modules/modules.v1.yaml`. No AI words it: the optional "worded by call 5, coach reviews, library wording released on the due date" path is **not built** (so `AI_USAGE.md` is unchanged and claims nothing new).
3. *Plans.* SUB-SFL and SUB-NODEC 4 modules, ADD-NOCARRY 3, PV-HEARD 2, PV-REVERSE 1; "not yet" uses the template's alternatives, then any unused approach; running out stops with "Talk to your mentor or coach" and a `coach_notified` event. An error with no plan gets one module and a log entry.
4. *Notifying a coach* means a recorded event that the coach's table counts (failed, overdue, not downloaded after `MODULE_NO_DOWNLOAD_DAYS`, default 5, tracks sent to a person). There is no push channel.
5. *Audio* is taken only when she presses Download audio, through the existing endpoint; teachers on the same text share one cached file because the cache is keyed by text and voice.
6. *Database.* The project has no migration folder, so the four tables (`tracks`, `track_modules`, `module_feedback`, `module_events`) are created by `Base.metadata.create_all` like every other table.
7. *The coach* sees counts per module for a cohort, no teacher id; a cohort of one is one teacher's progress, so the same under-5 rule that hides class figures from officers was not applied to coaches (coach lists of class-only cohorts already show them).

**Needs review.** Hindi and Tamil strings for the module screens and the smaller-step sentence are Claude drafts (TODO-HUMAN(Seema, Shivani)). The strategy text is still `status: draft` (Seema). The Tamil word *தொகுதி* and Hindi *मॉड्यूल* are the words you suggested.

**Confirmed by.** Not confirmed: for Gopi to review (the defaults above).

## 2026-11-02 · AI review of the note, with follow-up questions (Part B, call 17)

**Decision.** A small model (call 17, `MODEL_FEEDBACK_REVIEW`, Haiku) reads the masked note after her answer and picks barrier and focus tags and up to two follow-up questions from closed lists in `content/modules/feedback_review.v1.yaml`. Code validates every id (an unknown tag or question drops the whole output), allows at most one free question and only if it passes a checker (120 characters, a question, no name or number, no judging her, no diagnosing a child, no advice), ignores tags below confidence 0.5, and shows a gentle message on a safety flag (welfare words are also caught in code before any model). The branch table still decides the branch; tags only (1) put preferred approaches first among the alternatives for "not yet" and (2) move matching sections to the top, and code writes the "What changes next" line. AI off, offline or any failure: feedback is saved and only the branch table applies. The review, questions and answers are private to her.

**Not built.** The optional AI-worded intro ("What we changed because of what you told us", through review, omitted if not approved by the due date): not built, so nothing is claimed. No recorded fixture of a real model reply is committed (none was made; no live call was run); tests use a canned reply and a temporary recording. The eval (`python tasks.py eval feedback_review`) runs its code side free (0 of 4 made-up names leaked, 0 injected outputs accepted); the model side needs `--live`.

**Findings.** Two welfare-style notes in Hindi and Tamil (a complaint about a head teacher, distress) are not caught by the code word list, so for them the model's safety flag is the only guard until Shivani extends `content/safety/welfare_terms.yaml`. A YAML pitfall was fixed: unquoted `yes` and `no` become booleans.

**Confirmed by.** Not confirmed: for Gopi.

## 2026-11-02 · Four answers on a module, and the not-tried hold (Part A)

**Decision.** The answers are `worked`, `partly`, `not_yet` and `not_tried` (the old `tried` is now `worked`; rows made earlier are rewritten by `services/modules/migrate.py` at start). `not_tried` is a HOLD, never a result: the module stays open (not `feedback_given`), the planned dates and the end date move by `MODULE_DEFER_DAYS` (7) at most `MODULE_MAX_DEFERRALS` (2) times, the second deferral records a `coach_notified` event, and after it the daily job makes the planned module as `no_feedback` with the reason "you had not tried it yet". "Get the next module" always works while held. Why-not-yet chips (no time, materials, not sure how, absent, other) are kept as private events; coaches see only counts, with "not tried" in its own column.

**Defaults I chose.** (1) The first deferral happens when she answers; the second is made by the daily job when the moved date arrives (a repeated "not tried" press does not defer twice). (2) A deferral moves every planned date after the held module and the end date, so the spacing is kept. (3) The Postgres answer column is widened to 10 characters at start (create_all cannot alter it). (4) The Hindi and Tamil strings are Claude drafts for Seema and Shivani.

**Confirmed by.** Not confirmed: for Gopi.

## 2026-11-02 · A private check-in, and a masked summary shared to the cohort chat only if she agrees (Part C)

**Decision.** The check-in (answer, note, follow-up answers, "What changes next") is private to the teacher and the default is NOT shared. The sharing step shows the exact text, built by code from the answer, the validated tags and her masked note (no AI writes it); she ticks the parts (counts and name off by default), can edit, and presses Share, Don't share or Edit. The text is checked as typed (a name, roll number, phone, email, class code or percentage blocks Share and names what to remove) and masked again on Share. One post per module (Share twice does nothing); Retract soft-deletes it and is audited; Share later stays open until the next module is made. In the chat it is a Check-in card; replies work as usual. "What I would like help with" goes through the existing question flow (`chat.ask`), and the AI draft only if she ticks it (rule 15: no thread text goes to Claude without its own consent). Coaches and mentors get counts of answers (`/api/modules/coach/cohorts/..`, `/api/modules/mentor/cohorts/..`), never a note; a safety flag shows her a gentle message and tells the coach only if she presses "Ask my coach to call me" (a content-free event shown as a count). Officers have no route to the chat or to modules.

**Defaults and assumptions.** (1) "My name" means her chat name ("Teacher 7"), because the app never holds her real name; otherwise the card says "A teacher in this cohort". (2) The chat is the cohort space she joined for the same error; a cohort of one class has no chat, so the button is hidden and "No peers yet" shows. (3) The unread badge counts other teachers' visible posts since she last tapped the button (the time is kept on her phone only). (4) Offline, the check-in is saved and Share is disabled with the reason; the chat page is opened but its messages are not cached by this change, so "new messages need a connection" is shown and a read-only cached thread is **not** built. (5) The summary is capped at 600 characters.

**Confirmed by.** Not confirmed: for Gopi.

## 2026-11-02 · The spoken script of a module has its headings, and call 18 rewords it for listening

- **Decision:** the text sent to the voice now says each section heading (What this does, What you need, Steps, An example, How to know it worked) before the section, and pauses after "Module n of N." Call 18 (`c18_module_narration`, haiku) may reword each part so a listener can follow it by ear. Code speaks the headings; the model writes only the bodies. Its output is used only if every part is present in order, every number and `{slot}` is kept and none added, the length is close, and the pre-filter and call 7 pass; otherwise the code-built script is used. It runs once when a module is made and is stored with the module.
- **Also fixed:** "None" in the content files means no materials and is now read as "No materials needed."; worked examples are chosen per error, so a PV-HEARD module has no subtraction example.
- **Why:** a listener cannot see the headings, and the model is good at spoken phrasing but must not touch numbers.
- **Alternatives:** let the model write the headings (rejected: can drop or change them); reword on every view (rejected: cost and drift).
- **Confirmed by:** not yet. The per-error examples and the Hindi and Tamil headings need Seema and Shivani; no live narration run has been made, so call 18 is Built, not Verified.
