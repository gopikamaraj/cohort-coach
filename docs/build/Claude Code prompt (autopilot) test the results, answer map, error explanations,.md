# Claude Code prompt (autopilot): test the results, answer map, error explanations, single-teacher cohort and Bodhan audio download in the browser, then fix and build

Paste everything below the line into Claude Code at the repo root, with the browser connected. It is written to run unattended overnight. It never asks questions.

---

**Mission.** You are on autopilot while I sleep. Using the connected browser, walk this flow end to end, find bugs and missing features, write tests, fix or build them, and verify each in the browser:

1. **The results page** for a check where about 16 students' papers have been entered and approved: check that all the content is correct and proper.
2. **An answer map:** a table of roll number against question, with each cell showing which type of error it is, like a heatmap. Beside it, the same Which items check each error matrix that the paper page shows, so the teacher sees why an error is flagged.
3. **An explanation of each error** that appears.
4. **A cohort just for this teacher** (a single-class cohort).
5. **The cohort page:** intervention content built from the results (tips, strategies and other improvement ideas for the cohort's errors). **Text first.**
6. **Audio on request:** the teacher presses a **Download audio** button, and the audio is generated with **Bodhan AI** and downloaded as a file.

## Autopilot rules (read twice)

- **Do not ask me anything.** When you must decide, choose the safer option, write the decision in `docs/build/autopilot/LOG.md` with the reason, and carry on.
- **Branch only.** Create the branch `autopilot/results-cohort-audio` from the current branch. Commit locally after each verified step with a clear message. **Never push. Never merge. Never touch main.** The submitted version is frozen.
- **Never delete or weaken a test.** If a test must change, say why in the log.
- **Keep a log** at `docs/build/autopilot/LOG.md`: a timestamped line for each step (what you observed, what you changed, which tests ran, the result). Update it after every step, so I can read it when I wake up. The log holds **counts and plain text only**.
- **Time box:** about 6 hours. Stop earlier when every item in Done when passes.
- **Stop and write a note** if: a test that passed before fails and you cannot fix it in 3 attempts (revert that change to the last good commit and move on); a secret appears in any output; a real child's name appears in any data; or a cost cap below is reached.
- **Cost caps for live calls** (put them in `.env.local` as `AUTOPILOT_MAX_TTS_CHARS=20000`, `AUTOPILOT_MAX_STT_SECONDS=300`, `AUTOPILOT_MAX_CLAUDE_CALLS=0`, and enforce them in code): **no live Claude calls at all.** Run the AI in `recorded` mode. Live Bodhan calls only for the audio download feature and its verification, and print the estimated cost before the first live call.
- **Privacy.** The papers may be real pilot data. Screenshots show roll-by-answer data, so **save them only under `data/autopilot-screens/` (git-ignored), never commit them**, and never put a per-child answer in the log or in a commit. Roll numbers only; no names. Add the folder to `.gitignore` first.
- **Browser safety.** Use the connected browser only on the app's own localhost address. Do not open any other site, do not touch other tabs, and do not use any real account. If the browser tools are not available in this session, say so in the log, and fall back to Playwright with screenshots.
- **Secrets.** Read keys only from environment variables. Never print one.
- **Honesty.** A recorded answer is labelled as recorded. Planned features are never shown as working. Content that has not been reviewed by a person is labelled as a draft.
- Follow `docs/design/stitch/DESIGN.md` (Calm Institutional), colours only from `theme.css` (add tokens there when you need them), 44 px touch targets, every string in `en`, `hi` and `ta`, and text that fits in Hindi and Tamil.

## Step 0. Preflight

1. Read `CLAUDE.md`, `DECISIONS.md`, `PROGRESS.md`, `AI_USAGE.md`, `docs/design/stitch/DESIGN.md`, the README, and the reports in `docs/build/reports/`. Find the code for: the results page and class card, My class, the error finder (`engine/diagnosis.py`, `engine/bugs.py`) and the error names (`content/lang/error_names.yaml`), cohort formation and the cohort page, the strategy and track content (`content/`), lessons, the speech layer, `finishCheck`, and the end-to-end tests.
2. Start the app with the project's documented command, in `AI_MODE=recorded` and the voice in its configured mode. Write down the address.
3. Check the speech layer: if `docs/build/reports/SPEECH-LAYER.md` exists, the Bodhan adapters are built; use them. If not, you will build the minimum needed in Part F.
4. In the browser, sign in as the teacher demo account (find the test credentials in the README or the seed data; never print a password). Open My class and find the check whose papers were uploaded. Record how many papers (rolls) are entered, approved and absent. If it is not finished, finish it through the normal screens. If there is no such check, enter the test sheets from the test folder (`demo/test-sheets/` or as the README says) through the normal Enter check flow with recorded reads, approve them all, and finish.
5. Make a backup copy of the development database before changing any schema or data. Note its path in the log.

## The loop (for every part)

Observe in the browser, then write the findings, then write a failing test, then fix or build, then verify in the browser, then run the affected tests, then commit, then log. For each finding record: severity (blocker, wrong content, missing, polish), what was expected, what you found, and the evidence (the screenshot path, the console or network message, or the test name). Fix in order of severity.

Check the browser at two sizes: a phone (390 by 844) and a laptop (1280 by 800). Read the browser console and the network log on every screen, and treat any error as a finding. Use the engine's own functions to recompute what a page shows, and compare.

## Part A. Review the results page

Check every item, and fix what is wrong:

- **Header and counts:** class, paper code, kind, date, number of children entered, absent, and not counted. The numbers equal the entered data (recompute them from the stored answers with the engine and compare).
- **Concepts and errors:** each concept shows how many children went wrong, in counts (for example 9 of 16 children), never percentages. Each error shows its name in plain words (from `error_names.yaml`), the number of children, and whether it is confirmed (the two-item rule) or possible (one question). If a single-question error is shown as confirmed, that is a bug.
- **Consistency:** totals on the class card, the diagnosis list and anything else on the page agree. A child counted under an error is counted once.
- **Wording:** no jargon, no raw codes shown to the teacher where a name exists, no English left on a Hindi or Tamil screen, no placeholder or developer text, no `undefined` or `NaN`.
- **States:** empty, loading and error states read clearly. Reopen and See results work. A check with an absent child is handled. The page is correct after a reload and after going offline and back online.
- **Privacy:** no names. The page is visible only to the teacher whose class it is (a coach or officer sees counts elsewhere, never this roll-level view).
- **Accessibility and layout:** headings in order, labels, 44 px targets, no horizontal scroll on the page body, text fits in Hindi and Tamil. Run axe on the page.

## Part B. The answer map (a heatmap table)

Add a section to the results page, **Answer map**, built on the phone from the same data and the same error finder as the rest of the page. Do not re-derive error types in the interface. Ask the engine.

- **Table:** rows are roll numbers (approved entries; absent rolls shown as one muted line or a count), columns are the paper's questions in order. The column header shows the question number and, under it, the operation (for example 703 − 468). Adaptive items carry a small tag: extra. A **total row** under the columns shows how many children got that question wrong (counts).
- **Cells:** a correct answer is a quiet tick on a pale background. A wrong answer that matches an error shows a **short code** (two or three letters) on that error's colour. A wrong answer with no matching error shows a neutral mark. Blank shows a dash, and cannot-read shows a question mark.
- **Not by colour alone:** every error type has a colour **and** a short code **and** a pattern or shape. Colours come from `theme.css` tokens (add a heatmap palette there, colour-blind safe, with a contrast check and a note in DESIGN.md).
- **Legend:** one chip per error type present, with its name, its code and the number of children. Tapping a chip highlights that error's cells and dims the rest. Tapping again clears it.
- **Cell detail:** tapping or focusing a cell opens a small popover: roll number, question and operation, the answer given, the correct answer, the error type, and one plain line on what the child likely did, with a link to its full explanation (Part C).
- **Sorting:** by roll number (default) or by number of errors. On a phone the table scrolls horizontally inside its own container, with the roll column fixed.
- **Accessibility:** a real `table` with `th` and `scope`, every cell's accessible name says roll, question and error in words, and keyboard arrow keys move between cells.
- **Local only:** the table exists only on the phone that holds the answers. Say so in one line under it: This table stays on this phone.
- **Tests:** unit tests for the cell state function and legend counts; a browser test that, for five chosen cells, the cell content equals the engine's diagnosis; a test that column totals equal the wrong counts; a test for sorting, highlighting, the popover, keyboard movement, and the phone layout; axe; Hindi and Tamil at 360 px.

## Part B2. Which items check each error (the coverage matrix)

Show, on the results page, the same matrix the paper page shows under Which items check each error: one row per error type, one column per item of the paper, a dot where an item checks that error, and a final column that counts the items. **Reuse the existing component and the paper's own data. Do not retype or re-derive it.** Put it under the answer map, in a section called **Why an error is flagged**, open by default on a laptop.

- **Fix what is wrong in the current rendering.** In the current version the headers for items 10 to 15 break onto two lines (1 over 0), the word Items breaks as Ite and ms, and error names break across lines (PV- over HEARD). Make header cells non-wrapping with a minimum width, show the error code with its plain name from the error names file, and keep the table inside its own horizontal scroll container on a phone with the error column fixed. Check it at 360, 390 and 1280 px.
- **Add this class's numbers.** Add a column Children in this class: the count confirmed, and the count possible, using counts only. Show every error the paper checks, even when the count is 0, so the teacher sees which errors were not found.
- **Say the rule in plain words** under the table: An error is confirmed when a child makes it on at least two of its items. On one item it is shown as possible. Read the thresholds from the engine and do not hard-code them.
- **Say when errors share items.** In the current matrix PV-HEARD and PV-REVERSE share items 1 and 2, and SUB-SFL and SUB-NODEC share items 7 to 10, 14 and 15. Add a note: where two errors share items, the child's actual answer decides which error it is.
- **Link it to the answer map.** Choosing an error row highlights its items in this matrix and marks those columns in the answer map. Choosing a column in the answer map highlights the errors that item checks.
- **Items tagged extra** (adaptive) are marked in the header.
- **Check the data, too.** Compare the matrix with the engine's error probes for this paper. If a dot is missing or extra, or an item count is wrong, log it as a finding and fix the source of the data.
- **Not by colour alone, and accessible.** A real table with a caption and header scopes. Each dot has a text alternative such as Item 7 checks SUB-SFL, and blank cells say does not check to a screen reader.
- **Tests:** the component renders from the paper's data and equals the paper page's matrix; each row's item count equals its dots; the children column equals the class card; header cells do not wrap at 360 px; the row and column highlighting works both ways; axe; Hindi and Tamil fit.

## Part C. Explain each error

For every error type that appears in the class, show a clear explanation, from the legend chip and from each cell popover, in a panel or a section called **What each error means**.

- **Source:** approved content in `content/` (create `content/errors/explanations.v1.yaml` if there is none). Fields, in English with Hindi and Tamil where they exist: name, **what the child is doing** (the procedure in one or two sentences), **an example worked from this class's own question** (computed with the engine's bug function for that error on that question, for example: the child takes the smaller digit from the larger in each column, so 703 − 468 gives 365, the correct answer is 235), **why it happens**, **how to spot it** in a child's work, and **what to do first**. The example must be computed by code, not typed.
- **In this class:** for each error, the number of children (a count), the questions where it appeared, and the most common wrong answer.
- **Status:** any explanation text that you write yourself is marked `status: draft` with `TODO-HUMAN(Seema): review`, shown to teachers with a small label Draft until a coach approves it (in judge mode, the existing Demo: pre-approved badge). Reuse existing content first. List every new piece of text in the report.
- **Tests:** every error code that the engine can produce has an explanation (a test fails if one is missing); examples equal the bug function's output; counts equal the class card; layout and language checks.

## Part D. A cohort just for this teacher

- On the results page and the cohort area, add **Create a cohort for my class**. It opens a short form: choose which errors to work on (a checklist of this class's errors with counts, the most common one pre-selected) and a name (pre-filled). Confirm creates a **single-class cohort**.
- It uses the existing cohort model with a clear scope marker (for example `scope: class_only`). It stores counts only. It is labelled **Just my class: no other teachers yet**, on every screen where it appears. When other classes with the same error arrive, the existing cohort logic may offer to merge them. Do not build the merge now.
- Policies: the production minimum number of classes is not changed. The single-class cohort is a separate, labelled path. Record this in `DECISIONS.md`.
- The cohort appears in My programme and on the cohort page. A coach sees it in the Cohorts view as a single-class cohort, in counts.
- **Tests:** creating it, the errors chosen, the label, no other teacher's data, the coach's view, a reload, and offline behaviour.

## Part E. The cohort page: intervention content (text first)

On the cohort page add **Intervention content**, built **from the results**, for each of the cohort's errors (most common first):

1. **What you are seeing in your class** (counts and the example from Part C).
2. **Why children do this.**
3. **A two-minute check** to confirm it with a few children.
4. **Strategies to try** (up to three), each with steps, simple materials (bundles of sticks, place-value cards, a number line, stones) and where it comes from (the source label from the library).
5. **A ten-minute activity** for a small group.
6. **Common mistakes when teaching this.**
7. **How to know it is working** (what to look for in the next check).
8. **Ideas to practise in free time or at home.**
9. **If it does not improve**, another approach to try.

Rules for the content:

- **Build it from approved content first.** Look in `content/` for strategy cards, track content, lessons and scripts for each error code, and assemble the sections from them **in code**. Do not call the AI for this feature. The AI is in `recorded` mode, and no live Claude calls are allowed.
- Where the library has no content for a section, **do not invent it silently.** Show only the sections that have content, and add a clearly marked draft entry in the content files (`status: draft`, `TODO-HUMAN(Seema): review`, written plainly and grounded in the existing library's style and sources, with no claims you cannot source). List every new piece in the report as a **content gap**.
- **Text first.** The whole pack reads well as text on a phone, with the sections collapsible, and prints cleanly. Nothing plays by itself.
- Language: use the Hindi and Tamil text where it exists. Where a language version does not exist, show English and a note saying the Hindi or Tamil version is not available yet. Do not machine-translate in this session.
- Counts, not percentages. No names. A Draft label where it applies.
- **Tests:** the pack is built from the cohort's errors; every section comes from content with a source; a missing section is omitted and logged, not invented; the text uses the class's real numbers from the engine; the page is correct on a phone and a laptop; axe; Hindi and Tamil fit.

## Part F. Audio download with Bodhan

Each section of the pack gets a **Download audio** button, and the whole pack gets one too. Pressing it generates the audio from the **text shown** and downloads an MP3 file. Nothing is generated until it is pressed.

- **If the speech layer exists** (`SPEECH-LAYER.md`), use it. **If it does not, build the minimum yourself**, in the same shape: an interface with a Bodhan text-to-speech adapter first and the existing Sarvam adapter as the fallback.
- **Read Bodhan's API reference** at `https://console.bodhan.ai/api-docs/` and save a dated copy to `docs/vendors/bodhan/api-reference.md` (if you cannot fetch it, use the summary below and log that you could). Key facts: `POST https://api.bodhan.ai/v1/audio/speech`, bearer key, JSON body with `model` set to `indic-speak`, `input`, `voice` (a name such as Kavya for Hindi, Anitha for Tamil), and `instructions`, which is **a JSON string** such as `{"lang": "hi", "style": "educational lecture"}`; `lang` is required; each request must be **a sentence or two, about 30 seconds of speech, and longer text is not split for you**; the reply is a WAV (PCM16, 24 kHz, mono); a bad voice, language or style gives 422.
- **Keys** from the environment: `BODHAN_SPEAK_API_KEY` (fall back to `BODHAN_API_KEY`), and the base URL `BODHAN_BASE_URL` (default `https://api.bodhan.ai`). Never print a key. Check that `ffmpeg` is available and say so in the log if it is not.
- **Pipeline:** split the text into sentences (aware of the Hindi danda, and never splitting inside a sum such as 703 − 468), group into chunks of one or two sentences (target 220 characters, hard maximum 300), generate chunks in parallel with a limit of 3, retry a chunk once, stitch with a short silence between sentences and a longer one between paragraphs, normalise the loudness, and encode a mono MP3 at 48 kbps. If a provider fails on any chunk, regenerate the whole file with the fallback provider, so the voice never changes midway. If all fail, keep the text and say the audio could not be made, with a Try again button.
- **Voice and style:** one narrator voice per language from `content/voices.yaml` (create it if it does not exist: Hindi Kavya, Tamil Anitha, English a voice that reads English well, each marked `TODO-HUMAN(Seema): confirm by listening`), with the style set to `educational lecture`.
- **Cache** each chunk and each finished file by a hash of the provider, voice, language, style and the text, so a repeat press makes no call.
- **The button's behaviour:** it shows Preparing the audio with a progress line, then downloads the file named from the error and the language (for example `intervention-sub-sfl-en.mp3`), and shows the file size. A label says **AI-generated voice**. It is disabled with a reason when the phone is offline. Respect a per-user cap on characters and say plainly when it is reached. No audio is kept on the phone beyond the download.
- **Verify live, within the caps:** press one Download audio button in English, and one in Hindi or Tamil if that content exists. Then check the file in code: it exists, `ffprobe` gives a duration close to the expected length from the text, it is not silent, and, if the budget allows, a round trip through Bodhan's speech-to-text (send each piece under 30 seconds, as WAV) returns text close to the source. Log the characters used and the estimated cost. Use the mock provider for every automated test.
- **Tests:** sentence splitting and chunk sizes (including sums and the Hindi danda), the request body with `instructions` as a JSON string, the mock provider's success, 422, 429, 5xx and timeout, the whole-file fallback, the cache, the cap, the file name, offline disabling, no key in any log, and a browser test that the button starts a download with the mock.

## Part G. Cross-cutting checks

On the screens you touched: roles (teacher sees her class's map; coach and officer do not see roll-level data; a different teacher cannot open this class), Hindi and Tamil, accessibility with axe, offline and reload behaviour, the console and network log without errors, and performance (usable within about 3 seconds on a throttled phone profile). Make sure the existing end-to-end tests still pass. Run the project's full test suites at the end and report the counts before and after.

## Finish

1. Write `docs/build/autopilot/REPORT.md`: for each part, what you observed, the findings by severity, what you fixed or built, the tests that cover it, what you could not do and why, the content gaps and every new piece of text for Seema to review, the live calls made and their cost, and the test counts before and after.
2. Update `docs/design/stitch/INVENTORY.md`, the help documents, the README and `DECISIONS.md` (entry dated today).
3. Write a short **morning summary** at the top of the log: three lines on the state, and the five things I should look at first.
4. Stop the servers you started. Leave everything committed locally on the branch, and unpushed.

**Done when** the results page is verified correct in the browser and by recomputation, the answer map shows the engine's error types per roll and question, the results page shows the coverage matrix with this class's counts and the plain-words rule, every error has an explanation computed from the class's own question, a single-class cohort can be created, the cohort page shows text-first intervention content from approved content with drafts clearly labelled, Download audio produces a valid MP3 through Bodhan within the caps, the tests pass, axe is clean on the new screens, and the report and log are written.
