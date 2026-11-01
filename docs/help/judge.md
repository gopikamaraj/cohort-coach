# Judge guide: a ten-minute test path

## What you are testing

Cohort Coach is a tool for primary teachers in India that groups them for training by the specific mistake their pupils make, and helps them rehearse the fix before using it on children. Everything in the demo is simulated or labelled as simulated. The judge guide answers from the repository, the rubric map, the deck and the video script, and gives an honest status for each claim: Built, Partly built, Simulated, Mock or Roadmap.

## Sign-in

Judge mode needs no sign-in and holds no real user's data. The staff pilot has its own sign-in, with accounts held by the team; judges do not need it. Use View as in the assistant panel to see another role's assistant on demo data. The About this product tab always answers as the judge guide.

## The path

1. Open the web app. The landing page shows four role cards and a five-minute guided tour. Ask the guide: who is the user?
2. Open the guided tour at step 1. It runs the check on sample sheets and shows the error card with where learning most likely broke down.
3. On the Judge page, choose Load a simulated class, then open My class. Each card shows a count of children, never a percentage.
4. Open Practice, choose Start, and type: Priya, what is 52 minus 29? Then type: Tell me how you got that. Open the Judge tab and choose Show AI layers to see the five layers of one turn.
5. Open the AI map and then the audit trail. Open Try to break it to see which check stops each prepared bad line.
6. Choose the Coach role on the landing page and open the review screen. Choose Officer and open the results to see one working track, one not working and one hidden under five classes.
7. On the Judge page choose Simulate offline, then open Enter check. The result waits and is sent when you go back online.
8. Switch the language in the top bar of the landing page and open My profile to see the same screens in Hindi or Tamil.
9. In the assistant, open About this product and ask: what is real and what is simulated?

## What is real and what is simulated

The error counts, the cohorts, the verdicts and the children in the Practice Class are simulated. The model calls are real: Claude reads sheet photos, labels the teacher's moves, speaks as the simulated children and drafts lessons. The pilot server is real and holds no real class data yet.

## Where to look

The rubric map, docs/RUBRIC_MAP.md, lists every claim with its status, code path, test, demo steps, slide and video time. The README table Where AI is used is generated from ai/registry.py.

## Paper Studio (check papers made by code)

As a teacher, open Papers, tap Create a paper and choose Generate from rules. Choose a new paper and tap Make the paper: you see the anchor and adaptive items, the answer key, a grid of which items check each error, the automatic check results, and its frozen post-test twin; Print opens the real PDF. As a coach, open Papers: the review queue, the published rules and Test these rules. No AI is used: code builds every paper from approved rules and an independent verifier re-checks it. Sample PDFs are in `docs/samples/` (class "SAMPLE", no child data); the rules are in `rules/paper-rules.v1.yaml`; the check of generated papers in every language is `docs/evidence/paper_studio_verification.md`.

## The demo flow, step by step

Open the Judge page and tap Run the demo flow (or open #/demo?step=1). A bar on every screen shows Demo step n of 12 (step 13, two classes, is optional), with Back, Next, the judge guide's question for the step, and Reset demo. The steps: 1 start as a teacher with a made-up class 3A; 2 make the pre-test paper in Paper Studio (the pilot paper, Form A); 3 generate 20 filled demo sheets and download them; 4 upload sheet 1 for the AI to read, then Auto-fill the other sheets from the demo answer file (no AI call); 5 review each sheet in the drawer and approve it; 6 finish entering, then Simulate other classes' results; 7 see the three cohorts (her class is in 2 of them: one this term and one next term, because a class takes one track a term); 8 make the first audio lesson (Demo: pre-approved); 9 try it in Practice Class; 10 ask the cohort a question (a 60 second wait, Skip the wait; the AI answers only from approved material and says when it has none); 11 the coach's queue and the SCERT officer's dashboard; 12 the post-test (optional) with before and after; 13 (optional) two classes to a cohort.

## What is simulated in the demo

The class, its 20 children, their answers and sheets are made up by code from demo/scenarios/class_3a.yaml and labelled Demo. The 24 other classes come from the simulated block generator and are labelled Simulated, and so is every cohort count and dashboard number. The mentor's method card is a simulated mentor's. The demo sheets are synthetic, so the reading summary is not evidence of accuracy on real handwriting. Real: Paper Studio, the sheet reader call on sheet 1, the error finder, the grouping and mentor rules, the lesson drafter and its checks, the chat service and its gates, the review queues.

## Papers page (create, import, assign, cohort status)

Papers sits between Home and Enter check. Create a paper offers two routes: Generate from rules (Paper Studio) and From a PDF or an answered sheet. In the PDF route a vision call (call 16) reads only the printed questions; code computes every key, error probe and coverage cell with the engine, an independent check agrees, a printed key that differs is flagged, and a person confirms each item. Handwriting and names are ignored and the upload is deleted on confirmation or after 24 hours. The assistant panel asks one open question at a time and its answers go through the same whitelisted edit as a typed change, tagged Assistant changed this with an Undo. Each paper shows whether cohorts formed and the reason if not. Roles: a teacher assigns only to her own class, a mentor inside the cohorts she mentors, a coach inside their programme; the officer has no access. See docs/build/reports/PAPERS-PAGE.md for what is built and what is not.

## Why did no cohort form?

A cohort forms when enough classes share the same track. Each class gets one track: writing a number as it is said (PV-HEARD) first, otherwise the mistake the most children made, and only when at least 1 child in 4 showed it with at least 10 children checked. A child shows a mistake only when it appears on at least 2 of the questions that check it. The screen gives every class's reason for each mistake: in, under 1 in 4, another track, too few children checked, or no track for that mistake yet. A class that is the first to submit waits for other classes. In production a cohort needs 15 classes (COHORT_MIN_CLASSES). The pilot and the demo allow 2, labelled "Pilot cohort, two classes". When a paper has only one question of a kind, such as borrowing across a zero (703 - 468), the 2-question rule cannot be met there. The pilot and the demo may then count that one question (COHORT_ALLOW_SINGLE_ITEM_PROBES), and the cohort says "Based on one question per child". Production leaves this off. At pilot scale there is no waitlist: both classes are trained, and the pilot compares the trained mistake with the untrained ones.

## How is the next lesson chosen?

Code chooses it; the AI only words it. After lesson 1 the teacher plays it or marks it heard, then answers Tried it, Partly or Not yet, with an optional note (a child's name is removed before it is saved). Then she can press Generate next lesson, and the coach can press it for her. Tried it gives the next lesson in the track. Partly gives the same approach again, as a smaller step with more practice. Not yet gives another approach for the same mistake from the strategy library, leaving out the approaches she has already had. If she has not answered by the set date (3 days in the demo), the planned next lesson is queued, and her silence is never counted as a result. Call 5 words the lesson from the approved lesson topic and strategies; if no draft comes back, code writes it from the same content. Every lesson goes to the coach's review queue before it reaches her, voiced in her language with her class's numbers filled in by code. A failed voice leaves the text, with a retry.

## Your cohorts and what is happening in each

Two classes, step 5 (Cohorts) lists each cohort you coach: the mistake, the number of classes and teachers, the children in the cohort who showed it, and the mentor suggestion or why there is none. It also shows lesson 1's status in each language, plays (system), lessons marked heard (self-report), feedback (tried, partly, not yet) with notes that have names removed, the next lessons' status, chat activity (open questions, AI drafts waiting, answers sent by the AI, corrections) and the next check. A timeline lists every event, with links to the review queue and the chat. Counts only, never a child. A mentor sees only her own cohort, and an officer sees totals, with any figure over fewer than 5 classes hidden.

## Recorded AI answers and AI off

The header says AI: recorded answers when the server replays recorded AI answers (AI_MODE=recorded), and each replayed answer says Recorded AI answer. It says AI: off when the AI is switched off (AI_MODE=off); then each AI feature says so and offers its non-AI path, and nothing pretends to be an AI answer. Calls 4 (method card) and 6 (digest) are planned, not built, and the AI map says so. A newly made demo sheet has no recording to replay, so in recorded mode sheet 1 says so and Auto-fill carries on. Report: docs/build/reports/QA-DEMO.md.
