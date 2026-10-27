# Claude Code prompt: AI-drafted replies in the gated cohort chat

Paste everything below the line into Claude Code at the repo root.

---

**Task.** Add AI-assisted replies to the gated cohort chat. A teacher asks a question in the app. The AI drafts a reply from approved material only. The mentor or coach sends it, edits it, or writes their own. If nobody answers before a timeout that the coach sets, the draft goes to the teacher labelled as AI-generated, and the mentor can correct it afterwards.

**Design rules this must keep.**

- The PWA is the primary channel. Chat content stays inside the app. WhatsApp and Telegram, if enabled, carry only a content-free notice such as "You have a new reply in Cohort Coach".
- Child names are masked before any model call, with the existing masking layers (pre-call, post-generation).
- Auto-sending an AI answer is a deliberate, narrow exception to the rule that nothing AI-drafted reaches a teacher before a human approves it. It applies only when every gate in Step 3 passes.
- Children appear as counts and patterns only. No percentages for teachers.

**Step 0. Read first.** Read CLAUDE.md, DECISIONS.md, PROGRESS.md, docs/design/stitch/DESIGN.md (if present), and the existing code for: the cohort chat, mentor and coach pages, roles and auth, the masking layers, the output checker (call 7), the review queue, the strategy library, method cards, the audit trail, the call registry and prompt caching. Reuse them. Do not build a parallel pipeline.

**Step 1. Data model.**

- chat\_message: id, thread\_id, author\_role (teacher, mentor, coach, ai), body, status (pending, answered\_by\_human, ai\_draft\_ready, ai\_sent, corrected), ai\_due\_at, created\_at.
- ai\_reply\_draft: message\_id, draft\_text, sources (content ids and the supporting sentence ids), question\_class, checker\_result, model, tokens, status (drafted, sent\_as\_is, edited\_and\_sent, discarded, auto\_sent), edited\_text, edit\_reason\_tags, decided\_by, decided\_at.
- chat\_config: scope (global or per cohort), ai\_timeout\_hours, ai\_auto\_send\_enabled, set\_by, set\_at. Audit-logged.
- **Coach-configurable timeout.** Only the coach role can change it. Default 24 hours, allowed range 1 to 168, validated on the server. A per-cohort override beats the global default. The due time is computed and stored on each question when it is created (ai\_due\_at), so changing the setting never moves questions that are already waiting. The settings page says "Applies to new questions".

**Step 2. Draft pipeline, on every new teacher question.**

1. Mask names and other personal data.
2. Classify the question: content\_question, child\_specific, safety\_or\_welfare, discipline\_or\_personal, off\_topic, unclear.
3. Retrieve from approved material only: published track lessons, approved method cards, enabled strategy-library entries, filtered to the cohort's error and the teacher's language. Use the Citations API if the AI gaps work verified it; otherwise keep the existing verbatim-sentence validator.
4. Draft with Sonnet in the teacher's language, at most 120 words, practical and classroom-ready, citing at least one source. If no source supports an answer, return no\_answer with a reason. Never invent content.
5. Check: rule-based pre-filter, then the output checker (call 7), then validators (arithmetic by code, citations present and verbatim, no names, reading level).
6. Store the draft with its sources. Safety and welfare questions get no draft and go straight to the coach with a flag. Child-specific and discipline questions get a draft for the mentor only and never auto-send.

**Step 3. Auto-send gates.** At ai\_due\_at, send the AI draft only if all of these hold: no human has replied; ai\_auto\_send\_enabled is on; the question class is content\_question; the draft cites approved sources; the checker passed; the per-teacher daily AI reply limit is not exceeded. Otherwise keep waiting and alert the coach. The scheduler must be idempotent, so it never double-sends.

**Step 4. Labels the teacher sees.** Icon plus text, never colour alone.

- Human-written answer: no AI label.
- AI draft sent or edited by a human: "Drafted with AI, checked by your mentor."
- Auto-sent after the timeout: "AI-generated from approved material. Your mentor will check it."
- If a human corrects an auto-sent answer: post "Correction from your mentor" under it, mark the AI message Corrected, and send an in-app notice.
- While waiting: "Waiting for your mentor. You will get an answer by {time}."

**Step 5. Mentor and coach experience.**

- An inbox of pending questions sorted by due time, with a countdown. Each shows the masked question, the suggested reply and its sources.
- Actions: Send as is, Edit and send (with voice dictation), Write my own, Discard draft, Escalate to coach, and a quick mark of Good or Not good.
- Auto-sent answers appear in a Needs review list until a human has looked at them.
- Coach settings page: timeout stepper, auto-send on or off, per-cohort override.

**Step 6. Learn from corrections.** Store each edit with reason tags (wrong content, too long, not practical, wrong language, unsafe). After 20 to 30 corrections, add them to the call 7 prompt as examples of content that was rejected and why. Report: sent-as-is rate, edit rate, auto-sent count, correction rate, median time to first response, to docs/evidence/chat\_metrics.json (synthetic data in judge mode, labelled simulated).

**Step 7. UI.** Follow DESIGN.md. Teacher chat is phone first. The mentor inbox and the coach settings are desktop first. English, Hindi and Tamil labels, 44px targets, inline SVG icons, offline: a question typed offline is queued and shows as Queued.

**Step 8. Tests first.**

- The timeout setting rejects values outside 1 to 168 and is coach-only; ai\_due\_at is fixed at creation; a settings change does not move existing questions.
- Auto-send never fires for child\_specific, safety\_or\_welfare, no\_answer, unchecked or source-less drafts.
- Exact label text for each of the five cases. The correction flow works. The scheduler never double-sends.
- Names are masked before the model call and checked again after generation.
- Red team, 50 prompts: injection in questions, child-specific and safety cases, off-topic, Tamil, Hindi and English mixing. Unsafe auto-sent answers must be zero.
- Every draft and decision writes an audit entry.

**Step 9. Kit updates.**

- CLAUDE.md: add the narrow auto-reply exception and its gates.
- DECISIONS.md: add an entry dated 2026-10-24 stating that this is a deliberate exception to human approval before anything AI-drafted reaches a teacher, and why.
- AI\_USAGE.md call registry: add the new call. PROGRESS.md: update.
- docs/design/stitch/INVENTORY.md: add the teacher chat, mentor inbox and coach settings screens.
- Report: docs/build/reports/CHAT-AI.md, with anything that needs Seema or Shivani (wording of labels in Hindi and Tamil, the default timeout).

**Done when** the tests pass, a teacher question gets an AI draft in the mentor's inbox, a human can send, edit or replace it, an unanswered question is auto-sent with the label only when every gate passes, and a coach can change the timeout.
