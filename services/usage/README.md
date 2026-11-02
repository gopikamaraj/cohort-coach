# Per-action cost and time

The footer of the app shows what the **last action** cost and how long it took, summed over every call that
action caused. It is not a running total: starting another action starts it again from nothing.

## How an action id travels

1. **Client** (`apps/pwa/src/lib/action.ts`). `runAction(name, fn)` makes a uuid, starts a timer, and keeps
   the action as "running" while `fn` runs. The one `fetch` wrapper in `lib/meter.ts` adds
   `X-Action-Id` and `X-Action-Name` to every request to our API during that time. When `fn` ends, the timer
   stops (that is the wall time) and the app asks `GET /api/actions/{id}/usage` every 1.2 s until
   `complete` is true, once more after that, and gives up after 30 s.
2. **Server middleware** (`middleware.py`). Reads the header, keeps the id in a context variable
   (`context.py`), counts the request as in flight in the shared store, and when it ends writes one
   `cloud_run` entry (the request's wall time, `cold` for the first request an instance serves) and counts it
   out. It is a pure ASGI middleware, so a background task started by the request runs inside the call and the
   action stays open until it is done.
3. **Worker threads.** A new thread does not inherit the context. Start work in a pool with
   `services.usage.context.submit(pool, fn, ...)`, which carries the id across. (Done in the lesson audio
   chunks and the Practice Class speech pool.) A background task or thread that does not use it records
   nothing for the action.
4. **Hooks, one per provider.**
   - Claude: `SqlAuditSink.write` (`ai/audit.py`) calls `meter.record_llm` for each audit row, so every Claude
     call is counted once, with its tokens and retries.
   - Speech: `default_chain` (`services/speech/service.py`) wraps each provider in `MeteredProvider`, so every
     text-to-speech and speech-to-text call is counted once, failures included.
5. **Ledger** (`models.py`, `store.py`). One row per event in `usage_entries` and one per action in
   `usage_actions`, in the app's own database, which every Cloud Run instance shares. Inserts are separate
   rows and the in-flight counter is one atomic `UPDATE`, so parallel calls cannot overwrite each other. Rows
   older than 24 hours are purged as new ones are written.

## What an entry holds

Kind (`llm`, `tts`, `stt`, `cloud_run`), provider, model or voice, **units** (numbers only: tokens,
characters, seconds, request milliseconds), cost in USD (or none), start, duration, status
(`ok`, `failed`, `retried`), a request id and a few flags (`cold`, `cached`, `estimated`). `meter.record`
refuses any other key and any non-number, and there is no column that could hold a prompt, a reply, a
transcript, audio or a name.

## Prices (`content/usage_pricing.yaml`)

- **Claude:** `ai/pricing.yaml` (per model, with its source and date).
- **Speech:** `content/speech_prices.yaml` (INR, per provider and function), turned into USD with
  `inr_per_usd` from `usage_pricing.yaml`.
- **Cloud Run:** `cloud_run` in `usage_pricing.yaml`: vCPU, GiB, concurrency and the two per-second prices.
  Billing there is instance-based (CPU always allocated), so the cost shown is **an estimate and an upper
  bound**: the request's seconds times the service's vCPU and GiB, as if it had the instance to itself.
- A price that is missing or `null` shows as **n/a** (the units are still counted) and logs one warning. It is
  never shown as 0. As shipped, `inr_per_usd` and both Cloud Run prices are `null`: fill them in from the
  providers' own pages (`TODO-HUMAN(Gopi)`), then restart the API.
- `display_currency` is `USD` or `INR`; everything is stored in USD.

## Add a new billable provider

1. Put its price in a config file (or `speech_prices.yaml` for speech), with `as_of` and a source.
2. Wrap its client in **one** place: a wrapper class like `MeteredProvider` that times the call, reads the
   usage from the response, calls `pricing.<fn>` for the cost and `meter.record(...)`. Record a `failed`
   entry when it raises. For a stream, record when the stream ends.
3. If it is a new kind, add its allowed unit names to `ALLOWED_UNITS` in `meter.py`, to `UNIT_KEYS` in
   `api.py`, and a row in `UsageFooter.tsx`.
4. Never pass text, audio or ids of people to `record`.

## Update prices

Edit the YAML, restart the API (the config is read once). Nothing is typed in code.

## Add an action to the footer

Wrap what the click does in `runAction("name", async () => { ... })`, make sure every request it makes goes
through `fetch` (so the header is added), and add `usage.a.name` to `strings/en.json`, `hi.json` and
`ta.json`. The footer's end of the action is when that function returns (the file saved, the print dialog
about to open).

## The bar

It sits above the bottom tabs inside the app frame, so it cannot cover them, and respects the safe-area
inset when there are no tabs. Tapping it opens a table (scrolls on a small screen); "Hide this bar" turns it
off, and Profile turns it back on. It is shown to every role, teachers included; `VITE_USAGE_FOOTER=0` removes
it.

## Limits

- Time a background step spends outside any provider call is not metered; its calls are.
- Instance-based Cloud Run billing is shared by concurrent requests, so the per-action Cloud Run figure is
  an upper bound, not an invoice line.
- Failed calls are recorded as `failed`; a retry is a second entry. Only Claude entries are marked `retried`
  (from the audit row's retry count).
- The ledger is in the app's database, so it needs the same database on every instance (it is).
