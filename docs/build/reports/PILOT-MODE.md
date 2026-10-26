# Pilot mode: report (23 Oct 2026)

**Status: built and tested; not yet run against a real bucket, a real Sarvam key or a real phone.**
Brief: with `PILOT_MODE=1` the app shows sign-in and two working pages, *Upload sheets* and *Intervention audio*, and nothing else.

## What exists now

| Part | Where | What it does |
| --- | --- | --- |
| Switch | `ai/config.py` (`pilot_mode`, `pilot_audio_max`), `services/api/main.py` (`create_app`) | Off by default. On: only the pilot router and `/api/health` are mounted, API docs are off, every other path is a 404. `/api/health` adds `"pilot": true` (and only then). |
| Web app | `apps/pwa/src/main.tsx`, `src/pilot/` | At start the app asks `/api/health` (or the build flag `VITE_PILOT_MODE=1`; the answer is remembered for offline starts) and loads either the full app or `PilotApp`, which imports no other screen. The router sends every address except `#/upload` and `#/audio` to `#/upload`. |
| Sign-in | `services/pilot/auth.py`, `services/api/roles/` | Accounts in `PILOT_ACCOUNTS` (`name:roles:key`), signed tokens (12 h), five wrong tries pause a name for ten minutes, the `X-Role` header and judge mode are ignored. Roles: `coordinator` (new), `coach`, `officer`. |
| Page 1 | `UploadSheets.tsx`, `uploads.ts`, `services/pilot/sheets.py` | Codes, consent gate, camera or files (JPG, PNG, HEIC, PDF), on-device shrink, SHA-256 duplicate skip, queue with statuses (queued, uploading, stored, failed, retry), offline queue, signed upload to the private bucket, then call 8. Counts: uploaded, read, needs a second look. Retention setting and delete-all-for-school. |
| Page 2 | `InterventionAudio.tsx`, `services/pilot/lessons.py`, `audio.py` | Stepper (default 3, max `PILOT_AUDIO_MAX`), language, voice, Generate, empty state, cards with play, script, download, share, regenerate and versions, coach approve/return, share log. |
| Storage | `services/pilot/storage.py` | `S3BlobStore` (boto3; SSE requested; signed PUT 5 min, GET 2 min) and `LocalBlobStore` (tests and `PILOT_LOCAL_STORE=1` only). The sheets bucket must differ from `S3_BUCKET`; with no sheets bucket the pilot refuses to start. |
| Tables | `services/api/db.py` | `pilot_sheet`, `pilot_class_count`, `pilot_config`, `pilot_audio`, `pilot_share`, `pilot_audit`. Review rows reuse `review_items` and `review_decisions`. |
| Permissions | `services/api/roles/permissions.yaml` | `pilot.upload_sheets`, `pilot.sheets_admin`, `pilot.generate_audio`, `pilot.audio_view`, `pilot.approve_audio`, `pilot.share_audio`; role `coordinator`; two boundaries, each tied to a real test. |

## How the audio chain maps to the brief

class counts from the read sheets (`pilot_class_count`, summed) → diagnosis (`engine.diagnosis.profile_from_counts`, the same track rule as everywhere) → approach from the approved move lists (`content/movelists/`, ordered per error in `content/pilot/lessons.v1.yaml`) → script (template drafter) → validators (check-items, no percent sign, numbers allowed-list, arithmetic, readability, language, pre-filter) → call 7 → `review_items` → the coach approves → Sarvam Bulbul → m4a → published-audio bucket. A failed check never reaches the queue; an unavailable checker sends the card to a person with a note; nothing is voiced, published, downloadable or shareable before approval.

## Where the brief assumed something that did not exist (read this)

| The brief said | What was there | What I did |
| --- | --- | --- |
| "the existing auth stub", "roles" | Only an `X-Role` header honoured in judge mode | Added real sign-in for pilot mode (accounts from the environment, signed tokens). It is deliberately small. |
| "the strategy library" | Move lists and rubrics for the Practice Class (`content/movelists/`) | Used them as the approved approaches. |
| "script drafting (calls 4 and 5)" | **Neither call is built** (P09 and P11 are not started) | A **template drafter**: words from `content/pilot/lessons.v1.yaml` and the move lists, counts from the engine, wrong answers from `engine.bugs`. `ScriptDrafter` is the seam for call 5. Nothing was added to `AI_USAGE.md` because no AI capability was added. |
| "the review queue" | Tables only (`review_items`, `review_decisions`), no routes | The pilot routes write to them. Reject reasons use `ai/guard/rejections.py` and are appended as call 7 examples. |
| "scripts/pilot_import" | Does not exist | Not used. Sheets that need a second look wait for hand-keying; that tool is still to be built. |
| "the existing Sarvam voices" | Child voices only; one teacher speaker (`ritu`) | `content/voices/pilot.v1.yaml` lists seven narrator speakers already named elsewhere in the repo. None was verified (the key is rejected). |
| "the coordinator generates and approves" (done-when) | Approval belongs to the coach (the gate must stay) | A coordinator who also holds the coach role (`PILOT_ACCOUNTS=name:coordinator+coach:KEY`) does both from one sign-in. A coordinator alone cannot approve. |
| Approval permission "kept" | `coach.approve_items` is planned for P11 and unused | Added `pilot.approve_audio` for the coach so the landing-page dialog is not changed; same meaning. |

## Decisions that need Shivani or Seema

| # | Decision | Default now | Owner |
| --- | --- | --- | --- |
| 1 | **Name-on-sheet policy.** The page tells the coordinator to ask schools to write roll numbers, not names, and to cover any name before the photo. Nothing checks the photo for a name. Is that enough, or should a masking step run before upload? | Notice only | Seema (with HMs), Shivani |
| 2 | **Consent wording and reference.** What exactly does the school sign, and what is the reference the coordinator types (letter date and number?). The app stores whatever fits `[A-Za-z0-9 ./_-]`, 3 to 60 characters. | Free reference, checkbox "School consent is on file for these sheets." | Seema, with the programme's legal reviewer |
| 3 | **Retention period.** | 90 days after upload, editable 7 to 365 in the app (`PILOT_RETENTION_DAYS`). Class counts are kept after the photo is deleted. | Seema |
| 4 | Whether sheets with roll numbers stored in a bucket count as children's personal data (`docs/privacy.md` now says *to confirm*). | Treated as sensitive | Legal reviewer |
| 5 | Hindi and Tamil wording of every `pilot.*` string, the Hindi and Tamil lesson glue and the WhatsApp message (the brief said to mark these as needing Shivani). | First drafts by the build | Shivani |
| 6 | The lesson content itself: order of moves per error, one worked example per error, the single question lesson 1 tells the teacher to ask. Scripts are about one minute each, shorter than the 2 to 3 minutes the size limit allows for. | Template from the move lists | Seema |
| 7 | Which narrator voices to keep. | Seven stock speakers, default `ritu` | Shivani |

## Storage: Google Cloud Storage or Firebase (added 24 Oct)

`GcsBlobStore` (`services/pilot/storage.py`) is a third backend beside S3 and the local dev store. A Firebase Storage bucket is a GCS bucket, so the same code covers both. Set `GCS_SHEETS_BUCKET` (private, for sheet photos) and `GCS_AUDIO_BUCKET` (approved audio), two different buckets. If any `GCS_*` bucket is set it is used; otherwise the S3 keys; otherwise the pilot refuses to start. URLs are V4 signed, 5 minutes to upload and 2 to download (24 hours for a shared audio link). GCS encrypts at rest by default, so there is no encryption header.

**Authentication needs no key file** (the project's organisation policy `iam.disableServiceAccountKeyCreation` blocks keys). In order: (1) a key in `GCS_CREDENTIALS_JSON` or `GOOGLE_APPLICATION_CREDENTIALS`, only if you have one; (2) otherwise Application Default Credentials: on Cloud Run or Compute Engine the attached service account (metadata server), on a laptop `gcloud auth application-default login`. Without a key a URL cannot be signed locally, so Google's IAM service signs it on behalf of a service account: the attached one on GCP, or `GCS_SIGNER_SERVICE_ACCOUNT` on a laptop.

One-time setup in Google Cloud (not testable from here):
1. Create the two buckets, **uniform bucket-level access on** and **public access prevention enforced**.
2. Service account `gcs-storage-admin@fln-cohort-coach.iam.gserviceaccount.com` (already created) with *Storage Object Admin* on both buckets (done). Also grant **Service Account Token Creator** on that account: to yourself for a laptop (`gcloud iam service-accounts add-iam-policy-binding gcs-storage-admin@fln-cohort-coach.iam.gserviceaccount.com --member=user:<you> --role=roles/iam.serviceAccountTokenCreator`), and to the account itself when it is the one attached to Cloud Run or a VM. Enable the *IAM Service Account Credentials API*.
3. Laptop: `gcloud auth application-default login`, then in `.env` leave `GCS_CREDENTIALS_JSON` and `GOOGLE_APPLICATION_CREDENTIALS` blank and set `GCS_SIGNER_SERVICE_ACCOUNT=gcs-storage-admin@fln-cohort-coach.iam.gserviceaccount.com`. On GCP: attach the service account to the service and leave all three blank.
4. CORS on the sheets bucket so the phone can upload straight to it: `gsutil cors set cors.json gs://<sheets-bucket>` with `[{"origin":["<PWA origin>"],"method":["PUT"],"responseHeader":["Content-Type"],"maxAgeSeconds":3600}]`. The audio bucket needs no CORS.
5. Lifecycle rule on the sheets bucket: delete objects older than 97 days (90-day default retention plus a week) as a backstop. Applied to `fcc-build-app-sheets-bucket` on 24 Oct; if `PILOT_RETENTION_DAYS` is raised above 90, raise the rule too. With Firebase, leave Storage security rules at deny-all: the app only uses signed URLs.

Tests: `tests/pilot/test_gcs.py` (offline, with a throwaway key; no network).

## Could not verify

- **A real GCS or S3 bucket.** The signed-URL shape and the encryption header are tested against boto3's offline signer (`tests/pilot/test_uploads.py`), not a live bucket. The bucket needs CORS allowing `PUT` from the PWA origin with the `Content-Type` and `x-amz-server-side-encryption` headers, public access blocked and default encryption on; none of that can be tested from here.
- **Live Sarvam.** Speech is stubbed in tests. `tests/pilot/test_full_pass.py::test_live_speech_voices_one_short_line` runs only with `PILOT_LIVE_SPEECH=1`; the key was rejected on 22 Oct, so it has not run.
- **A real phone.** Web Share with a file, the camera capture, the HEIC path and the m4a being accepted by WhatsApp are untested on a device. The browser tests use Chromium with a phone viewport and a stubbed `navigator.share`. The share code tries `audio/mp4`, `audio/x-m4a`, `audio/m4a` and keeps the first that `canShare` accepts; set `PILOT_AUDIO_FORMAT=mp3` if a phone refuses m4a.
- **Call 8 on pilot photos.** Reading is tested with a stand-in model. The real reader has not seen the pilot pre-test sheets; its accuracy bar (eval 9) is unchanged and not re-run.
- **HEIC and PDF** are stored but not read (no decoder is installed), so they always show as "need a second look". Chrome on Android shrinks and converts most camera photos to JPEG before upload; an iPhone's HEIC may not decode in the browser.
- **Scripts are about a minute long.** The brief's "2 to 3 minute note" is the size budget (a 3-minute note renders under 1 MB: tested), not a length the template produces.
- **Postgres.** Tests use SQLite; the new tables use plain types, no migration was written (the repo builds tables with `create_all` until Alembic arrives; see DECISIONS).
- Background reading of a sheet runs in the API process after the upload response; if the process restarts in that moment the sheet stays "stored" (counted as uploaded, not read) until it is reuploaded. A retry button for stuck sheets is not built.

## Evidence

Run these; numbers are whatever the commands print.

```text
.venv/Scripts/python.exe -m pytest tests/pilot tests/roles -q
cd apps/pwa && npx vitest run src/pilot && npx playwright test e2e/pilot.spec.ts
.venv/Scripts/python.exe -m ruff check . && .venv/Scripts/python.exe -m mypy
```

| Brief's test | Test |
| --- | --- |
| Every non-pilot route is a 404 | `tests/pilot/test_pilot_mode.py::test_every_non_pilot_route_returns_404_in_pilot_mode` (every path of the normal API, from its OpenAPI document), `test_the_api_docs_are_off_in_pilot_mode`, `test_the_only_routes_are_pilot_routes_and_health` |
| Web app redirects | `src/pilot/pilot.test.ts` "the pilot router"; `e2e/pilot.spec.ts` "every other address goes to Upload sheets" |
| Consent gate blocks upload | `test_the_consent_gate_blocks_an_upload`; `pilot.test.ts` "the consent gate"; `e2e` "sheets cannot be added until consent is confirmed" |
| Duplicate checksum skipped | `test_a_duplicate_checksum_is_skipped`; `pilot.test.ts` "skips a duplicate checksum" |
| Failed file retries | `test_a_failed_file_can_be_retried`; `pilot.test.ts` "marks a sheet failed … a retry puts it back" |
| No public URL; signed URLs expire | `test_no_public_url_exists_for_any_sheet`, `test_signed_urls_expire`, `test_a_signed_s3_url_is_signed_short_lived_and_asks_for_encryption` |
| No child name column or field | `test_no_child_name_column_or_name_field_exists` |
| Audio count bounds, audit, lowering | `test_counts_outside_one_to_the_maximum_are_rejected`, `test_the_maximum_comes_from_pilot_audio_max`, `test_changing_the_count_is_audit_logged`, `test_lowering_the_count_deactivates_cards_and_never_deletes_them` |
| Nothing published before approval | `test_nothing_reaches_the_published_bucket_before_approval` |
| Full pass on a synthetic class | `tests/pilot/test_full_pass.py` (20 synthetic sheets: upload, read, three scripts, approve, voice, download, share); live speech behind `PILOT_LIVE_SPEECH=1` |
| Download and Share refuse unapproved audio | `test_download_and_share_are_unavailable_for_unapproved_audio`; `e2e` "approval gates Download and Share" |
| File names carry no names | `test_file_names_hold_no_school_or_teacher_name`, `test_an_approved_file_downloads_with_a_name_that_holds_only_slot_and_language` |
| Size target | `test_a_three_minute_note_is_mono_and_under_the_size_target` (white noise, the worst case, m4a and mp3), `test_a_long_script_is_encoded_smaller_to_stay_under_the_target` |
| Fallback when sharing is unsupported | `pilot.test.ts` "sharing on WhatsApp"; `e2e` "when the phone cannot share files …" |
| Marking a share writes `pilot_share` and is audited | `test_marking_a_share_writes_rows_and_is_audit_logged` |

## Running it

```text
PILOT_MODE=1  PILOT_ACCOUNTS="seema:coordinator+coach:<key>"  PILOT_TOKEN_SECRET=<random>
S3_SHEETS_BUCKET=<private bucket>  S3_BUCKET=<published audio bucket>  S3_ENDPOINT=...  (see .env.example)
SPEECH_MODE=live  SARVAM_API_KEY=...  AI_MODE=live  ANTHROPIC_API_KEY=...
uvicorn services.api.main:app          # the Telegram bot (scripts/run_bot.py) is a separate process: do not start it
npm run build   (VITE_API_BASE=<api url> VITE_PILOT_MODE=1 for a separate static host)
```

Local try-out with no bucket: `PILOT_LOCAL_STORE=1` keeps sheets and audio under `.pilot-local/` (gitignored). Never use it in production.

## Review (privacy-guardian, 23 Oct)

No child name, roll number or per-child answer reaches the database, logs or audit rows; no secret is hard-coded or logged. Two blocking items:

- **B1, photos kept server-side (rule 2).** Deliberate, and written into CLAUDE.md rule 2 and DECISIONS.md as the brief asked. It needs Gopi's own confirmation and the legal items in the table above before any real school's sheets are uploaded.
- **B2, officer and coach views.** Fixed: the share log (`shared_with`) is returned only to the coordinator, and an officer sees no scripts and no sheet or class figures while fewer than 5 classes are pooled (`test_an_officer_sees_no_share_log_and_no_small_class_figures`). **Still open:** the coach must read the script to approve it, and with one or two pilot classes that script states the pooled count. Accepted for the pilot because the coach is the reviewer role; a human should confirm this in DECISIONS.md.

Fixed from the non-blocking list: an object that arrives short or oversized is deleted; the local store refuses uploads over 8 MB.
Not fixed (open): a failed bucket delete leaves an orphan (add a lifecycle rule on the sheets bucket); the sign-in throttle is per name and per process, with no minimum key length (use long random keys); sign-out leaves queued photos and cached audio on the phone; `PILOT_LOCAL_STORE=1` is not blocked in production (never set it there); the token secret falls back to `LINK_SECRET`.

## Words first, voice on the first tap (added 26 Oct)

The coach's approval now approves the text only. An approved lesson is shared as a lesson link (`/#/lesson/<token>`, signed, 14 days, one lesson, no sign-in). The first tap on **Download audio** on that page voices the script (one Sarvam call), keeps the file, and later taps reuse it; `PILOT_VOICE_DAILY_MAX` (default 20) caps new voicings caused by teachers' taps. The coordinator can still press **Make audio now**. Tests: `tests/pilot/test_lesson_link.py` (links, first-tap-once, two taps at once, the cap, the voice down, expiry, tampering, every other route still needing a token) and the lesson-link cases in `apps/pwa/e2e/pilot.spec.ts`. Decision: `DECISIONS.md` 2026-10-26. Not built: on-device voice (parked), and a "this is wrong" flag on the lesson page.
