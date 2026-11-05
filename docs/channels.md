# Channels: one back end, thin adapters

> **Status (30 Oct 2026): the web app is the only channel in the demo and the pilot. Telegram is on the roadmap.** The Telegram adapter below is built and covered by golden-transcript tests, but no bot is deployed and nothing in the app points to it. WhatsApp stays a stub.

Every teacher flow is defined once in `services/api/flows/` as steps (message, choice, link now;
photo batch, number grid, voice, media, text as their phases land). A channel adapter only renders
a step and returns the answer. It never computes a number, decides what comes next, or calls a model.

```mermaid
flowchart LR
  T[Telegram bot] --> TA[telegram adapter]
  W[Web app PWA] --> PA[pwa adapter: /api/flow]
  X[WhatsApp later] --> WA[whatsapp stub]
  TA --> F[Flow engine: state, consent, linking, delete]
  PA --> F
  WA --> F
  F --> S[(teachers, channel_links, link_codes, flow_state)]
  F --> E[engine/: counts and tracks, via facts.py]
```

## What is where

| Piece | File | Job |
| --- | --- | --- |
| Steps | `services/api/flows/steps.py` | What a flow asks or says; copy by string key |
| Flows | `services/api/flows/onboarding.py`, `t1.py` | Language, consent, link code, home menu |
| Engine | `services/api/flows/engine.py` | Current step, answers, replay keys, linking, deletion |
| Words | `strings/{en,hi,ta}.json`, `services/api/strings.py` | The same copy for every channel |
| Rendering | `services/api/channels/base.py` | Step to text and buttons |
| Web | `services/api/channels/pwa/` | `GET /api/flow/current`, `POST /api/flow/answer`, `/code`, `/link` |
| Telegram | `services/api/channels/telegram/` | Update parsing, `/start`, `/start judge`, `/start CODE`, `/stop`, webhook |
| WhatsApp | `services/api/channels/whatsapp/` | Stub: numbered text options |

## Identity

A teacher has one id, her nickname (decided 2026-11-03). On the web the nickname is the sign-in; a chat id (Telegram, roadmap) is linked to
it. To use the second channel she asks for an 8-character code (15 minutes, one use) and sends it to
the bot (`/start CODE`) or types it in the web app. Her other record on that channel is erased on
linking. `/stop` in Telegram, and "Delete my data" in either channel, ask once and then erase the
teacher, links, flow state, her consent history and her class counts everywhere.

## Adding a channel

1. Write `channels/<name>/` with a function that turns its incoming event into `(step_id, option_id)`
   and a sender that shows `Message` objects from `base.render_turn`.
2. Import nothing from `engine/` or `ai/` (`tests/channels/test_import_rule.py` fails otherwise).
3. Add the channel to `tests/channels/test_golden.py`: the same scripted answers must show the same
   words and choices and leave the same stored state as the web adapter.

## T4 and T6: lessons, two taps, my result (P10)

```mermaid
flowchart TD
  M[T1 menu] -->|"My track and lessons<br/>(only if a track is published)"| I[intro: error in words, number of lessons]
  I --> L[lesson: one media step<br/>voice note + words + badge line]
  L -->|not due yet| W[later: "Lesson N comes in D days"]
  L --> T[tried in class?]
  T -->|yes| H[how did it go?]
  H --> K[thanks: your own report]
  T -->|not yet| X
  K --> X[next: next lesson / model lesson / rehearse / back]
  X -->|next| L
  X -->|rehearse| P[link: Practice Class]
  M -->|"My result<br/>(after two checks)"| R[result in counts] --> F["a failed track counts against the track, not you"]
```

| Step | Telegram | Web app |
| --- | --- | --- |
| Lesson (`media`) | A voice note (OGG/Opus) fetched from a signed lesson link, the words as its caption, or as a following message when long; the badge line is part of the words | A lesson card with the words and an audio player on the same link |
| Taps (`choice`) | Inline buttons, callback data `step:option` | Buttons |
| Model lesson | A message with the script and the badge line | A card |
| Rehearse (`link`) | A button that opens the Practice Class with a signed link | A link |
| My result | Messages, counts only | Cards, counts only |

Lessons come only from a published manifest (a track version both keys switched on). Taps are self-report, stored per lesson per pseudonymous teacher id, and shown to officers as counts. Not built (cut in P10): the call 9 reflection pointer, voice reflections and the biweekly "Still using it?" prompts. Offline replay of a downloaded lesson in the web app is not built either; a lesson is fetched when it is opened.

## Known gaps

Photo, voice and number-grid steps have no adapter rendering yet (P08 and P10). The webhook sender
does not retry; a failed send is dropped. Telegram's Bot API cannot confirm a message was read.
