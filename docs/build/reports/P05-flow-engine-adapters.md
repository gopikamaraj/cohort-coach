# P05 (v3) · Flow engine and channel adapters

Date: 20 Oct 2026 · Status: 🟡 (backend built and tested; real-phone check and web photo/voice steps open)
Commits: `331f2ec` (engine), `84cdad6` (adapters, web step screen), plus the review-fix commit that follows.

## What was built

- **Flow engine** (`services/api/flows/`): versioned per-teacher state, step types in `steps.py`, onboarding (language, five separate consents off by default, link code) and the T1 home menu (status in counts, "what my class gets wrong", signed practice link, check info, delete my data). Replayed answer keys change nothing. The engine imports no channel.
- **Identity**: one random teacher id; devices and chats are links to it; 8-character one-use link codes (15 minutes); linking erases the chat's earlier separate record; deletion removes teacher, links, state, consent history and class counts.
- **Adapters** (`services/api/channels/`): web JSON step API (`/api/flow/*`), Telegram (update parsing, `/start`, `/start judge`, `/start CODE`, `/stop`, closed-by-default webhook, polling runner `scripts/run_bot.py`), WhatsApp stub (numbered text).
- **Shared strings**: `strings/{en,hi,ta}.json` used by the bot and the web app.
- **Web**: a `/flow` screen rendering the server's steps, linked from Home.
- Docs: `docs/channels.md`, `docs/architecture.md` and `docs/offline.md` sections.

## Evidence

| Claim | Command | Result |
| --- | --- | --- |
| Engine, identity, deletion, strings complete in 3 languages, no percentage | `pytest tests/flows -q` | passed (see run below) |
| Same words, choices and stored state through web and Telegram; judge label in both; webhook closed without secret; WhatsApp contract | `pytest tests/channels -q` | passed |
| Adapters and web app import nothing from `engine/` or `ai/` | `tests/channels/test_import_rule.py` | passed |
| Whole suite | `python tasks.py check` | green before each commit (615 Python, 204 web tests at T02) |

Final counts after the review fixes: `pytest tests/channels tests/flows` = 29 passed.

## Review outcomes

- **Privacy-guardian**: no blocking findings. Fixed: consent history now erased with the teacher; `/stop` added; bot-token URL no longer logged or re-raised; `LINK_SECRET` in `.env.example`. Not fixed (documented): the chat id is stored on the first message before core consent is given (needed to hold the conversation); the device id is a bearer credential with no rate limit on `/api/flow/link`.
- **Integrity-auditor**: honest, no blocking findings. The replay test compares the last step only (the earlier auto messages are not state; logged in DECISIONS). The golden code mask is narrow.
- **Judge-reviewer**: pass with fixes. Done: tasks ticked, PROGRESS updated, `docs/channels.md` written, judge-label and delete tests added. Deferred below.

## Deferred (honest gaps)

- Real-phone confirmation of onboarding and T1 in the bot and the web app: **needs Gopi**.
- PWA components for photo batch, number grid and voice, and the outbox replay (P08); `/r/<token>` route; QR code; server-side judge API (V3-T07, T09, T12).
- Dexie reduction and moving diagnosis out of the PWA (V3-T08, T13); server-side privacy follow-ups other than consent erasure (V3-T15).
- Sender retries for the webhook; rate limit on linking; Pydantic warns that the `copy` field shadows a `BaseModel` attribute (rename later).
- Hindi and Tamil strings for the new flows are drafts awaiting native review.
