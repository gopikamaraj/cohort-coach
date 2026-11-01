# Claude Code prompt: pilot sheets as a local demo data source (folder, ingest script, answer file, Enter check option)

Paste everything below the line into Claude Code at the repo root. It builds on the Demo Studio, check record and Paper Studio prompts. Reuse the Demo Studio's answer-file format and loader. Do not invent a second one.

---

**Task.** Add the **pilot pre-test sheets** (two classrooms, two teachers) as a second demo data source next to the synthetic sheets:

1. A local folder for the answered sheets.
2. An ingest script that tidies the photos and writes one JSON answer file: the test, its questions, and for every child every question's given answer, whether it is right, and the diagnosis inputs.
3. On the **Enter the check** screen, a **Data source** option: **Synthetic** or **Pilot**. With Pilot, the teacher selects a sheet for the **first roll number** and the AI reads it live. **Auto-fill** loads the other roll numbers from the answer file.

**Why.** The demo video and the hands-on demo are stronger on real sheets. The reading evidence is also real: we can compare the AI's read with hand-keyed truth.

## Rules that cannot be broken

- **Real children's data never goes into the repository.** The folder `data/pilot/` is git-ignored, and a test fails if any file under it is tracked. The same applies to the JSON, the images and any derived file that holds child-level answers. Counts only may be committed.
- **The Pilot option exists only on a machine that has the folder.** It is hidden unless the setting `PILOT_DEMO=1` is on, the folder exists, and a valid `data/pilot/manifest.yaml` with a consent note is present. The hosted judge demo never has the folder, so judges see Synthetic only. Confirm this in a test.
- **Consent first.** `manifest.yaml` must contain `consent_confirmed: true`, who confirmed it, the date and the scope (for example "internal demo and the project video"). Without it the option stays disabled with a plain explanation.
- **No names.** Sheets carry roll numbers only. The ingest script scans every sheet for a printed or written person's name and blacks out the region in the normalised copy. A human must review those sheets.
- **Pilot data is labelled.** Every screen showing it carries a **Pilot data: real sheets, roll numbers only** banner. Sheets loaded from the answer file are labelled **Read from pilot answer file**. The sheet read live is labelled **Read by AI**.
- **No external leak.** Pilot images are served only through an authenticated local route, never cached by the service worker, never bundled into the build, and never sent anywhere except the model call for the sheet the teacher selects (the same call the product makes in pilot mode).
- Follow DESIGN.md. Do not change behaviour of the Synthetic path.

**Step 0. Read first.** Read CLAUDE.md, DECISIONS.md, PROGRESS.md, docs/pilot/, the Demo Studio code (answer file `reads.json`, its loader, the labels), the check record and Enter the check screen, call 8 (answer reading), the Paper Studio pilot Form A record and its golden files in `tests/fixtures/`, `engine/bugs.py` and `engine/diagnosis.py`, and the settings and role code.

## Step 1. The folder

Create this layout, all git-ignored, and add `docs/pilot/PILOT-DEMO.md` (tracked, no data) that explains it:

```
data/pilot/
  raw/            the photos as received, untouched
  sheets/         normalised copies: {classcode}-roll{NN}.jpg
  truth/          optional hand-keyed CSVs: 3A.csv, 3B.csv (roll, q1 to q15)
  manifest.yaml   classes, strengths, teacher labels, consent note, review flags
  pilot_answers.json   generated answer file
  ingest_report.md     generated, counts and review items
```

`manifest.yaml` holds, per class: the class code (for example 3A, 3B), class strength, a teacher label (T1, T2: no names), the test date and the dictated numbers if they differ by class (the pilot used different dictation numbers per class). The roll numbers with no sheet are listed as `no_sheet`.

## Step 2. The ingest script

Add `tools/pilot/ingest.py` and the command `python tasks.py pilot-ingest`. It is idempotent and offline except for the optional AI steps, which are cached and cost-capped.

1. **Tidy.** For each file in `raw/`: fix EXIF orientation, detect and fix 90-degree rotation, downscale to a long edge of about 1600 px, save as JPEG.
2. **Duplicates.** Detect duplicates and near-duplicates by hash and perceptual hash. Keep the best-lit, sharpest copy per child. List dropped files in the report.
3. **Class and roll.** Use the file name if it follows a pattern. Otherwise read the class and roll from the sheet's header with the AI (the printed roll box and check code). Rename to `{classcode}-roll{NN}.jpg`. Anything uncertain goes to the review list. Never guess silently.
4. **Name scan.** A cheap vision call asks whether a person's name appears and where. Black out any such region in the normalised copy, and list the sheet for human review. Record only a yes or no and the region count in the report.
5. **Read.** Read every sheet with the product's own call 8 (blind to the expected answers, as in the product), with cost caps and caching by image hash. Store the draft reads with their confidence.
6. **Truth.** If `truth/*.csv` exists, use it as the verified answers. For every disagreement with the AI read, keep the truth, mark the sheet `verified`, and count the disagreement. Where there is no truth, the sheet stays `unverified`.
7. **Diagnose.** Run the existing error finder (`engine/diagnosis.py` and the bug functions) over the final answers, against the pilot Form A record. Do not reimplement any arithmetic.
8. **Write** `pilot_answers.json` (Step 3) and `ingest_report.md`: files in, duplicates dropped, sheets per class, roll numbers with no sheet, low-confidence reads, sheets flagged for a name, sheets unverified, and the counts below.
9. **Reading accuracy, counts only.** When truth exists, write `docs/evidence/pilot_reading_accuracy.md`: per class, how many answers the AI read correctly out of the total, how many sheets had at least one wrong read, and how confidence related to errors. No per-child rows. This file is tracked.

## Step 3. The answer file

Extend the Demo Studio answer-file schema with a `source: "pilot"` and these fields. Keep the same loader.

```
test: name, form (A), kind (pre), date, paper_version, competencies,
      questions: [ { no, text or prompt, type (dictation | add | subtract),
                     competency, skill, answer_format,
                     correct_answer, class_variants (dictation numbers by class),
                     options (null for written answers, a list if any),
                     error_probes (bug codes that apply),
                     expected_wrong (bug code -> the wrong answer it would give) } ]
classes: [ { class_code, teacher_label, strength, test_date,
             sheets: [ { roll, file, status (entered | absent | no_sheet),
                         source (truth | ai | truth+ai), verified (true | false),
                         image_hash,
                         answers: [ { q, given, correct (true | false | null),
                                      status (answered | blank | unreadable),
                                      confidence, flag (smudged | crossed_out | null),
                                      matched_bug (code or null) } ],
                         summary: { score, flagged_errors (two-item rule),
                                    single_item_probes } } ],
             class_summary: { counts per error code, children paired, absent } } ]
```

The class summary is counts only. Child-level fields exist only inside this ignored file.

## Step 4. The Enter the check option

1. **Data source** control at the top of Enter the check, shown in judge mode only: **Synthetic** (default) or **Pilot**. Pilot is disabled, with a one-line reason, unless Step 1's conditions hold. Selecting it shows the banner and a **Class** choice (3A or 3B). The check is created from the answer file's test: name, form A, pre-test, date, class code, strength.
2. **Roll list** as in the check prompt: "Roll no N - not entered" and so on, with a status per roll. Roll numbers with no sheet show **No sheet**, and become absent when she presses Finish entering.
3. **First roll number.** The teacher picks the sheet. Offer two ways: a gallery or dropdown of the folder's sheets for that class (thumbnails, "Roll no 3 - sheet available"), and the normal file picker. Selecting it sends the image to call 8. The data fills with the AI's answers, labelled **Read by AI**, with the image beside it.
4. **Auto-fill the rest.** A button loads the data for every other roll number from `pilot_answers.json`, with no AI call, labelled **Read from pilot answer file**. It also marks each as **Verified** or **Unverified** from the file. No fake progress bar.
5. **Review drawer** (as built for the demo): the bottom drawer shows the sheet image from the folder beside the read data, with Approve, Next unreviewed, Mark absent and **Re-read with AI** (a live call within the cost cap, relabelled Read by AI).
6. After Finish entering, the class card, diagnosis and before and after use only approved entries. Everything downstream is the real code.
7. **Optional step.** If the demo continues to cohort formation, the two pilot classes' counts join the simulated classes. Each class is labelled **Pilot** or **Simulated**. Only class-level counts leave the answer file.

## Step 5. The routes

All routes exist only when `PILOT_DEMO=1`, the folder and manifest are valid, and the request is authenticated as a judge or teacher in a demo session on this machine. Otherwise return 404.

- `GET /api/demo/pilot/manifest`: classes, strengths, test, and which rolls have sheets.
- `GET /api/demo/pilot/sheet/{class}/{roll}`: the normalised image, with `Cache-Control: no-store`.
- `POST /api/demo/pilot/read`: read the selected sheet with call 8.
- `POST /api/demo/pilot/autofill`: the answers for the other rolls from `pilot_answers.json`.

The service worker must never cache these routes. The build must never include `data/pilot/`.

## Step 6. Tests first

- **Guards:** `git ls-files data/pilot` is empty. The build output contains no pilot file or name. The routes return 404 without `PILOT_DEMO=1`, without the folder, without the consent note, and for the wrong role. The hosted configuration never shows the Pilot option.
- **Ingest on a fake folder** made from the synthetic sheets (never real data): rotation fix, duplicates dropped, class and roll from name and from header, renaming, name regions blacked out, truth overrides the AI read, disagreements counted, unverified sheets flagged, and the report counts add up.
- **Answer file:** validates against the schema, every answer has a question, `correct` matches the key, the matched bug code comes from the existing bug functions, and the class summary equals the engine's counts.
- **Enter the check:** the Pilot option appears only under the conditions. The first roll is read by AI and labelled. Auto-fill makes no AI call and labels the rest. No-sheet rolls become absent on Finish. The drawer shows the right image. The Synthetic path is unchanged.
- **Privacy:** the banner is on every screen that shows pilot data; no name appears; routes send no-store headers; the service worker has no pilot entries.
- Axe accessibility checks on the changed screens.

## Step 7. Docs and kit

- `docs/pilot/PILOT-DEMO.md`: how to put the sheets in, fill `manifest.yaml`, confirm consent, run `python tasks.py pilot-ingest`, review the report, and start with `PILOT_DEMO=1`.
- DECISIONS.md: an entry dated 2026-11-01 for the local-only pilot data source, the consent gate and the name scan.
- RUBRIC\_MAP.md: the user-testing row links to the pilot reading accuracy file.
- AI\_USAGE.md: note the optional header read and the name scan.
- Report: `docs/build/reports/PILOT-DEMO.md`.

**Order:** Steps 1 to 3 (look at a few normalised sheets and the report before going on), then 5, then 4, then 6 and 7.

**Done when** the tests pass, a machine with the folder offers Pilot, a machine without it never does, the first roll reads live, the others auto-fill from the answer file, the guards hold, and `docs/evidence/pilot_reading_accuracy.md` exists when truth is present.
