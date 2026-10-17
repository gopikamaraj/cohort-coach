# Test round 3: Practice Class usability (21–25 Oct)

For Seema. Five primary teachers, ten minutes each, think-aloud. Nobody on the team may be a tester. Written consent from every teacher first. No child names anywhere: not on paper, not in the notes. Hindi lines for the participant are in the right-hand column of each table; Shivani reviews the Hindi (`TODO-HUMAN(Shivani)`).

## Before you start

- The app and this script are in English and Hindi. A Tamil-speaking tester uses the English text with a facilitator who speaks Tamil; a Tamil script is parked in `docs/build/PARKING.md`.

- Open the staging URL on the teacher's own phone if you can (`docs/deploy.md` has the steps; the URL goes in `docs/build/PROGRESS.md`). If staging is not up yet, use `python tasks.py dev` on a laptop with a hotspot, or the offline stub: `python tasks.py practice --stub` (the stub is a rule-based stand-in, **not** the real AI: do not use it for the "sounds like my class" rating).
- Give each teacher a participant code (T3-01, T3-02, …). Names stay on the consent form only.
- The app opens in judge mode. Choose the Teacher role, and the teacher's language.
- Tell the teacher: "We are testing the app, not you. There are no wrong answers. Please say out loud what you are thinking."

## Consent reminder (read aloud)

| English | हिंदी (draft) |
| --- | --- |
| "What you say to the pretend children is not kept on our servers. It stays on this phone. We will write down what you say about the app, with a code instead of your name. You can stop at any time." | "आप नकली बच्चों से जो कहेंगी वह हमारे सर्वर पर नहीं रखा जाता। वह इसी फ़ोन पर रहता है। ऐप के बारे में आप जो कहेंगी उसे हम आपके नाम की जगह एक कोड के साथ लिखेंगे। आप कभी भी रुक सकती हैं।" |

## The ten minutes

| Minute | What you ask the teacher to do | What you watch for |
| --- | --- | --- |
| 0–1 | Open the app and find Practice | Can she find it without help? |
| 1–2 | Start practice. Read the five children's names aloud | Does she notice the shy child? |
| 2–7 | "Teach the children how to do 52 minus 29, the way you would in your class." Let her type or tap the materials | Where does she hesitate? Does she use the materials tray? Does she name a child? |
| 7–8 | Press "End and see feedback". Ask her to read it aloud | Does she understand "what went well" and "one thing to try"? Does she accept the quotes as her own words? |
| 8–9 | "Try again with the same children" once, or stop | Does she want to retry? |
| 9–10 | Questionnaire (below) | |

Note, for every point: the minute, what she did or said (a quote if you can), and whether the app helped or got in the way. Do not help unless she is stuck for more than a minute; note when you did.

## Two ratings after the rehearsal

1. **"Sounds like my class", 1 to 5.** "How much did the pretend children sound and make mistakes like the children in your own class?" 1 = not at all, 5 = exactly like them. (This is the realism rating for the child-voice eval.)
2. **"Was the feedback useful", 1 to 5.** (This is the usefulness rating for the feedback eval.)

## System Usability Scale (10 statements, 1 = strongly disagree, 5 = strongly agree)

| # | English | हिंदी (draft) |
| --- | --- | --- |
| 1 | I think that I would like to use this app frequently. | मुझे लगता है कि मैं इस ऐप का बार-बार इस्तेमाल करना चाहूँगी। |
| 2 | I found the app unnecessarily complex. | मुझे ऐप ज़रूरत से ज़्यादा जटिल लगा। |
| 3 | I thought the app was easy to use. | मुझे ऐप इस्तेमाल करना आसान लगा। |
| 4 | I think that I would need the support of a technical person to be able to use this app. | मुझे लगता है कि इस ऐप को चलाने के लिए मुझे किसी तकनीकी व्यक्ति की मदद चाहिए होगी। |
| 5 | I found the various functions in this app were well integrated. | मुझे ऐप के अलग-अलग हिस्से आपस में अच्छी तरह जुड़े लगे। |
| 6 | I thought there was too much inconsistency in this app. | मुझे ऐप में बहुत ज़्यादा बेमेलपन लगा। |
| 7 | I would imagine that most people would learn to use this app very quickly. | मुझे लगता है कि ज़्यादातर लोग इस ऐप को बहुत जल्दी सीख लेंगे। |
| 8 | I found the app very cumbersome to use. | मुझे ऐप इस्तेमाल करने में बहुत बोझिल लगा। |
| 9 | I felt very confident using the app. | ऐप इस्तेमाल करते हुए मुझे पूरा भरोसा महसूस हुआ। |
| 10 | I needed to learn a lot of things before I could get going with this app. | इस ऐप को शुरू करने से पहले मुझे बहुत कुछ सीखना पड़ा। |

## Entering the results

1. Add one row per teacher to `docs/user-testing/round3-results.csv` (start from `round3-results-template.csv`). Participant codes only; no names, no school names, no child names.
2. Run `python scripts/round3_summary.py`. Code computes the SUS score for each teacher (odd items: score − 1; even items: 5 − score; sum × 2.5) and the group mean, the "sounds like my class" median and the share who finished. With five teachers the summary carries the note "read as directional".
3. For each thing that confused a teacher, add a row to `docs/feedback-log.md` ("You said → We changed", with the commit that changed it) or use `/log-feedback`.
4. Do not type any figure into the deck by hand: copy it from `docs/evidence/round3_summary.json`.

## What the app must not do during the test

It must never show a score or a percentage to the teacher. If it does, stop and tell Gopi.
