# Claude Code prompt: Paper Studio (rule-based worksheet generator, rule database, rule editor and reviewer)

Paste everything below the line into Claude Code at the repo root. Put the pilot test guide and answer key (`Pilot_-_Test_Guide_and_answer_key.docx`) and the NIPUN Grade 3 documents in `docs/pilot/` and `docs/kb_seed/` first.

---

**Task.** Build **Paper Studio**: the part of the product that makes the termly check papers. It has a rule database, a generator, a rule editor, a paper reviewer, a PDF renderer and an answer key with a layout map. **No AI is used to generate a paper.** Code builds it from approved rules, and people approve the rules and the exceptions.

**Why.** The check is the start and end of every track. The papers must be correct, repeatable, tied to a check, safe to print, and comparable before and after.

**Rules.**

- **No AI in generation.** Numbers, keys, wrong-answer patterns and layout come from code. Fixed instruction strings are written and reviewed by people, never machine-translated.
- **Reproducible.** The same blueprint, rules version, class profile and seed always give the same paper and the same hash.
- **Rules are versioned and never edited in place.** A change makes a new version. A published version is immutable. Every paper pins the rules version it used.
- **Two people for rules.** The author of a rule change cannot approve it.
- **No child data and no names.** A class profile is class-level counts only. Papers have a roll number box and no name field. The child's paper does not say "Cohort Coach".
- Follow DESIGN.md. English, Hindi and Tamil text must fit.

**Step 0. Read first.** Read CLAUDE.md, DECISIONS.md, PROGRESS.md, docs/design/stitch/DESIGN.md, and the existing code for: the check record and the "Start a check" screen, error codes and the engine that finds errors, the sheet reading flow, the class card and before and after view, roles and permissions, the strategy library, migrations, and the eval harness. Read the pilot test guide and answer key, and the NIPUN Grade 3 documents. Reuse what exists.

## Step 1. The rule database

Add these tables, with versioning and an audit trail:

- `rule_template`: id, competency (C1, C2 or C3), skill, operation (dictate, add, subtract), digit pattern (for example "tens digit is zero, borrow needed"), number range, answer format, and constraints.
- `rule_bug`: error code, the bug function id and its parameters. A bug function computes the wrong answer a child who makes that mistake would write (for example taking the smaller digit from the larger, forgetting to reduce the tens, writing a zero).
- `blueprint` and `blueprint_slot`: the sections, the number of items, which slots are **anchor** and which are **adaptive**, and the coverage rule that each error code must be probed by at least two items in one paper.
- `string_pack`: instruction strings per language (English, Hindi, Tamil), plus a bilingual English and Hindi layout.
- `rule_version`: status (draft, in\_review, published, retired), author, approver, timestamps, and a diff against the previous version.
- `paper`: id, check id, form (A, B or C), seed, blueprint version, rules version, status (draft, auto\_approved, queued, approved, rejected, frozen), hash, approved\_by, approved\_at, frozen\_at.
- `paper_item`: paper, slot, template, operands, correct answer, expected wrong answers per error code, `is_anchor`, `twin_of`.
- `class_profile`: class, source (past, intake or baseline), skill weights, the list of skills marked **not assessed**, language, strength, and the check ids it was built from.
- `review_queue`.

**Seed the database** from the pilot: import the 15 items of Form A as an explicit paper from the test guide, and create two blueprints: `baseline_15` (reproduces the pilot's structure, all anchors) and `standard_10_5` (10 anchor items and 5 adaptive items). Seed the bug functions for every error code the engine already knows. Export all rules as YAML into `rules/` so judges can read them.

## Step 2. The generator

`generate_paper(check, class_profile, blueprint, rules_version, seed)`:

1. **Anchor slots** use fixed skills and difficulty, so papers across checks and classes measure the same thing. Only the numbers change. These are used for before and after.
2. **Adaptive slots** go deeper on the error codes the class profile weights most, and skip any skill marked not assessed. They are for diagnosis, not for measuring improvement.
3. **Pick numbers** by seeded sampling that satisfies the template's digit pattern and range. Use a seeded generator and never the global random state.
4. **Compute** the key, and the expected wrong answer for every bug function that applies to the item.
5. **Discrimination rule.** If two bug functions give the same wrong answer on an item, that item cannot tell them apart. Reject it unless the blueprint intends it.
6. **Coverage rule.** Every error code in the blueprint is probed by at least two items in one paper. If the constraints cannot be met, return a clear failure naming the rule, not a weaker paper.
7. **Uniqueness.** No duplicate item inside a paper. Form B uses a twin of every Form A item (same skill and difficulty, new numbers), records `twin_of`, and never repeats a number pair from Form A.
8. **Output** a paper record with a stable hash.

## Step 3. The class profile, and who generates when

**Profile sources, in order:**

1. **Past checks of this class.** Use class-level counts only, from the latest closed check, for example "9 of 18 went wrong borrowing across a zero". No child-level data goes to the server.
2. **No past data:** a short **intake form** for the teacher. What the class is good at, what it struggles with (a pick-list mapped to skills), which topics have been taught (a checklist), class strength, language, and whether the class has taken a similar test. A skill marked not taught becomes **not assessed**, so no child is flagged for something never taught.
3. **Neither:** the standard baseline.

**Who generates, and when:**

- **Pre-test:** the teacher (or the coordinator for her) from "Start a check", at the start of a track, using the profile above.
- **Post-test:** the system, together with the pre-test, as its frozen twin. It is built from the pre-test only and never adapted to the track. It is printed when the track ends.
- **Next termly check:** the teacher, from the Next step card about 7 days before it is due, from the last check's class counts.
- **Exceptions** (custom items or edited wording): the teacher or a reviewer, at any time, but they go to the review queue.

## Step 4. Approval

- A paper that passes every automatic check and uses only published rules with no custom edits is **auto-approved** and audit-logged. A configurable sample (default one in five) is added to the review queue after the fact for a spot check.
- A paper with custom items or any failed check goes to the **queue before it can be printed**.
- **Freeze:** when the first sheet is entered for a check, the paper is frozen, its hash is recorded, and it can no longer be changed.
- Only approved or auto-approved papers can be printed. Rejected papers keep the reviewer's reason.

## Step 5. Automatic checks (before anyone sees a paper)

Write an **independent verifier** in a separate module that shares no code with the generator, and recomputes every key from the operands. Also check: every error code probed at least twice; the discrimination rule; no duplicate items; wrong answers differ from correct ones; all strings present in every language; every glyph in the strings exists in the embedded fonts; nothing overflows the page; Form A and Form B twins match. Any failure blocks approval and names the item and the rule.

## Step 6. PDF, answer key and layout map

1. **PDF:** A4 portrait, print-safe in black and white. A large form letter and a printed **check code** in the header (for example `A · PRE · 3A · T3`, matching the check record). A roll number box and no name field. Large answer boxes. Embedded fonts: Noto Sans, Noto Sans Devanagari and Noto Sans Tamil. Languages: English, Hindi, Tamil, and an English and Hindi bilingual layout. Small corner marks on every page for alignment when a photo is taken. Render on the server. If the backend is Python, use WeasyPrint. Otherwise use the closest option that shapes Devanagari and Tamil correctly.
2. **Answer key PDF:** the correct answers and the common wrong answers for each error code, for hand marking.
3. **Layout map (JSON):** page, position and size in millimetres of every answer box, the roll box, the form letter and the check code area, plus the corner marks. The sheet reader uses it to crop each box, and to check that the printed code matches the open check.
4. **Look at the output.** Render every language's PDF to images and view them. Fix clipping, overlapping and glyph problems before moving on.

## Step 7. Screens

Follow DESIGN.md. Phone friendly, with text alternatives.

- **Papers:** the papers for a class by check, with status, form, language and a Print button.
- **Generate a paper** (inside Start a check): shows where the profile came from (past checks, intake or baseline), lets her change the language, shows a preview, the key and a coverage grid of error codes against items, and an "Anchor items" and "Adaptive items" label. A pre-test creates its post-test twin automatically.
- **Intake form:** the short teacher questions.
- **Review queue and paper view** (coach and reviewer): preview, key, coverage grid, automatic check results, Approve or Reject with a reason.
- **Rule editor** (coach and reviewer): a form over the database for templates, bug functions, blueprints and strings. Fields for operation, digit pattern, zero position, range and the error probes to apply, with side-by-side language strings. It shows five sample items with their keys and wrong answers, warns if the constraints cannot be met, and has a **Test this rule** button that runs the automatic checks. A change is saved as a draft, submitted for review, approved by a second person, then published. A diff shows what changed. Version history and retire. YAML export and import with schema validation.

## Step 8. Integration

- **Check record:** Start a check creates or attaches the paper. The paper carries the check's form and code. The reader warns when the printed code and the open check disagree.
- **Before and after:** compare on anchor twins only. Adaptive items appear separately and are never used to claim improvement.
- **Judge mode:** a guided tour step that generates a paper, shows the key and the coverage grid, and shows the rule editor with a published rule. Include demo classes and clearly labelled sample PDFs in `docs/samples/` with no child data.
- **Role-based assistant:** add Paper Studio help to the teacher, coach and judge help documents.
- **Events:** log generation and approval events (class, check, blueprint, versions, seed, hash). No child data.

## Step 9. Tests first

- **Determinism:** the same inputs give the same paper and hash. A different seed gives different numbers.
- **Anchors** keep the same skills and difficulty across papers. **Adaptive items** respond to the profile and respect not assessed.
- **Coverage and discrimination rules** hold, and a failure names the rule.
- **Form B** has a twin for every Form A item and repeats no number pair.
- **The independent verifier** catches a deliberately broken key.
- **Rules workflow:** an author cannot approve their own change. A published version cannot be edited. A paper pins its versions. A retired rule cannot be used.
- **Approval:** auto-approval happens only under the stated conditions, custom edits go to the queue, spot-check sampling works, and a frozen paper cannot change.
- **PDF:** all four layouts render, fonts are embedded, every glyph is covered, nothing overflows, and the layout map matches the rendered boxes (check by sampling pixels).
- **Permissions:** only coach and reviewer can use the rule editor and the queue.
- **Privacy:** no names, and the class profile holds counts only.
- Axe accessibility checks on every new screen.

## Step 10. Evidence and kit updates

- `docs/evidence/paper_studio_verification.md`: generate 200 papers per language across the blueprints and report how many passed every check. Counts only.
- RUBRIC\_MAP.md rows for Paper Studio, with status, code path, tests and demo steps.
- AI\_USAGE.md: state clearly that generation uses no AI.
- DECISIONS.md: an entry dated 2026-10-30. Anchor and adaptive items, the frozen post-test twin, auto-approval within the rules, two-person rule publishing, and the class profile order.
- README: how to generate, approve and print a paper, and how to export the rules.
- docs/design/stitch/INVENTORY.md updated. Report: `docs/build/reports/PAPER-STUDIO.md`.

**Order:** Steps 1 and 2 with the verifier from Step 5, then 6, then 3 and 4, then 7, then 8, then 9 and 10. Look at the PDFs before building the screens.

**Done when** the tests pass, a pre-test and its post-test twin generate and print in English, Hindi and Tamil, the independent verifier passes, a rule change goes through two people, and the evidence file exists.
