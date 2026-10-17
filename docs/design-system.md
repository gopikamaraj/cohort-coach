# Design system (v1, P05)

Written before the screens. A compact token plan for a phone-first app used by primary teachers in sunlight, on cheap Android phones, in Tamil, Hindi and English.

## Where it comes from

A government primary classroom: a ruled exercise notebook, blue ink, a red margin line, a slate board and chalk, and bundles of ten sticks tied with string for place value. The app borrows the notebook for its structure and the sticks for its one memorable element. It uses no photos and no illustrations beyond SVG.

## Colour tokens

Five named colours plus two neutrals. Contrast ratios are computed against the paper colour (WCAG formula); body text aims for 7:1 and nothing is below 4.5:1.

| Token | Hex | Used for | Contrast |
| --- | --- | --- | --- |
| `paper` | `#FBFCFD` | Page and card background (a cool white, with faint blue rules) | n/a |
| `ink` | `#14201F` | Body text and headings | 16.3 on paper |
| `muted` | `#4A5856` | Secondary text | 7.2 on paper |
| `pen` | `#1B4F9C` | The one primary action per screen, links, focus ring | 7.7 on paper; white on pen 7.9 |
| `margin` | `#B3261E` | "This is wrong" flag, errors, the simulated-data banner edge | 6.4 on paper; white on margin 6.5 |
| `stick` | `#E8B93C` | The bundle-of-sticks marks, with `ink` text on top | ink on stick 9.1 |
| `slate` | `#1F3A33` | Judge-mode strip and the phone frame bezel; chalk text `#F2F5F0` on it | 11.2 |
| `rule` | `#9DB4D2` | Notebook rule lines and borders (decorative only, never text) | 2.1, so never carries meaning alone |

Colour never carries meaning alone: every state also has a word or an icon.

## Type

System fonts only, so nothing is downloaded and Android's Noto Devanagari and Noto Tamil are used: `system-ui, "Noto Sans Devanagari", "Noto Sans Tamil", sans-serif`. Sentence case everywhere; no all-caps labels.

| Role | Size and weight | Use |
| --- | --- | --- |
| Count numeral | 40 px, 700 | The "11" in "11 of 28 children" |
| Title | 24 px, 700 | Screen title |
| Card heading | 20 px, 700 | Error name on a card |
| Body | 18 px, 400, line height 1.5 | Everything else (Indic scripts need the room) |
| Small | 16 px, 400 | Notes; never below 16 |

## Spacing and shape

Scale in px: 4, 8, 12, 16, 24, 32. Tap targets are at least 48 × 48 px. Corners are square or 2 px, borders 1 px `rule`, no shadows. Cards are ruled-notebook rows: a 4 px `margin`-coloured left edge only where something needs attention, otherwise a plain 1 px border. Screens use one column at 360 px wide.

## The one memorable element: tally bundles

Counts are drawn as sticks: a row of short vertical strokes, grouped in tens and tied with a band, with the children who show the error filled in `stick` and the rest outlined. "11 of 28 children" is read in words and seen as 28 sticks, 11 of them filled. It is SVG, has a text alternative, and is the only decorative element in the app.

## Components

- **Primary button:** `pen` fill, white text, 48 px high, full width on phones; one per screen.
- **Secondary button:** 1 px `pen` border, `pen` text, same size.
- **Keypad:** a 3 × 4 grid of 56 px keys (digits, backspace, "blank", "can't read"), because Indian phones' system keyboards switch scripts in the middle of entry.
- **Banner:** the "Simulated data" strip, `margin` left edge, always visible when synthetic data shows, with the word "simulated" in the teacher's language.
- **Status line:** an icon plus a word for online, offline and "will send when connected".
- **Focus ring:** 3 px `pen` outline with a 2 px offset on every interactive element.

## Motion

None that carries meaning. Transitions are 120 ms opacity at most, and are removed under `prefers-reduced-motion`.

## Check against common generated-UI looks

| Look | What the first idea was | Change made |
| --- | --- | --- |
| Cream background with terracotta accents | A warm paper and a clay red | Cool white paper with blue rules and blue ink; red kept only for "wrong" and errors |
| Acid green on black | A chalkboard in neon chalk | Slate is used only for the judge strip and bezel, with soft chalk text, not for screens |
| Identical rounded cards with soft shadows | A stack of equal cards | Square ruled rows, no shadows; cards differ by what they hold (a count, an example) |
| All-caps eyebrow labels, monospace data labels | Small caps above each card, monospace counts | Sentence-case headings only; counts are large proportional numerals plus the stick drawing |
| A gradient hero | A banner on Home | None: Home is one status sentence and one action |

## Accessibility

Body contrast 16.3:1, secondary 7.2:1. Every control has a visible label; audio and icon-only controls have text names. The page language attribute follows the chosen language. Layout is checked at 360 px in the screenshots under `docs/evidence/screenshots/`.
