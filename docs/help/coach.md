# Coach and reviewer help

## What is waiting for me

Open the review screen. It lists what waits for your decision, with how long each item has waited and the results of the automatic checks. Nothing is approved automatically: unapproved content waits, and the list shows its age. Open the cohort screen for the chat: it shows posts that were reported or held, so you can hide, erase the text, restore or pin them.

## How do I approve a document

Open the item in the review screen and read its checks. You can edit it; an edit that fails the checks is not saved and says why. To send it back, choose one reason: wrong maths, culturally off, too complex for the medium, tone issue, or factually shaky. To approve, use the coach's key. Approving is gate three of four. Your approval alone does not publish anything: the programme officer's key then switches the version on.

## Checking a module's audio

Each published module is voiced by an AI voice (Bodhan AI first, Sarvam if Bodhan cannot). Open the review screen and scroll to Module audio. Each module shows whether you have approved it and how many sentences passed the check: every sentence was turned back into text and compared with the script, and a sentence marked with a warning sign is one to listen to. Open a module to play it; the sentence being said is highlighted. If one sentence sounds wrong, press Regenerate this sentence (the button shows about what it costs): only that sentence is made again. Regenerate the module makes the whole module again. Teachers keep hearing the version you last approved until you approve a new one; approving replaces the old file. A module from a cohort of fewer than 5 classes is listed but hidden, because its script and audio carry the counts of those classes. The programme officer can listen but not regenerate or approve. Listening is optional: a module is published whether or not you have listened to it. Every voice is AI-generated (Bodhan AI / AI4Bharat, or Sarvam AI).

## Which drafts came from the AI

Track modules are drafted by the AI model offline, with every class number as a slot that code fills. The review screen shows each draft with its checks. A draft that failed a code check or the second-model check is held back and marked, and the reason is shown. Reply drafts in the cohort chat are marked as drafts for a person to send or replace.

## What the automatic checks are

Code validators check numbers and sums, quotes, length, language and personal data. A rule-based pre-filter checks for profanity, personal details and off-topic text. A second model, the output checker, checks tone, safety and fit. You are the human gate after these. Rejection reasons you give are saved and shown to the checker as examples of what was rejected before.

## Which cohorts have gone quiet

The assistant cannot read cohort activity yet, so it cannot say which cohorts have gone quiet. The cohort screen shows each cohort's thread and its state: proposed, active, closing or closed.

## What you cannot see

You cannot see any one teacher's standing, and there is no ranking of teachers. You see cohort-level counts only, and only when at least five classes are behind them. The assistant cannot approve anything: approve in the review screen.

## Your time

A coach's time is capped at about thirty minutes a week, working from one weekly batch.

## Moderating the thread

The thread is moderated after posting. A post with a child's name, a roll number, a phone number or an email is not posted. Anyone can report a post, and a reported post is held until you decide. Text and voice in a thread are deleted thirty days after the cohort closes.

## Reviewing check papers and their rules

Papers shows the check papers waiting for you: papers changed by hand, papers that failed an automatic check, papers in wording not yet reviewed in that language, and a spot check of one in five papers the rules approved on their own. Open one to see its items, its answer key, the grid of which items check each error, and the automatic check results. A paper that failed a check cannot be approved: reject it with a reason, which is kept with the paper. Below the queue are the paper rules: the version in use, its item templates, every version with what changed, an export as YAML, and Test these rules, which shows five sample items for each item template and builds a sample paper for each paper layout plan (blueprint) through every automatic check. A rule change is a new version: its author submits it, and a second person publishes it; nobody approves their own change, and a published version never changes.

## Papers: create, import, assign, review and archive

On the Papers page you can create a paper from the rules or from a PDF or an answered sheet, assign any paper to a teacher, a class or a cohort in your programme, review imported papers and archive papers. Only the printed questions of an upload are read, handwriting and names are ignored and not kept, and the upload is deleted on confirmation or after 24 hours. Code computes every key and the grid of which items check which error, and the AI is never asked for an answer key. An imported paper shows Imported, awaiting review in the review queue until someone other than the importer confirms it; it is already printed, so the system does not print it. A frozen paper, one with a sheet entered, cannot change: duplicate it as a new version. A pre-test cannot be assigned to a cohort, because cohorts form from its results. Each paper shows whether cohorts have formed, or why not and the next step. The assistant asks one question at a time about anything missing and fills the draft with an Undo; it never confirms, approves, assigns or archives.

The basics are the same as for a teacher. A paper is the printed set of questions; a check is one use of it in your class. They are separate jobs, so you make or bring in a paper on the Papers page, and Enter check only asks you to choose one. Open Papers and tap Create a paper. There are two ways. Generate from rules: code builds the paper from the approved rules, from your last check's class counts, from four short questions about your class, or the standard paper. The first ten items are anchors, the same skills and level on every paper, and before and after are compared only on these; up to five adaptive items go deeper on what your class finds hard and never count as improvement. From a PDF or an answered sheet: upload a PDF or up to three photos of a paper you already used. Only the printed questions are read. Handwriting and names are ignored and not kept, and the upload is deleted when you confirm, or after 24 hours. The AI reads the questions; it never gives an answer key. Code works out every correct answer, the error each item can show and the grid of which items check which error, and a printed key that differs is flagged, never trusted. You confirm every item before the paper can be used. An item the system cannot score yet, such as a word problem, is listed as not supported: leave it out or enter it by hand. A dictated item needs the number that was said. An imported paper says Imported, awaiting review until a reviewer confirms it, and it is not printed by the system because it is already printed. Enter check uses the chosen paper's own key, worked out by code from its numbers, so an imported paper is entered like any other. Once the first sheet is entered the paper is frozen and cannot change: make a new version instead. Each paper shows whether cohorts have formed. If not, it says why and what to do next: no check has used the paper yet, a check is open with some sheets entered, every sheet is entered and not yet approved, approved but not closed, or submitted and waiting for other classes with the same error. A pre-test cannot go to a cohort, because cohorts form from its results. Papers assigned to you show at the top of Papers and in Enter check. The assistant asks one question at a time about anything missing, such as the class, the kind, the form or an unclear number, and fills in the draft from your answers. It marks what it changed with an Undo, and it never confirms, approves or assigns: you press those.

## Why did no cohort form?

A cohort forms when enough classes share the same track. Each class gets one track: writing a number as it is said (PV-HEARD) first, otherwise the mistake the most children made, and only when at least 1 child in 4 showed it with at least 10 children checked. A child shows a mistake only when it appears on at least 2 of the questions that check it. The screen gives every class's reason for each mistake: in, under 1 in 4, another track, too few children checked, or no track for that mistake yet. A class that is the first to submit waits for other classes. In production a cohort needs 15 classes (COHORT_MIN_CLASSES). The pilot and the demo allow 2, labelled "Pilot cohort, two classes". When a paper has only one question of a kind, such as borrowing across a zero (703 - 468), the 2-question rule cannot be met there. The pilot and the demo may then count that one question (COHORT_ALLOW_SINGLE_ITEM_PROBES), and the cohort says "Based on one question per child". Production leaves this off. At pilot scale there is no waitlist: both classes are trained, and the pilot compares the trained mistake with the untrained ones.

## How is the next module chosen?

Code chooses it; the AI only words it. After module 1 the teacher plays it or marks it heard, then answers Tried it, Partly or Not yet, with an optional note (a child's name is removed before it is saved). Then she can press Generate next module, and the coach can press it for her. Tried it gives the next module in the track. Partly gives the same approach again, as a smaller step with more practice. Not yet gives another approach for the same mistake from the strategy library, leaving out the approaches she has already had. If she has not answered by the set date (3 days in the demo), the planned next module is queued, and her silence is never counted as a result. Call 5 words the module from the approved module topic and strategies; if no draft comes back, code writes it from the same content. Every module goes to the coach's review queue before it reaches her, voiced in her language with her class's numbers filled in by code. A failed voice leaves the text, with a retry.

## Your cohorts and what is happening in each

Two classes, step 5 (Cohorts) lists each cohort you coach: the mistake, the number of classes and teachers, the children in the cohort who showed it, and the mentor suggestion or why there is none. It also shows module 1's status in each language, plays (system), modules marked heard (self-report), feedback (tried, partly, not yet) with notes that have names removed, the next modules' status, chat activity (open questions, AI drafts waiting, answers sent by the AI, corrections) and the next check. A timeline lists every event, with links to the review queue and the chat. Counts only, never a child. A mentor sees only her own cohort, and an officer sees totals, with any figure over fewer than 5 classes hidden.

## Modules and dates

Each cohort's improvement track is a plan of modules with due dates. Under Cohorts, each cohort shows, for every module: how many teachers are at it, how many have it made and downloaded, how many answered tried, partly or not yet, what is overdue or failed, and how many have not downloaded it after a few days. These are counts; no teacher is named.

You can move all the remaining dates earlier or later (for a holiday), with a reason, and make the next module now. A module that is already made keeps its date. Every change is recorded.

A daily job makes each module that is due, at 06:00 Indian time. Run it with python tasks.py modules-due. In production, call POST /api/modules/jobs/due once a day at 06:00 Asia/Kolkata (for example from Cloud Scheduler), with the header X-Job-Token set to MODULES_JOB_TOKEN. It is safe to run twice and catches up a missed day. If a module still cannot be made after three tries, you are told and the count shows as failed.
