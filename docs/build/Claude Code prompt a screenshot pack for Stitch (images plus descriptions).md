# Claude Code prompt: a screenshot pack for Stitch (images plus descriptions)

Paste everything below the line into Claude Code at the repo root.

---

**Task.** Build a **Stitch pack**: for every screen and state of the app, capture screenshots (including long scrolling pages, tabs, drawers and dialogs) and write a description of every visible element, so Stitch can see what exists today and read what each part does. A `.md` extracted from code alone is not enough. Stitch needs the pictures and the words together.

**Rules.**

- **Demo data only.** Run against a judge-mode demo session with recorded AI answers. Never use pilot data, real keys or paid calls. Every capture of data must show the Demo label. Assert this in the harness.
- **Pictures must be true.** Capture what a user sees, with fonts loaded, animations finished and no development overlays.
- **The numbers must match.** Every number on an annotated image must match a row in that screen's element table.
- **Read-only for the product.** Do not change screens or behaviour. Add only the capture tooling and the pack.
- **Deterministic.** The same run gives the same pictures: fixed clock, seeded demo data, animations disabled, reduced motion on.

**Step 0. Read first.** Read CLAUDE.md, DECISIONS.md, PROGRESS.md, docs/design/stitch/DESIGN.md, docs/design/stitch/INVENTORY.md, the router and screen list in `apps/pwa/src`, the Playwright config and the existing end-to-end specs (they already log in as a judge, view as each role and use recorded AI answers). Reuse their login and demo helpers.

## Step 1. The manifest

Create `docs/design/stitch/pack/manifest.yaml`, generated from the router and INVENTORY.md and then completed by hand. One entry per **screen state**:

- `id`, `screen`, `route`, `role` (teacher, mentor, coach, officer, judge), `language` (en, plus hi for the main screens), `viewport` (phone 390 by 844 at 2x is primary; desktop 1280 by 800 is secondary), `theme` (dark too, if the app has it).
- `setup` steps to reach it: login, view-as role, demo data to load, clicks.
- `states`: every variant worth showing: each tab, each segmented choice, an opened dropdown, the review drawer open, a dialog or bottom sheet open, a menu open, empty, loading, error, offline, a long list, a filled form and a validation error.
- `scroll`: how to capture it (see Step 2).

Cover every route and every state named in INVENTORY.md and the end-to-end specs. Print a count of entries.

## Step 2. The capture harness (Playwright)

Add `tools/stitch_pack/capture.ts` (or the equivalent in the existing e2e folder) and a command `python tasks.py stitch-pack`.

1. **Stable pages.** Wait for fonts (`document.fonts.ready`), for network idle, and for any skeleton to disappear. Disable CSS animations and transitions, set `prefers-reduced-motion`, freeze the clock, hide dev overlays and toasts that are not part of the state.
2. **Long pages.** For every entry capture:
   - the **first viewport** exactly as a user sees it, with fixed headers and bottom bars in place;
   - the **full page**. If the page scrolls inside a container (an app shell with a fixed header or bottom bar), find the container (the element with `overflow-y` auto or scroll whose `scrollHeight` exceeds its `clientHeight`). Capture it as **scroll slices**: one screenshot per scroll position, with 80 px of overlap, named `...-s01.png`, `-s02.png` and so on;
   - a **stitched long image** built from the slices, with the fixed header and bottom bar kept only once. Split any image taller than 2,400 px into parts with a few pixels of overlap and label the parts. Keep every file under 4 MB.
3. **Horizontal scrolling** (wide tables, chips): capture the scrolled-to-end view too.
4. **Interaction states.** Click each tab and segmented control and capture each result. Open each dropdown, menu, drawer, dialog and bottom sheet and capture it. For each, also capture the page behind it (the drawer entries are clean and open variants).
5. **Roles and languages.** Repeat for every role the screen exists for, using the judge's view-as switch, and for Hindi on the main screens.
6. **Offline and error.** Use the browser context's offline mode for the offline state. Use recorded or mocked responses for error and empty states.
7. **Naming.** `NN-screen_state_role_lang_viewport.png`, with a two-digit order number, for example `07-enter-check_drawer-open_teacher_en_phone.png`.
8. **Safety checks.** Fail the entry if the image is blank (almost no pixel variation), if a page with data lacks the Demo label, or if any text matches an email, phone number or key pattern.

## Step 3. Describe every element (automatically)

For each captured state, extract with Playwright from the live page, and save as JSON beside the image:

- every visible element that is **interactive** (button, link, input, select, tab, switch, checkbox, menu item) or **meaningful** (heading, label, status, badge, number, image, icon with text), up to about 40 per image;
- for each: a number `E1`, `E2`, ..., its role, accessible name, visible text, `data-testid` if any, **bounding box** in pixels and as a percentage of the viewport, its **region** (header, side rail, bottom bar, main, drawer, dialog, footer), state (selected, disabled, expanded, checked), and a **style summary**: font size and weight, text colour, background, border, radius, and spacing around it, with the design token name when it matches one;
- the **region layout**: a top-to-bottom, left-to-right outline of regions with their approximate share of the screen.

## Step 4. Annotated images and contact sheets

1. For each clean image, write an **annotated copy** (`...-annotated.png`) with numbered boxes `E1`, `E2` drawn over the elements, in a colour that contrasts with the screen, with the numbers readable. Never draw on the clean image.
2. For each screen, write a **contact sheet** (`...-sheet.png`): its main states side by side in one image (up to four), each labelled, no wider than 3,000 px. This is for Stitch inputs that take only one image.

## Step 5. A spec file per screen

Write `docs/design/stitch/pack/<NN>-<screen>/spec.md` with this structure. Fill the tables from the JSON. Write the purpose and behaviour lines yourself, by reading the component source for the screen, in plain language:

1. **Screen**: name, route, roles, languages, when a user sees it, and what they are trying to do.
2. **Images**: a table of every file, what it shows, the viewport, the scroll position and the state.
3. **Layout**: the region outline from Step 3.
4. **Elements**: a table with the number, type, label or text, region, position and size, style summary, and **what it does** (and what happens when it is tapped).
5. **Content and data**: the real text on screen (copy it exactly), what data it shows and where that data comes from, and which parts are dynamic.
6. **States and transitions**: each tab, drawer, dialog, empty, loading, error and offline state, and how a user moves between them.
7. **What works and what to change**: from `docs/design/audit/AUDIT.md` if it exists, otherwise your own list of the visible problems against the visual rubric (hierarchy, spacing, type scale, consistency, density, states, touch targets, Hindi and Tamil fit).
8. **Constraints**: phone first, 44 px touch targets, English, Hindi and Tamil text must fit, the design tokens from DESIGN.md, no new features.

## Step 6. A ready-to-paste Stitch prompt per screen

Write `docs/design/stitch/pack/<NN>-<screen>/stitch-prompt.md`, no longer than about 1,800 characters, in this form:

> Redesign this screen of a teacher-support app for Indian primary school teachers. Attached: the clean screenshot, the annotated screenshot with numbered elements, and a contact sheet of its states. **Keep:** the content, the order of actions, and the purpose of every numbered element. **Improve:** hierarchy, spacing, type scale and consistency, using Material 3 with the Calm Institutional palette (teal primary). **Design these states:** (list them). **Elements to keep, by number:** (a short list of the numbered elements with their purpose). **Constraints:** phone first at 390 px, touch targets of at least 44 px, English, Hindi and Tamil text must fit without cutting, no new features.

Also write one `pack/00-tokens.md` that holds the colours, type scale, spacing and radii from DESIGN.md, to attach once.

## Step 7. Index and README

Write `pack/INDEX.md` listing every screen, its states and files, and `pack/README.md` explaining how to use the pack in Stitch: attach `00-tokens.md` once, then for each screen attach the clean image, the annotated image and the contact sheet, and paste `stitch-prompt.md`. Tell the reader to check Stitch's current limits on the number and size of images and the length of the prompt, and to use the contact sheet when only one image is allowed. Do not state Stitch's limits as facts.

## Step 8. Validate

Write `tools/stitch_pack/validate.py` and run it as part of `python tasks.py stitch-pack`. It checks that every manifest entry has its images, JSON, spec and prompt; that every number on an annotated image exists in the element table and the reverse; that no image is blank or over 4 MB; that every long page has slices and a stitched image; that Demo labels are present; that no prompt is longer than 1,800 characters; and that no file contains a secret or personal data. It prints a summary: screens, states, images, elements described, failures.

## Step 9. Look at it yourself

Open at least 10 of the images, covering a long page, a tab, a drawer, Hindi and the desktop view. For each, confirm that the picture is clear and the numbers on the annotated copy are readable and in the right place. Fix the harness when they are not. Record what you checked in the report.

## Step 10. Kit updates

Add a section to docs/design/stitch/INVENTORY.md linking the pack. Add a DECISIONS.md entry dated 2026-11-01: the Stitch pack, its demo-only rule and the annotation scheme. Add the pack folder to `.gitignore` for images over 4 MB only if needed, and keep the specs and prompts tracked. Write `docs/build/reports/STITCH-PACK.md` with the counts and the checks you made.

**Order:** Steps 1 and 2 (look at a few captures before going on), then 3 and 4, then 5 to 7, then 8 to 10.

**Done when** `python tasks.py stitch-pack` runs clean, every screen has clean, annotated and sheet images plus a spec and a prompt, long pages have slices and a stitched image, and the validator passes.
