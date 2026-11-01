# Teacher help: today, when you are stuck, and what the audio is

## What should I do today

Open My programme. It shows the step you are on: the check, your cards, a lesson, or the next check. Do that one step. If you have not entered a check yet, start with Enter check. If you have, open My class to see your cards, then the lesson in My programme. Plan for no more than about twenty minutes a week: the app is built around that limit.

## What an error card means

A card names one mistake and says how many of your children make it. A child is counted only if the mistake showed on at least two questions that test it, so one slip is not counted. The example under the count comes from your own class. The card never says why a child made the mistake for certain; it only says what is most likely, and a one-minute question you can ask a child to check.

## How is my class doing since the last check

The app shows change in children only after the next check, not before. Until then, My programme says "awaiting next check". The number of lessons delivered tells you what was sent, not whether children improved. When the next check is entered, My programme shows the comparison.

## I'm stuck, what can I try

- Try the lesson for your class's focus again with only three children, using bundles of ten and loose sticks.
- Ask the child to explain how they got their answer before you correct it.
- Check by adding back: if 52 minus 29 is 23, then 23 plus 29 should be 52.
- Rehearse in Practice first, then try it in class.
- Tap the flag on any card that looks wrong, so the team can review it.

## Why was this audio chosen

A lesson comes from the track for your cohort's mistake, which a coach has approved. The app picks the lesson that follows the last one you finished. It does not pick lessons by how well you teach, and it never scores a teacher. Each lesson shows a badge: Checked means the app's automatic checks passed, and Reviewed means a coach also approved it.

## If a lesson did not work

A track that does not work is a fault of the track, not of you. After a lesson, tap that it did not work, and the team reads it as feedback on the track.

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

## How is the next lesson chosen?

Code chooses it; the AI only words it. After lesson 1 the teacher plays it or marks it heard, then answers Tried it, Partly or Not yet, with an optional note (a child's name is removed before it is saved). Then she can press Generate next lesson, and the coach can press it for her. Tried it gives the next lesson in the track. Partly gives the same approach again, as a smaller step with more practice. Not yet gives another approach for the same mistake from the strategy library, leaving out the approaches she has already had. If she has not answered by the set date (3 days in the demo), the planned next lesson is queued, and her silence is never counted as a result. Call 5 words the lesson from the approved lesson topic and strategies; if no draft comes back, code writes it from the same content. Every lesson goes to the coach's review queue before it reaches her, voiced in her language with her class's numbers filled in by code. A failed voice leaves the text, with a retry.

## Entering a check: roll numbers, absent children and finishing

Enter check works from a paper that already exists. Choose it (papers assigned to you come first), check the date, say how many papers there are, and tap Start the check. If there is no paper for your class yet, use Create a paper to go to Papers; Enter check never makes one. Then work one roll number at a time. The roll list shows each roll number as Not entered, Entered, or Absent, and as Approved or Not approved, with a line of counts above it. Add a sheet by typing the answers, by Take a photo of this sheet, or by Select a folder of pictures (where your phone cannot choose a folder, Choose pictures lets you pick many from the gallery). The AI reads the picture and fills the boxes, marking the ones it is unsure of; it is a suggestion. Tap the small picture icon beside the roll list to see the sheet beside the boxes, compare, correct, and tap Approve. Typed answers need approving too. Tick Absent today for a child who was away; that approves the roll number. Under the boxes, tick Missed the teaching for the topics your register says were missed; the question numbers come from the paper. Finish entering is switched on only when every roll number is approved or absent, and a note above it names the ones that are not. Pictures are read and dropped: they are held in memory only and are gone when you finish or leave the page. To change something afterwards, open Enter check and tap Reopen, then Finish entering again to update the results.

## When the AI is not available

If the AI service is down, the top of the screen says AI: off, and each part that needs it tells you so: type the answers instead of reading a photo, the lesson comes from the approved template and is shown as text, and your chat question waits for your mentor or coach. Nothing you entered is lost.
