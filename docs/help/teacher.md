# Teacher help: today, when you are stuck, and what the audio is

## What should I do today

Open My programme. It shows the step you are on: the check, your cards, a module, or the next check. Do that one step. If you have not entered a check yet, start with Enter check. If you have, open My class to see your cards, then the module in My programme. Plan for no more than about twenty minutes a week: the app is built around that limit.

## What an error card means

A card names one mistake and says how many of your children make it. A child is counted only if the mistake showed on at least two questions that test it, so one slip is not counted. The example under the count comes from your own class. The card never says why a child made the mistake for certain; it only says what is most likely, and a one-minute question you can ask a child to check.

## How is my class doing since the last check

The app shows change in children only after the next check, not before. Until then, My programme says "awaiting next check". The number of modules delivered tells you what was sent, not whether children improved. When the next check is entered, My programme shows the comparison.

## I'm stuck, what can I try

- Try the module for your class's focus again with only three children, using bundles of ten and loose sticks.
- Ask the child to explain how they got their answer before you correct it.
- Check by adding back: if 52 minus 29 is 23, then 23 plus 29 should be 52.
- Rehearse in Practice first, then try it in class.
- Tap the flag on any card that looks wrong, so the team can review it.

## Why was this audio chosen

A module comes from the track for your cohort's mistake, which a coach has approved. The app picks the module that follows the last one you finished. It does not pick modules by how well you teach, and it never scores a teacher. Each module shows a badge: Checked means the app's automatic checks passed, and Reviewed means a coach also approved it.

## If a module did not work

A track that does not work is a fault of the track, not of you. After a module, tap that it did not work, and the team reads it as feedback on the track.

## Practice, step by step

Open Practice, then Start. Say or type what you would say to the children, for example: "Priya, what is 52 minus 29?" Open Materials to show bundles of ten. When you are done, tap End and see feedback. If you name a real child, the name is removed before anything is sent to the AI; the five pretend children keep their names. Rehearsing is a way to try a move safely. No source has shown yet that it changes children's results; the pilot will test that.

## Speaking in Practice

Hold the button while you speak and let go when you finish. A timer shows how many seconds you have used, up to 25. At 25 seconds the recording stops by itself, with the message "That is the longest we can listen to at once. Say the rest in a second message." What you said in those 25 seconds is still used. A very short or silent recording is not sent: you see "I didn't catch that. Try again." Silence is never scored. Your recording is sent to a speech service (Bodhan AI, or Sarvam if Bodhan cannot) to be turned into text, then dropped; it is never kept. The text of what was heard is always shown. Each pretend child keeps one voice for the whole practice, and the voice sounds happier or sadder as the engine's mood for that child changes. The voices are AI-generated. If the voice stops working, or this practice has used its share of speech, you see "Voice is off for the rest of this practice. The text continues." and you carry on by typing.

## Telegram

Telegram is planned for later and is not available now. For now, use the web app for every step.

## How do I print a check paper

Open Papers, tap Create a paper and choose Generate from rules. Choose the pilot paper (Form A before training, Form B after it), whose answers you can enter on this phone, or a new paper for your class, which you print and mark by hand with its answer key. A new paper is built from your last check's class counts, or from four short questions about your class, or it is the standard paper. A topic you have not taught is left off the paper, so no child is flagged for it. Pick the language and tap Make the paper. The first ten items are anchors: the same skills and level on every paper, and before and after are compared only on these. Up to five adaptive items go deeper on what your class finds hard; they help find errors and never count as improvement. A pre-test makes its post-test twin at the same time, frozen until the track ends. Only an approved paper prints; a paper in wording nobody has reviewed yet waits for a reviewer. Once the first sheet is entered, the paper is frozen. All your papers are on the Papers page. No AI writes a paper: code builds it from approved rules.

## Papers: make a paper, bring one in, and see what became of it

A paper is the printed set of questions; a check is one use of it in your class. They are separate jobs, so you make or bring in a paper on the Papers page, and Enter check only asks you to choose one. Open Papers and tap Create a paper. There are two ways. Generate from rules: code builds the paper from the approved rules, from your last check's class counts, from four short questions about your class, or the standard paper. The first ten items are anchors, the same skills and level on every paper, and before and after are compared only on these; up to five adaptive items go deeper on what your class finds hard and never count as improvement. From a PDF or an answered sheet: upload a PDF or up to three photos of a paper you already used. Only the printed questions are read. Handwriting and names are ignored and not kept, and the upload is deleted when you confirm, or after 24 hours. The AI reads the questions; it never gives an answer key. Code works out every correct answer, the error each item can show and the grid of which items check which error, and a printed key that differs is flagged, never trusted. You confirm every item before the paper can be used. An item the system cannot score yet, such as a word problem, is listed as not supported: leave it out or enter it by hand. A dictated item needs the number that was said. An imported paper says Imported, awaiting review until a reviewer confirms it, and it is not printed by the system because it is already printed. Enter check uses the chosen paper's own key, worked out by code from its numbers, so an imported paper is entered like any other. Once the first sheet is entered the paper is frozen and cannot change: make a new version instead. Each paper shows whether cohorts have formed. If not, it says why and what to do next: no check has used the paper yet, a check is open with some sheets entered, every sheet is entered and not yet approved, approved but not closed, or submitted and waiting for other classes with the same error. A pre-test cannot go to a cohort, because cohorts form from its results. Papers assigned to you show at the top of Papers and in Enter check. The assistant asks one question at a time about anything missing, such as the class, the kind, the form or an unclear number, and fills in the draft from your answers. It marks what it changed with an Undo, and it never confirms, approves or assigns: you press those.

## Why did no cohort form?

A cohort forms when enough classes share the same track. Each class gets one track: writing a number as it is said (PV-HEARD) first, otherwise the mistake the most children made, and only when at least 1 child in 4 showed it with at least 10 children checked. A child shows a mistake only when it appears on at least 2 of the questions that check it. The screen gives every class's reason for each mistake: in, under 1 in 4, another track, too few children checked, or no track for that mistake yet. A class that is the first to submit waits for other classes. In production a cohort needs 15 classes (COHORT_MIN_CLASSES). The pilot and the demo allow 2, labelled "Pilot cohort, two classes". When a paper has only one question of a kind, such as borrowing across a zero (703 - 468), the 2-question rule cannot be met there. The pilot and the demo may then count that one question (COHORT_ALLOW_SINGLE_ITEM_PROBES), and the cohort says "Based on one question per child". Production leaves this off. At pilot scale there is no waitlist: both classes are trained, and the pilot compares the trained mistake with the untrained ones.

## How is the next module chosen?

Code chooses it; the AI only words it. After module 1 the teacher plays it or marks it heard, then answers Tried it, Partly or Not yet, with an optional note (a child's name is removed before it is saved). Then she can press Generate next module, and the coach can press it for her. Tried it gives the next module in the track. Partly gives the same approach again, as a smaller step with more practice. Not yet gives another approach for the same mistake from the strategy library, leaving out the approaches she has already had. If she has not answered by the set date (3 days in the demo), the planned next module is queued, and her silence is never counted as a result. Call 5 words the module from the approved module topic and strategies; if no draft comes back, code writes it from the same content. Every module goes to the coach's review queue before it reaches her, voiced in her language with her class's numbers filled in by code. A failed voice leaves the text, with a retry.

## Entering a check: roll numbers, absent children and finishing

Enter check works from a paper that already exists. Choose it (papers assigned to you come first), check the date, say how many papers there are, and tap Start the check. If there is no paper for your class yet, use Create a paper to go to Papers; Enter check never makes one. Then work one roll number at a time. The roll list shows each roll number as Not entered, Entered, or Absent, and as Approved or Not approved, with a line of counts above it. Add a sheet by typing the answers, by Take a photo of this sheet, or by Select a folder of pictures (where your phone cannot choose a folder, Choose pictures lets you pick many from the gallery). The AI reads the picture and fills the boxes, marking the ones it is unsure of; it is a suggestion. Tap the small picture icon beside the roll list to see the sheet beside the boxes, compare, correct, and tap Approve. Typed answers need approving too. Tick Absent today for a child who was away; that approves the roll number. Under the boxes, tick Missed the teaching for the topics your register says were missed; the question numbers come from the paper. Finish entering is switched on only when every roll number is approved or absent, and a note above it names the ones that are not. Pictures are read and dropped: they are held in memory only and are gone when you finish or leave the page. To change something afterwards, open Enter check and tap Reopen, then Finish entering again to update the results.

## When the AI is not available

If the AI service is down, the top of the screen says AI: off, and each part that needs it tells you so: type the answers instead of reading a photo, the module comes from the approved template and is shown as text, and your chat question waits for your mentor or coach. Nothing you entered is lost.

## Reading the results: answer map, why an error is flagged, what it means

Open My class after you finish a check. Under the findings, the answer map has one row for each child (by roll number) and one column for each question. A tick means correct. Two letters show which mistake the answer matches, with a colour and a pattern: PH writes a number the way it is said, PR swaps tens and ones, AC forgets the carried ten, SF takes the smaller digit from the larger, SN borrows a ten but does not reduce the tens digit. A cross means wrong with no known mistake, a dash means left blank, a question mark means it could not be read. A dashed edge means the child made the mistake once only, so it is possible, not confirmed. Tap a mistake in the list above the table to highlight it; tap a box to see the answer given, the correct answer and what the child likely did. Under the table, Why an error is flagged shows which questions check each mistake and how many children in your class made it. The table stays on this phone. What each error means explains each mistake with an example from your class. These explanations are drafts until a coach approves them.

## A cohort for your class and its ideas to try

On My class, tap Create a cohort for my class, choose the mistakes to work on (the most common one is chosen for you) and confirm. It is just your class, with no other teachers yet, and only counts are saved. Open the cohort page to read the improvement track: what you are seeing, why children do this, a two-minute check, strategies to try, a ten-minute activity, common teaching mistakes, how to know it is working, ideas for home, and what to try if it does not improve. Everything is text first. Tap Download audio on a section, or for the whole pack, to get an MP3 file made with an AI-generated voice; it needs a connection, and nothing is made until you tap. Hindi and Tamil text is not written yet, so those pages show English with a note.

## Your improvement track: modules

Your improvement track is a few short modules, one after another, each with a due date. Module 1 is ready as soon as you start the track. Later modules show only a title and a date until their turn.

Use Module 1 in class, then tell us how it went: It worked, It partly worked, Not yet working or I didn't try it yet. Then press Get the next module. Until you answer, that button is closed and says when the next module will arrive by itself.

What you answer decides the next module. It worked moves you to the next module in the plan. It partly worked gives the same approach again as a smaller step. Not yet working gives a different approach. I didn't try it yet is a pause, not a result: the module stays open, the next date moves by 7 days (at most twice), and you can pick a reason, read a shorter version or ask your mentor or coach. After the second pause the planned module comes by itself, and Get the next module works whenever you want it. If you do not answer, the next module still comes on its due date, and we do not count the silence as a result. You can answer late: the answer is saved with its module and only changes modules that are not made yet.

Each module has Why this module? with the reason, the text you can read or hide, and Download audio. A track has at most six modules. If the plan runs out or the limit is reached, the app tells you to talk to your mentor or coach. When the track is finished it says it is time for the next check. Making a module needs a connection; modules you already have, and audio you downloaded, work offline.

## Your check-in is private

When you answer a module, the answer, your note and any follow-up questions are saved for you alone. A lock on every step says so, and every step has a Skip. Nothing reaches the cohort chat unless you read the exact text and press Share with my cohort.

After your answer you may see one or two short questions (or a Skip), then a line that says what changes next, written by the app from what you told us. Then comes the choice to share a short summary with your cohort. The text is shown in a box you can edit. It is built from your answer, what the app understood from your note, and your note with names removed. You choose the parts: how it went, your note, what you would like help with, how many children in your class (counts only, off by default) and your chat name (off by default; otherwise it says "A teacher in this cohort"). It never contains a child's name, a roll number, a class code or a percentage, and if you type one the button explains what to remove. Pressing Share twice posts it once. You can Retract it later, and you can share it later until the next module is made. If you ask for help, your question goes through the normal question flow, where a coach checks any AI draft.

If you do not want to share, press Don't share. Coaches and mentors see only how many teachers answered worked, partly, not yet or not tried, never your note, unless you shared it. If your note suggests you or a child may be in difficulty, the app says so gently and shows Ask my coach to call me. Your coach is told only if you press it, and nothing you wrote is sent.
