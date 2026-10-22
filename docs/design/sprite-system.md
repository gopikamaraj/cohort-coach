# Sprite system: items, mats, avatars and expressions as data, drawn by code

Status: built 22 Oct 2026 (see `docs/build/reports/SPRITES.md` for what is built and what is only specified). Rules: `CLAUDE.md` rule 17, `DECISIONS.md` 22 Oct.

## Principles

1. **SVG only, built by code.** No raster art, no image generation, no AI at runtime.
2. **Everything dynamic is data.** A new topic, item, student, expression or mat is a JSON file under `content/sprites/`, never renderer code.
3. **Counts are exact by construction.** If a scene shows 45 balls, code draws 45 `use` elements, and a test parses the SVG and counts them.
4. **AI drafts at authoring time only**, inside the grammar (call 11, `SPRITE_AUTHOR`), and a human approves before any teacher sees it.

## Where things live

| What | Where |
| --- | --- |
| Palettes (slots, approved sets, skin tones, hair and cloth colours) | `content/sprites/palettes.v1.json` |
| Item specs | `content/sprites/items/<id>.v1.json` |
| Avatar parts (bodies, hair, outfits, accessories) | `content/sprites/avatar_parts.v1.json` |
| Expressions and face parts | `content/sprites/expressions.v1.json` |
| Persona looks (seed and look per approved persona) | `content/sprites/personas.v1.json` |
| Topic packs | `content/sprites/packs/<id>.v1.json` |
| Renderer, Python (canonical; PNG for Telegram) | `services/api/sprites/` |
| Renderer, TypeScript (inline SVG on the phone) | `apps/pwa/src/sprites/` |
| Parity fixture (Python output, TypeScript must match) | `tests/fixtures/sprite_golden.json` |

The two renderers are one grammar written twice. Both use integer arithmetic and the same seeded generator (xorshift32), so the same inputs give byte-identical SVG; `apps/pwa/src/sprites/golden.test.ts` proves it on the fixture the Python engine writes.

## Grammar

**Allowed SVG elements** (in any rendered output): `svg`, `g`, `circle`, `ellipse`, `rect`, `line`, `polyline`, `polygon`, `path`, `defs`, `linearGradient`, `radialGradient`, `stop`, `clipPath`, `use`.

**Forbidden:** `script`, `foreignObject`, `image`, `text` (and `tspan`, `title`, `desc`), `style`, `a`, `animate`, `animateTransform`, `set`; any `on*` attribute; a `style` attribute; any `href` that does not start with `#`; any non-whitespace text node.

**Item and avatar specs** use only these shapes: `circle`, `ellipse`, `rect`, `line`, `polyline`, `polygon`, `path`, with integer numbers, fills and strokes that are a **palette slot name** (never a hex), `none`, or `grad:<id>` for a gradient the same spec defines. A spec that contains a hex colour, a non-integer, an unknown shape or an unknown attribute fails the grammar validator.

**Palette slots:** `skin`, `hair`, `cloth_a`, `cloth_b`, `accent`, `item_a`, `item_b`, `mat`, `ink`. A palette maps each slot to a hex colour; specs never see the hex.

**Fixed viewBox per category:** item `0 0 24 24`; avatar `0 0 64 72`; scene and mat `0 0 240 160`.

**Size budgets** (compiled markup of one spec): item 2 KB, avatar 12 KB, mat 6 KB. A drawn scene has no budget: it is many `use` elements of one small definition.

**Animation** is CSS classes on the page's stylesheet (opacity and transform only) and is switched off under `prefers-reduced-motion`. No animation element lives in an SVG.

**Meaning without colour.** Items differ by silhouette or pattern (stick, counter, ball with seam, marble with swirl, mango with leaf, pencil, book). A bundle is shown by a box around ten units, group B in an addition scene by a frame, a marked unit in a subtraction scene by a cross. Palettes are tested for contrast against the mat under protanopia, deuteranopia and tritanopia (Machado, Oliveira and Fernandes 2009 matrices, severity 1.0, applied in linear sRGB).

**No text in the art.** Alt text and labels are i18n keys (`sprite.*` in `strings/{en,hi,ta}.json`); the SVG carries `data-alt` with the key, and the page puts the translated text in `aria-label`.

## Layout engines (pure functions, exact)

Each takes an item spec, a count, a palette and a seed and returns the SVG and a report, for example `{"item_id": "ball", "count_drawn": 45}`.

| Layout | What it draws | Report |
| --- | --- | --- |
| `row` | n units in rows of at most 20 | `count_drawn` |
| `grid_array(r, c)` | r by c units | `count_drawn = r*c` |
| `ten_frame` | 0 to 20 counters in one or two ten-frames, row by row | `count_drawn` |
| `bundle_group` | n units as whole bundles of exactly 10, plus loose units | `bundles`, `loose`, `count_drawn = n` |
| `place_value_mat` | 0 to 99: tens column of bundles, ones column of units | `tens`, `ones`, `count_drawn = n` |
| `number_line(min, max, marks)` | ticks for every integer, longer at 5 and 10, circles at the marks | `ticks`, `marks`, `count_drawn = len(marks)` |
| `bar_model(parts)` | one bar split in proportion, alternate parts patterned | `parts`, `total` |
| `cross_out(n of N)` | N units, exactly n crossed | `count_drawn = N`, `marked = n` |
| `scatter(n, seed)` | n units in seeded, non-overlapping cells | `count_drawn` |
| `two_groups(a, b, seed)` | a units and b units apart, group B framed | `count_drawn = a+b`, `groups` |

## Avatars and expressions

An avatar is a composition: body, skin tone, hair style, hair colour, outfit (two cloth colours), accessory (none or bag; glasses and ribbon were removed on 22 Oct after the privacy review, because they can read as disability and gender markers). The look is derived from a seed (`look_from_seed`), and a persona record may override any field. The same seed gives the same SVG hash. Names come from the approved persona pool, never the roster; styles are named `hair_a` to `hair_f`, not by gender; no caste, religion or disability marker, no likeness of a real child.

Expressions are face-part sets in the registry: `neutral`, `thinking`, `confused`, `got_it`, `wrong_answer`, `shy`, `distracted`. Each has a closed and an open mouth frame; the avatar SVG holds both and the page's CSS toggles them while audio plays. **Code maps child state to an expression in one table** (`services/api/sprites/expression.py`); AI never chooses one. A new expression is one JSON entry that reuses existing face parts.

## Packs

A topic pack manifest holds: `id`, `subject`, `items`, `mats`, `layouts`, `expressions`, scenario `templates` (number slots filled by code, text by i18n key), `i18n_keys`, `version`, `status` (`draft`, `approved`, `enabled`). Shipped: `place-value-add-sub` (stick, bundle_of_ten, counter, ball, mango, pencil, marble, book, ten_frame; mats place_value_mat and number_line; add and subtract word-problem templates) and `fractions-demo` (a new item and the existing `bar_model`, JSON only, no renderer change: a test pins the renderer's hash).

**Two keys.** The coach approves a pack (gate 3); the programme officer enables it for the block. Neither alone enables. Every change is a new pack version, and an enabled pack that is edited stays in use until the new version is approved and enabled.

**No check items.** A template's text and every filled number pair go through the no-check-items validator (no Form A or B pair, either order).

## Authoring-time AI (call 11, `SPRITE_AUTHOR`)

Input: a plain description ("red cricket ball"). Output: an item spec in this grammar through a JSON schema that enumerates the shapes and slots, never free SVG. Offline only; never in a live turn. Gates, in order: schema, grammar whitelist, size budget, no text, palette slots only, no raw colour, a contact-sheet tile rendered, the pre-filter and call 7 for child-appropriateness (no weapons, alcohol or tobacco, religious or political symbols, brand marks), then coach approval, then officer enablement. A rejected spec returns the failing rule to the author and is never shown to a teacher.

## Channels

- **PWA:** inline SVG from the TypeScript renderer, cached with the shell.
- **Telegram and WhatsApp:** the server renders the scene to PNG (`resvg-py`, a Rust renderer in a wheel with no system libraries) and the flow engine sends it as an image; no browser rendering.
- **Practice Class:** the seat row and the materials tray use the same renderer; judge mode's "Show the machinery" shows the sprite spec JSON for the scene.

## Dashboard boundary

Configurable in the dashboard: enable or disable packs, items and expressions; persona looks and seating; palettes from the approved list; scenario templates. Code only: the grammar, the renderer, the layouts, the validators, the state-to-expression table, and anything that computes a count.
