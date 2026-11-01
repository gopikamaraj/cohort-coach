# Bodhan AI: speech API reference notes

Read from https://console.bodhan.ai/api-docs/ on **1 Nov 2026** (HTTP 200, server-rendered page). These are notes on the two speech endpoints we use, not a copy of the page. The page wins over these notes and over the summary in `docs/build/bodhan-speech-prompts.md`. Re-read it before you change `services/speech/bodhan.py`.

## Common

- Base `https://api.bodhan.ai`. The `/v1` routes take OpenAI-style requests.
- Auth: `Authorization: Bearer <key>` on every request. The page's examples use one variable, `BODHAN_API_KEY`. We use `BODHAN_SPEAK_API_KEY` and `BODHAN_TRANSCRIBE_API_KEY`, each falling back to `BODHAN_API_KEY`.
- Rate-limit headers (`x-ratelimit-limit-requests`, `x-ratelimit-limit-parallel-requests`) and `x-request-id` are documented for the translation and transliteration endpoints only. We read them on speech responses if they are present.
- The `{"error": {"message", "code", "request_id"}}` envelope, and 429 `rate_limit_exceeded_error`, are documented for translation and transliteration only.
- The page shows no prices. It says speech to text is billed per second of audio. Pricing is linked at https://console.bodhan.ai/#pricing, which we haven't read.
- The page has no terms, licence or attribution text for the speech endpoints.

## Speech to text

- `POST /v1/audio/transcriptions`, `multipart/form-data`.
- `file` (required). `model` = `indic-transcribe` (required). `language` (optional): the vendor auto-detects without it, but the page advises passing it for non-English audio. We always pass it.
- Language codes include `hi` (Hindi), `ta` (Tamil) and `en` (English, Indian and global), among 25 codes in all.
- WAV is the documented format. FLAC, OGG and MP3 are also accepted. M4A, AAC, WebM and AMR are refused with **415**: the duration cannot be measured, so the request is not metered or transcribed.
- Up to **30 seconds** of audio per request; longer audio is rejected. No status code is given for that.
- 200: `{"text": "..."}`, in the language spoken. No timestamps and no confidence.
- Documented statuses: 200 and 415 only.

## Text to speech

- `POST /v1/audio/speech`, `application/json`.
- `model` = `indic-speak`; `input` (text; numbers, dates and currency are read in the language given); `voice` (one of 45 names); `instructions`, a **JSON string** holding an object with `lang` (required) and `style` (optional; leave it out for the voice's neutral reading).
- `lang` includes `hi`, `ta`, `en` (23 codes in all; `bhb` and `bho` are in the speech-to-text list only).
- Styles (14): `AIR style news`, `Customer Care`, `TV style news`, `advertisements`, `anger`, `children's stories`, `disgust`, `educational lecture`, `fear`, `happy`, `news`, `sad`, `single person narration audiobook`, `surprise`.
- Voices: 45, and any voice can read any language. They are grouped by recording language: Hindi Kavya, Suhani (female), Amit (male); Tamil Anitha (female), Arun (male); 23 female and 22 male across 22 languages. The full table is on the page and in `services/speech/bodhan.py` (`VOICES`).
- Length: a sentence or two per request, about 30 seconds of speech. Longer text is not split for you. No character limit is stated.
- 200: the body is `audio/wav`, PCM16, 24 kHz, mono.
- **422** if `input` is empty, `voice`, `lang` or `style` is not an accepted value, or `instructions` has no `lang`. The message names the unknown value.
- Documented statuses: 200 and 422 only.

## Not used

Translation, transliteration and document OCR.
