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
| OD-7 | Voice-lesson languages in the prototype | Hindi and English required; Tamil if time (cut-list item 6) | P09 | Gopi |
| OD-8 | Demo mentor | Seema nominates a real primary teacher by 25 Oct with written consent; until then a consenting team member's recording, labelled as such | P11 | Seema |
| OD-9 | Answer-reading eval data | Seema or Shivani photograph the unmarked pilot Form A sheets; the header band (class code, roll number) is masked locally before any upload; Shivani hand-keys the truth | P08, P13 | Seema, Shivani |
| OD-10 | Backup if Week 2 slips | Apply the cut list in order; Gopi decides anything beyond it | Any | Gopi |

## Settled decisions

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
