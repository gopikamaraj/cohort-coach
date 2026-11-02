# Pilot sheets as a local demo data source

The pilot pre-test sheets of two classrooms can be used in the demo on **one machine**: the one that
holds the sheets. The hosted judge demo never has them. This page explains the folder, the script and
the switch. It holds no data.

## The rule that cannot be broken

Real children's data never goes into the repository. `data/pilot/` is git-ignored, and a test
(`tests/pilot_demo/test_api.py::test_no_pilot_file_is_tracked_by_git`) fails if any file under it is
tracked. The same holds for the answer file, the images and anything derived from them that has a
child's answers. Only counts may be committed (`docs/evidence/pilot_reading_accuracy.md`).

Sheets carry roll numbers only. No child name is collected or stored.

## The folder

```text
data/pilot/
  raw/                  the photos as received, untouched
  sheets/               normalised copies: {class}-roll{NN}.jpg   (made by the script)
  truth/                optional hand-keyed CSVs: 3A.csv, 3B.csv    (roll, q1 to q10)
  manifest.yaml         classes, strengths, teacher labels, the consent note
  pilot_answers.json    the answer file                            (made by the script)
  ingest_report.md      counts and review items                    (made by the script)
  .cache/               AI results cached by image hash            (made by the script)
```

The pilot form (Form A) has 10 boxes, so a truth CSV has `roll,q1,...,q10`. A box that is empty means
the child left it blank. Digits only.

## manifest.yaml

```yaml
consent:
  consent_confirmed: true            # without this the option stays disabled
  confirmed_by: Seema
  date: 2026-10-20
  scope: internal demo and the project video
test:
  name: Pilot pre-test
  form: A
  kind: pre
  date: 2026-10-23
classes:
  - class_code: 3A                   # letters and digits, up to 8
    strength: 30                     # roll numbers 1 to 30
    teacher_label: T1                # T1, T2: never a name
    test_date: 2026-10-23
    no_sheet: [4, 9]                 # roll numbers with no sheet
    absent: [12]                     # children absent on the test day
  - class_code: 3B
    strength: 28
    teacher_label: T2
    test_date: 2026-10-23
    dictation: {1: 453, 2: 618}      # only if this class was dictated different numbers
```

## Run the ingest

1. Put the photos in `data/pilot/raw/`. If a file name looks like `3A-roll07.jpg` (or `3A_roll_07`), the
   class and roll come from the name. Otherwise the script reads them from the printed header.
2. Optionally write the hand-keyed truth to `data/pilot/truth/3A.csv`.
3. Run `python tasks.py pilot-ingest`. Add `--no-ai` to use file names and truth only, and
   `--max-usd 3` to change the cost cap. It is idempotent: model results are cached by image hash.
4. Open `data/pilot/ingest_report.md`. **A person must review every sheet listed under "a name was
   found" or "name scan not run"**, plus the sheets with no class or roll, a guessed orientation, or
   a low-confidence box.

What the script does, in order: fix orientation and shrink to 1600 px; drop exact duplicates and keep
the sharper of any near-duplicates; name each sheet by class and roll; scan each sheet for a written
name and black the region out of the normalised copy (call 15, the only extra AI step); read each
sheet with call 8, blind to the expected answers; replace the read with the hand-keyed truth where
there is one and count every disagreement; run the engine's own error finder and 2-item rule; write
the answer file and the report. No arithmetic is written in the script.

A sheet is `verified` when it has hand-keyed truth, and `unverified` when it is the AI's read alone.

## Start the demo with Pilot

Set `PILOT_DEMO=1` in `.env` (and `PILOT_DEMO_DIR` if the folder is somewhere else) and start the
judge-mode app (`JUDGE_MODE=1`). In Demo Studio, on **Enter the check**, a **Data source** control
shows **Synthetic** and **Pilot**.

| Situation | What the judge sees |
| --- | --- |
| `PILOT_DEMO` is not 1, or there is no folder (the hosted demo) | Nothing. Synthetic only. |
| The folder is there but no manifest, no confirmed consent, or no answer file | Pilot, disabled, with one line saying why |
| All of it is in place | Pilot works |

With Pilot: choose the class, choose a sheet for the **first roll number** (gallery, list or the file
picker) and read it live (**Read by AI**); then **Auto-fill** loads every other roll number from the
answer file with no AI call (**Read from pilot answer file**, **Verified** or **Unverified**).
Roll numbers with no sheet show **No sheet** and become absent when entering is finished. The review
drawer shows the sheet from the folder beside what was read, with Approve, Next unreviewed, Mark
absent and **Re-read with AI**. Every screen that shows pilot data carries the banner **Pilot data:
real sheets, roll numbers only**.

## What stays on the machine

- The pictures and the answer file are served only by the four routes under `/api/demo/pilot/`, only
  to a judge deployment, a live demo session on this machine and `PILOT_DEMO=1`. Everything else is a
  404. Each answer carries `Cache-Control: no-store`; the service worker caches no `/api` route.
- The pictures are never in the web build. The browser keeps pilot answers in memory only: they are
  not written to local storage, and are gone when the page reloads.
- The one network step that sees a picture is call 8 for the sheet the teacher selects (the same call
  the product makes). The ingest script also sends each normalised sheet to call 15 and call 8; that is
  your choice to run, and `--no-ai` avoids it.

## Known limit

A class that was dictated different numbers (`dictation:` in the manifest) is built correctly in the
answer file, but the on-phone error finder knows only the printed Form A numbers (346 and 728), so
the screen shows that class disabled with the reason instead of diagnosing it wrongly. The pilot pack
prints the same dictation numbers for every class; if a class really used others, see
`docs/build/PARKING.md`.

## Two classes to a cohort (1 Nov)

`python -m tools.pilot.flow_run` works out each class's counts from the answer file in memory and walks the five flows (cohort, lesson 1, feedback and the next lesson, chat, the coach's view) on the real API in a throwaway database, with recorded AI answers and no paid call. It writes `data/pilot/evidence/flow-run.md` (git-ignored), and only its counts and pass or fail lines go into `docs/build/reports/FLOW-CHECK.md`.

**For the paper record:** the 15-item pre-test has one question each for borrowing across a zero (item 14), the three-digit sum with two carries (item 11) and the three-digit borrow-twice (item 15), and dictates 305 to one class only. The 2-item rule cannot be met on any of them, so the pilot counts them only under `COHORT_ALLOW_SINGLE_ITEM_PROBES`. **The post-test paper must add a second item for each of these skills**, and then the setting is no longer needed.
