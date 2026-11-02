# Stitch pack: how to use it

The pack shows Stitch what the app looks like today (pictures) and what each part does (words). It was captured from the built app in judge mode on simulated demo data, with recorded AI answers and a stub voice. Nothing real or private is in it.

## What is in each screen folder

- **Clean images** (`...png`): the first viewport as a user sees it, scroll slices (`-s01`, `-s02`, with 80 px overlap), a stitched long image of the whole page (`-long`, split into `-long-p1`, `-long-p2` when taller than 2,400 px) and, for wide tables, `-hscroll`.
- **Annotated images** (`-annotated`, `-long-annotated`): the same pictures with numbered boxes E1, E2 and so on. The numbers match the element tables in `spec.md`. The clean images are never drawn on.
- **Contact sheet** (`<screen>-sheet.png`): up to four states side by side in one image, for tools that take only one image.
- **`spec.md`**: the screen, its images, layout, every numbered element (type, text, position, style, what it does), the text on screen, the states, measured problems and constraints.
- **`stitch-prompt.md`**: a prompt of at most 1,800 characters, ready to paste.
- **`*.json`**: the raw element data for each capture.

## Using it in Stitch

1. Attach `00-tokens.md` once.
2. For each screen, attach the clean image, the annotated image and the contact sheet, then paste `stitch-prompt.md`.
3. Check Stitch's current limits on the number and size of images and on the length of the prompt before you start. Use the contact sheet when only one image is allowed, and the long image when you want the whole page.

## Rebuilding

`python tasks.py stitch-pack` rebuilds everything, then runs the validator. `--only home,check` rebuilds some screens.

## What the pack does not cover

Core scope only: no dark theme (the app has none), no Tamil, no empty, loading, error or offline states, no pilot mode. See the report `docs/build/reports/STITCH-PACK.md`.
