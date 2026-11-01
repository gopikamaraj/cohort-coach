# Design system (v2, 29 Oct 2026: Material 3)

A compact token plan for a phone-first app used by primary teachers in sunlight, on cheap Android phones, in Tamil, Hindi and English. v1 (20 Oct) was a blue-ink notebook look; v2 follows the Stitch design file, `docs/design/stitch/DESIGN.md` ("Calm Institutional Material", which is Material 3), on every screen. The decision is logged in `docs/build/DECISIONS.md` (2026-10-29).

## How to change the look (quick changes)

Everything lives in one file, `apps/pwa/src/theme.css`. `styles.css` and `pilot/pilot.css` hold layout and read the tokens; `tests/test_design_tokens.py` fails if a hex colour or an rgba() creeps back into `styles.css`, if a stylesheet uses a token that nothing defines, or if the manifest or icons drift from the primary colour.

| To change | Edit | Notes |
| --- | --- | --- |
| The main colour | `--pen` (and `--pen-container`, `--on-pen-container`, `--tonal`) in `theme.css`; then `theme_color` in `vite.config.ts`, `<meta name="theme-color">` in `index.html`, `scripts/make_icons.py` and `icon.svg` | The test names any of these that no longer match |
| Page, card and text colours | `--paper`, `--surface`, `--ink`, `--muted`, `--chalk` | Run `python tasks.py test`; it recomputes every contrast figure below |
| Roundness | `--r-card`, `--r-btn`, `--r-field`, `--r-chip`, `--r-pill`, `--r-sheet` | One value each; every component reads them |
| Hover, focus and press tint | `--state-hover`, `--state-press` | A fraction (0.08 is 8%) |
| Body text size, spacing | `--fs-base`, `--fs-wide`, `--s1` to `--s6` | Never below 16 px for any text (the test checks) |
| The whole look at once | Build with `VITE_THEME=classic` | The older blue-notebook palette and 2 px corners, for comparison; layout and components stay Material 3 |

Not a token: the layout of the bottom bar, cards and sheets (in `styles.css`), and the audio and icon behaviour. A change there is a code change with a test.

## Colour tokens

Contrast ratios are computed against the paper colour (WCAG formula, recomputed from `theme.css` by `tests/test_design_tokens.py`); body text aims for 7:1 and nothing is below 4.5:1. The nine names below are the original ones; the other roles are listed in `theme.css`, each with what it is for.

| Token | Hex | Used for | Contrast |
| --- | --- | --- | --- |
| `paper` | `#F7FAFA` | Page background | n/a |
| `ink` | `#191C1C` | Body text and headings | 16.3 on paper |
| `muted` | `#3F4948` | Secondary text | 8.9 on paper |
| `pen` | `#0B6B6B` | Primary: the one main action per screen, links, focus ring, selected states | 6.0 on paper; white on pen 6.3 |
| `margin` | `#B3261E` | Error: "this is wrong", failures | 6.2 on paper; white on margin 6.5 |
| `stick` | `#E8B93C` | The bundle-of-sticks marks and highlighted quotes, with `ink` text on top | ink on stick 9.3 |
| `slate` | `#0F3B3B` | The dark strip, the board line and toasts; chalk text `#EEF4F3` on it | 11.0 |
| `chalk` | `#EEF4F3` | Navigation bar, wells, light text on slate | n/a |
| `rule` | `#BEC9C8` | Card outlines and dividers (decorative only, never text) | 1.6, so never carries meaning alone |

Containers carry meaning with an icon and a word as well, never colour alone: primary container for the focus (the guided tour, the scenario), tonal (secondary container) for neutral chips and the selected navigation item, tertiary (`warn`) container for what to watch and for offline, success container for what went well, error container for what failed. Buttons and fields that must be seen use `outline` (`#6F7979`, 4.3 on paper, above the 3:1 needed for non-text).

## Type

System fonts only, so nothing is downloaded and Android's Noto Devanagari and Noto Tamil are used: `system-ui, "Noto Sans Devanagari", "Noto Sans Tamil", sans-serif`. Sentence case everywhere; no all-caps labels.

| Role | Size and weight | Use |
| --- | --- | --- |
| Count numeral | 40 px, 700 | The "11" in "11 of 28 children" |
| Headline | 28 px, 700 | Landing page title |
| Title | 24 px, 700 | Screen title |
| Card heading | 18 to 20 px, 700 | Error name on a card, role names |
| Body | 18 px, 400, line height 1.5 | Everything else (Indic scripts need the room) |
| Small | 16 px, 400 | Notes; never below 16 |

## Spacing and shape

Scale in px: 4, 8, 12, 16, 24, 32. Tap targets are at least 44 px, and primary buttons and fields 48 px or more. Corners follow Material 3: cards and tiles 16 px, buttons and fields 8 px, chips and notes 12 px, sheets 28 px, the signal pill a soft 16 px. No shadows except the one floating toast. Hover, focus and press show as a tint of the content colour over the control (a state layer), not a colour change. Screens use one column at 360 px wide.

## The one memorable element: tally bundles

Counts are drawn as sticks: a row of short vertical strokes, grouped in tens and tied with a band, with the children who show the error filled in `stick` and the rest outlined. "11 of 28 children" is read in words and seen as 28 sticks, 11 of them filled. It is SVG, has a text alternative, and is the only decorative element in the app.

## Components

- **Filled button:** `pen` fill, white text, 48 px high, 8 px corners, full width on phones; one per screen.
- **Outlined button:** 1 px `outline` border, `pen` text, same size. **Tonal button** (`m-btn-tonal`): `tonal` fill, used for the quieter choice beside a filled one.
- **Navigation bar:** four tabs and More on `chalk`; the selected tab shows a `tonal` pill behind its icon and its label in `ink`. More opens a bottom sheet with 28 px top corners.
- **Chips and notes:** `tonal` or a container colour, 12 px corners, an icon and a word.
- **Keypad:** a 3 × 4 grid of 56 px keys (digits, backspace, "blank", "can't read"), because Indian phones' system keyboards switch scripts in the middle of entry.
- **Banner:** the "Simulated data" strip on `tonal`, always visible when synthetic data shows, with the word "simulated" in the teacher's language.
- **Signal pill:** an icon plus a word for online, offline and "will send when connected". Offline uses the tertiary container with a cloud-off icon, and a note under the header says what still works.
- **Focus ring:** 3 px `pen` outline with a 2 px offset on every interactive element.

- **Answer map** (results page): a real table, one button per cell (44 px), roll column fixed while the table scrolls inside its own box. A mistake is colour **and** two letters **and** a pattern: PV-HEARD PH (sky, forward stripes), PV-REVERSE PR (purple, backward stripes), ADD-NOCARRY AC (orange, dots), SUB-SFL SF (green, horizontal stripes), SUB-NODEC SN (yellow, vertical stripes). A confirmed mistake has a solid edge, a "possible" one a dashed edge. The tokens `--heat-ph/pr/ac/sf/sn` are in `theme.css`; `tests/test_design_tokens.py` checks each against `ink` (at least 4.5:1) and that no two are closer than 15 CIE76 units under protan, deutan and tritan simulation.

## Motion

None that carries meaning. State layers fade in 150 ms (`--motion`), and are removed under `prefers-reduced-motion`.

## Check against common generated-UI looks

| Look | What the risk is | What we did |
| --- | --- | --- |
| Cream background with terracotta accents | A warm paper and a clay red | Cool white-teal paper; the warm colour is used only for "what to watch" and offline, never as the brand |
| Acid green on black | A chalkboard in neon chalk | Slate is used only for the top strip, the board line and toasts, with soft chalk text |
| Identical rounded cards with soft shadows | Material 3 makes every card the same rounded box | No shadows; cards differ by what they hold and carry meaning in their container colour (the tour is a filled primary container, the rest outlined); one filled card per screen |
| All-caps eyebrow labels, monospace data labels | Small caps above each card, monospace counts | Sentence-case headings only; counts are large proportional numerals plus the stick drawing |
| A gradient hero | A banner on Home | None: Home is one status sentence and one action |

## Accessibility

Body contrast 16.3:1, secondary 8.9:1. Every control has a visible label; audio and icon-only controls have text names. The page language attribute follows the chosen language. Layout is checked at 360 px in the screenshots under `docs/evidence/screenshots/`, and for sideways scrolling at 320, 360, 768 and 1280 px.

## Larger screens (2026-10-20)

The phone frame is for phones only. From 768 px the app is a centred column (up to 820 px, 1000 px from 1200 px) with the same components. `apps/pwa/e2e/programme.spec.ts` checks for sideways scrolling at 320, 360, 768 and 1280 px.
