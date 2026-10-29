# CHAT-AI · AI-drafted replies in the cohort Q&A chat — tasks

**Goal (3 lines):** A teacher asks her mentor a question in the app. If she ticks the consent box, the AI drafts a reply from approved material only; the mentor or coach sends it as is, edits it, writes her own, or discards it. If nobody answers before a timeout the coach sets, an auto-send gate (every check must pass) sends the draft labelled as AI-generated, and the mentor can correct it afterwards.

**Spec:** `docs/build/cohort_chat_prompt.md` (the user's prompt). **Built on:** P11 cohort space (`services/api/cohorts/`), P09 review queue and active track versions (`services/content/`), the gates (`ai/guard/gates.py`), call 7, the thread posting check (`ai/validators/thread.py`).

**Starting commit:** `539e496` · **Started:** 2026-10-29

**Decisions taken for this build (recorded in DECISIONS.md 2026-10-29, to be confirmed by Gopi):**

- The Q&A is a **private thread per teacher** (her, her cohort's mentors, the coach). It is not the shared cohort thread, so rule 15 ("AI never writes thread posts") still holds for the shared thread.
- **Consent is a tick on each question, off by default.** Without it no model sees the question, no draft is made, and only a person answers.
- The question is **masked when it is posted** and only the masked text is ever stored: no raw child name is kept, and the mentor sees the masked text.
- **Auto-send is off by default** per cohort; the coach turns it on. The demo deployment turns it on.
- Source material is **approved lessons of the active track version and strategies that are approved or active**. No mentor method-card text exists yet (call 4 is not built), so none is retrieved.
- Two new calls: **12 (classify the question, Haiku)** and **13 (draft the reply, Sonnet)**. Safety and welfare words are caught by code first and never reach a model.

**Human inputs (placeholder-OK):**

| Input | Owner | Blocking? | Placeholder |
| --- | --- | --- | --- |
| Hindi and Tamil wording of the five labels and the chat screens | Seema, Shivani | No | first drafts, `TODO-HUMAN` in `docs/build/i18n-todo.md` |
| The default timeout (24 h), the daily AI-reply limit per teacher (3), auto-send default (off) | Seema | No | constants in `services/chat/config.py` |
| Safety and welfare word lists in Hindi and Tamil | Shivani, Seema | No | `content/safety/welfare_terms.yaml` marked `TODO-HUMAN` |

## Tasks

- [x] **C01 · Data model, settings and the timeout rules**
  - Test first: `tests/chat/test_config.py` (1 to 168 enforced on the server, coach-only, per-cohort override beats global, `ai_due_at` fixed at creation, a change never moves a waiting question, audit rows)
  - Done when: `chat_threads`, `chat_messages`, `ai_reply_drafts`, `chat_config` tables and `services/chat/config.py`
  - Evidence: `pytest tests/chat/test_config.py` 21 passed: range 1 to 168 and whole numbers enforced, coach only, assigned cohort only, cohort beats global, due time from the setting in force, audit rows · Commit: `CHAT-C01`
- [x] **C02 · Masking and the question class**
  - Test first: `tests/chat/test_mask.py`, `tests/chat/test_classify.py` (names, roll numbers, relatives, phones masked in en, hi, ta; masked before any model call; safety words never reach a model; a masked child means child-specific)
  - Done when: `ai/validators/mask.py`, `services/chat/classify.py`, call 12 module, prompt, schema, registry entry
  - Evidence: `pytest tests/chat/test_mask.py tests/chat/test_classify.py` 36 passed: names, roll numbers, relatives, phones, emails masked in en, hi and ta; safety words in three languages never reach a model, even without the AI tick; a masked child is child-specific; discipline words route to the mentor; low confidence or failure is unclear · Commit: `CHAT-C02`
- [x] **C03 · Approved material, call 13 and the draft pipeline**
  - Test first: `tests/chat/test_draft.py` (only approved material is retrieved, filtered to the cohort's error and language; a draft must cite at least one source with a verbatim quote; no answer when no source supports it; names, class numbers, Form items and percentages are blocked; call 7 result stored)
  - Done when: `services/chat/retrieve.py`, `ai/calls/c13_chat_reply.py`, `services/chat/draft.py`, prompt, schema
  - Evidence: `pytest tests/chat/test_draft.py` 27 passed: only approved lessons of the active version, only approved strategies, no sentence with a slot, language then English; 13 kinds of bad reply dropped (no or unknown or non-verbatim or short citation, over 120 words, a name, a phone, class counts, a percentage, a Form item, a wrong sum, a score); the checker can veto; the text of a held draft is never kept · Commit: `CHAT-C03`
- [ ] **C04 · Answering, labels and the correction flow**
  - Test first: `tests/chat/test_answer.py`, `tests/chat/test_labels.py` (send as is, edit and send with reason tags, write my own, discard, escalate, good or not good; the five label texts exactly; a correction marks the AI message corrected and posts "Correction from your mentor")
  - Done when: `services/chat/service.py`, `services/chat/labels.py`
- [ ] **C05 · The auto-send gates and the idempotent scheduler**
  - Test first: `tests/chat/test_scheduler.py` (never fires for child-specific, safety, no-answer, unchecked or source-less drafts; respects auto-send off, the daily limit and a human reply; never double-sends; the coach is alerted when it waits)
  - Done when: `services/chat/scheduler.py`, `scripts/chat_tick.py`
- [ ] **C06 · API, permissions, strings**
  - Test first: `tests/chat/test_api.py` (roles, device and person ids, no teacher id in any response, coach-only settings route, teacher sees only her own thread)
  - Done when: `services/api/chat.py` mounted, permissions `chat.answer` and `chat.configure`, strings en/hi/ta
- [ ] **C07 · Screens: teacher ask, mentor inbox, coach settings**
  - Test first: `apps/pwa/e2e/chat.spec.ts` (consent off by default, queued while offline, countdown, the five labels with an icon, 44 px targets, Hindi and Tamil headings)
  - Done when: `#/ask`, `#/inbox`, `#/chat-settings` follow `DESIGN.md`
- [ ] **C08 · Learning from corrections, metrics and the red team**
  - Test first: `tests/chat/test_corrections.py`, `tests/chat/test_redteam.py` (50 prompts, 0 unsafe auto-sent), `tests/chat/test_metrics.py`
  - Done when: `scripts/chat_metrics.py` writes `docs/evidence/chat_metrics.json` (simulated), `evals/runners/chat_redteam.py`
- [ ] **C09 · Kit, docs and report**
  - Test first: `tests/test_ai_usage_doc.py`, `tests/ai/test_registry.py`, `tests/test_stitch_prompts.py` stay green
  - Done when: CLAUDE.md exception, DECISIONS.md, AI_USAGE.md, README regenerated, Stitch inventory and prompts, `docs/build/reports/CHAT-AI.md`

## Blocked or deferred

| Task | Why | Next step |
| --- | --- | --- |
| Citations API for call 13 | call 4 (the citations work) is not built, so the existing verbatim-sentence validator is used | switch when call 4 is verified |
| Mentor method cards as a source | no method-card text exists yet | add as a source when call 4 lands |
| Telegram and WhatsApp content-free notice | notifications for the thread are cut (DECISIONS 2026-10-27) | `docs/build/PARKING.md` |
| Stitch exports for the three new screens | exports come from Stitch itself; prompts are written, screens are built from `DESIGN.md` | generate the exports, then compare |
