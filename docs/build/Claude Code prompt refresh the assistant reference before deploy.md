# Claude Code prompt: refresh the assistant's reference before every deploy (questions right for each page and role)

Paste everything below the line into Claude Code at the repo root, **before each deployment**. It brings the assistant's reference documents and its suggested questions up to date with the app as it is now, then runs the pre-deploy gate until it is green. It makes no AI call and spends nothing.

---

**Task.** The assistant (the "Assistant" button in the title bar) offers five suggested questions. They must be **written for the page the person is on and for their role**, and each must have a real pre-written answer that rests on a document in this repository. Today a question can be missing for a page, a page can fall back to generic questions, and a help page can describe an old screen. Fix that, then prove it.

## Rules

- **No AI calls, no paid APIs, no network.** Everything here is code and text.
- **The documents are the source of the answers.** A question may only be added if a rubric row or a help page already answers it, or you write that answer into the help page first. Never invent a feature: say what the app does now, and mark planned things "planned, not built" (see `docs/RUBRIC_MAP.md` status words and `AI_USAGE.md`).
- **Answers follow the role's scope** (`assistant_scopes.yaml`). A teacher's questions use teacher documents only; do not put coach or judge material in the teacher bank.
- **No child names, phone numbers or roll numbers** in any question, answer or help page. The index build refuses them.
- **Never weaken a check** (`min_questions`, the abstention check) to get green. If a page truly needs fewer questions, say so in `docs/build/DECISIONS.md` and change the number there, with the reason.
- **Smallest change.** Add or edit only what the gate reports or what the app changed. Do not rewrite questions that are fine.

## Step 0. Read

`docs/design/stitch/INVENTORY.md`, `docs/RUBRIC_MAP.md`, `AI_USAGE.md`, `assistant_scopes.yaml`, `docs/assistant_questions/*.json` and `screens.yaml`, `docs/help/*.md`, `services/assistant/questions.py` (how the top five are chosen: a question for the current page scores 10, one for any page 3, one for a demo step 8), `services/assistant/curate.py` and `answer.py` (how the pre-written answers are made from rubric rows and help pages), and `apps/pwa/src/App.tsx` (the tabs of each role and the page name the panel sends).

## Step 1. Find what is out of date

Run:

```
python scripts/build_assistant_index.py
python scripts/check_assistant_questions.py --json
```

Read the output. **Problems** are structural (a route with no screen name, a question for a screen that does not exist, a suggested question whose pre-written answer abstains). **Gaps** are a role and page with fewer than `min_questions` (2) questions written for that page.

Then compare the app with the reference yourself, because the script cannot see a help page that is wrong:

1. **Routes and tabs.** Is every route in `apps/pwa/src/lib/router.ts` listed under at least one role in `docs/assistant_questions/screens.yaml`, and do the lists match the tabs in `App.tsx` for each role (teacher, mentor, coach, officer, judge, admin)? Fix the YAML if the app changed. Add a new page name to `VALID_SCREENS` in `services/assistant/questions.py`.
2. **Page names.** The panel sends the route name; the role picker (`#/roles`) sends `landing`. Confirm that `App.tsx` still does this.
3. **Help pages.** For each role, open its page in `docs/help/` and check each statement against the screens and strings it describes (`strings/en.json`, the screens in `apps/pwa/src/screens/`). Correct anything that is old: labels, button names, step counts, what is built. Add a short section for any page that has none, in plain language for that role.
4. **Status words.** Anything described as working must be Built in `docs/RUBRIC_MAP.md`; planned features are labelled planned.

Write what you found, in a few lines, at the top of your final message.

## Step 2. Write the missing questions

For every gap, add questions to the role's bank in `docs/assistant_questions/<role>.json` (keep the file's format: 1-space JSON indent, ids continuing the role's numbering):

- `text.en`: one short question a person on that page would ask, in plain words ("What does this screen show?", "Why is a button disabled?", "What happens when I tap Finish entering?"). One question per idea. No jargon, no names.
- `screens`: the page it is written for (use that page only; use `"any"` only for a question that fits every page).
- `criteria` and `rubric_rows`: for the judge bank, the judged criteria (`ai`, `efficacy`, `innovation`, `roadmap`) and at least one row of `docs/RUBRIC_MAP.md` that answers it. For other roles, rubric rows if one fits.
- `steps`: leave empty unless it belongs to a numbered demo step (1 to 12).
- `query`: the words that find the answer: the page's own terms and the help page heading, so the pre-written answer is built from the right section.

Aim for **2 to 4 questions per page per role**, covering: what this page is for, the one main action, the most common "why" (a disabled button, an empty list, a number), and what is not built. Keep the five shown per page the best five: put the page's most useful question first in the bank.

If a question's answer is not yet in a help page, write that section first (Step 1.3), then the question.

## Step 3. Rebuild and run the gate

```
python tasks.py predeploy
```

It rebuilds the index and the pre-written answers, runs `check_assistant_questions.py`, checks the README is current, and runs `tests/assistant`. Repeat Steps 1 to 3 until it prints `predeploy ok`. If `tests/assistant` fails because a new help page or question trips a rule (a personal-data pattern, a question without a criterion, a rubric row with no judge question), fix the content, not the test.

## Step 4. Look at it

Start the app (`python tasks.py dev`), open the Assistant on five pages in at least three roles (use **View as** from judge mode), including the role picker, and check each time that: the five questions are about *that page*, none repeats, each answer opens offline with a source, and nothing claims a planned feature works. Fix what is wrong and rerun Step 3.

## Step 5. Record

- Add a line to `docs/build/DECISIONS.md` (dated today) only if you changed `screens.yaml` rules, the minimum, or a role's scope.
- Final message: the output of `python tasks.py predeploy`; the number of questions added per role; the help pages you corrected; anything you could not answer from the documents (a question you left out and why).

**Done when** `python tasks.py predeploy` prints `predeploy ok`, the five questions on each page you opened in Step 4 are right for that page and role, and nothing was weakened to get there.
