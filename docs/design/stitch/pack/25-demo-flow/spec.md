# 25 · Demo flow, steps 2 to 12

_Written for Stitch: what this screen is, what each part does, and what to keep. Tables are generated from the live page; the purpose and behaviour lines are written from the component source._

## 1. Screen

- **Route:** `#/demo`
- **Roles shown:** judge
- **Languages captured:** en
- **Inventory id:** X36, X37
- **When a user sees it:** A judge walks the demo from paper to post-test. Captured in one session, step by step.
- **What they are trying to do:** Make a paper, make 20 demo sheets, enter the check (one sheet read by AI, the rest auto-filled), review in the drawer, submit, simulate other classes and see the cohorts, hear lesson 1, practise, ask the cohort chat, act as the coach and the officer, and run the post-test.
- **Source:** apps/pwa/src/screens/DemoStudio.tsx, apps/pwa/src/components/DemoEntry.tsx
- **Data:** simulated demo data (judge mode, recorded AI answers). Every capture of data was checked for a Demo or Simulated label.

## 2. Images

| File | What it shows | Viewport | Scroll | State |
| --- | --- | --- | --- | --- |
| 01-demo-flow_s2-paper_judge_en_phone.png | First viewport, clean | 390 x 844 @2x | top | s2-paper · judge · en |
| 01-demo-flow_s2-paper_judge_en_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | s2-paper · judge · en |
| 01-demo-flow_s2-paper_judge_en_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | s2-paper · judge · en |
| 01-demo-flow_s2-paper_judge_en_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 377 px | s2-paper · judge · en |
| 01-demo-flow_s2-paper_judge_en_phone-s03.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 754 px | s2-paper · judge · en |
| 01-demo-flow_s2-paper_judge_en_phone-s04.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 1131 px | s2-paper · judge · en |
| 01-demo-flow_s2-paper_judge_en_phone-s05.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 1508 px | s2-paper · judge · en |
| 01-demo-flow_s2-paper_judge_en_phone-s06.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 1885 px | s2-paper · judge · en |
| 01-demo-flow_s2-paper_judge_en_phone-s07.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 2262 px | s2-paper · judge · en |
| 01-demo-flow_s2-paper_judge_en_phone-s08.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 2639 px | s2-paper · judge · en |
| 01-demo-flow_s2-paper_judge_en_phone-s09.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 3016 px | s2-paper · judge · en |
| 01-demo-flow_s2-paper_judge_en_phone-s10.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 3393 px | s2-paper · judge · en |
| 01-demo-flow_s2-paper_judge_en_phone-s11.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 3456 px | s2-paper · judge · en |
| 01-demo-flow_s2-paper_judge_en_phone-long-p1.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s2-paper · judge · en |
| 01-demo-flow_s2-paper_judge_en_phone-long-p2.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s2-paper · judge · en |
| 01-demo-flow_s2-paper_judge_en_phone-long-p3.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s2-paper · judge · en |
| 01-demo-flow_s2-paper_judge_en_phone-long-p4.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s2-paper · judge · en |
| 01-demo-flow_s2-paper_judge_en_phone-long-annotated-p1.png | Long image with numbered boxes | 390 x 844 @2x | full page | s2-paper · judge · en |
| 01-demo-flow_s2-paper_judge_en_phone-long-annotated-p2.png | Long image with numbered boxes | 390 x 844 @2x | full page | s2-paper · judge · en |
| 01-demo-flow_s2-paper_judge_en_phone-long-annotated-p3.png | Long image with numbered boxes | 390 x 844 @2x | full page | s2-paper · judge · en |
| 01-demo-flow_s2-paper_judge_en_phone-long-annotated-p4.png | Long image with numbered boxes | 390 x 844 @2x | full page | s2-paper · judge · en |
| 02-demo-flow_s3-sheets_judge_en_phone.png | First viewport, clean | 390 x 844 @2x | top | s3-sheets · judge · en |
| 02-demo-flow_s3-sheets_judge_en_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | s3-sheets · judge · en |
| 02-demo-flow_s3-sheets_judge_en_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | s3-sheets · judge · en |
| 02-demo-flow_s3-sheets_judge_en_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 422 px | s3-sheets · judge · en |
| 02-demo-flow_s3-sheets_judge_en_phone-s03.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 755 px | s3-sheets · judge · en |
| 02-demo-flow_s3-sheets_judge_en_phone-long-p1.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s3-sheets · judge · en |
| 02-demo-flow_s3-sheets_judge_en_phone-long-p2.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s3-sheets · judge · en |
| 02-demo-flow_s3-sheets_judge_en_phone-long-annotated-p1.png | Long image with numbered boxes | 390 x 844 @2x | full page | s3-sheets · judge · en |
| 02-demo-flow_s3-sheets_judge_en_phone-long-annotated-p2.png | Long image with numbered boxes | 390 x 844 @2x | full page | s3-sheets · judge · en |
| 03-demo-flow_s4-entry_judge_en_phone.png | First viewport, clean | 390 x 844 @2x | top | s4-entry · judge · en |
| 03-demo-flow_s4-entry_judge_en_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | s4-entry · judge · en |
| 03-demo-flow_s4-entry_judge_en_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | s4-entry · judge · en |
| 03-demo-flow_s4-entry_judge_en_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 422 px | s4-entry · judge · en |
| 03-demo-flow_s4-entry_judge_en_phone-s03.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 844 px | s4-entry · judge · en |
| 03-demo-flow_s4-entry_judge_en_phone-s04.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 1266 px | s4-entry · judge · en |
| 03-demo-flow_s4-entry_judge_en_phone-s05.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 1688 px | s4-entry · judge · en |
| 03-demo-flow_s4-entry_judge_en_phone-s06.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 2110 px | s4-entry · judge · en |
| 03-demo-flow_s4-entry_judge_en_phone-s07.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 2532 px | s4-entry · judge · en |
| 03-demo-flow_s4-entry_judge_en_phone-s08.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 2884 px | s4-entry · judge · en |
| 03-demo-flow_s4-entry_judge_en_phone-long-p1.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s4-entry · judge · en |
| 03-demo-flow_s4-entry_judge_en_phone-long-p2.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s4-entry · judge · en |
| 03-demo-flow_s4-entry_judge_en_phone-long-p3.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s4-entry · judge · en |
| 03-demo-flow_s4-entry_judge_en_phone-long-p4.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s4-entry · judge · en |
| 03-demo-flow_s4-entry_judge_en_phone-long-annotated-p1.png | Long image with numbered boxes | 390 x 844 @2x | full page | s4-entry · judge · en |
| 03-demo-flow_s4-entry_judge_en_phone-long-annotated-p2.png | Long image with numbered boxes | 390 x 844 @2x | full page | s4-entry · judge · en |
| 03-demo-flow_s4-entry_judge_en_phone-long-annotated-p3.png | Long image with numbered boxes | 390 x 844 @2x | full page | s4-entry · judge · en |
| 03-demo-flow_s4-entry_judge_en_phone-long-annotated-p4.png | Long image with numbered boxes | 390 x 844 @2x | full page | s4-entry · judge · en |
| 04-demo-flow_s5-drawer_judge_en_phone.png | First viewport, clean | 390 x 844 @2x | top | s5-drawer · judge · en |
| 04-demo-flow_s5-drawer_judge_en_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | s5-drawer · judge · en |
| 04-demo-flow_s5-drawer_judge_en_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | s5-drawer · judge · en |
| 04-demo-flow_s5-drawer_judge_en_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 422 px | s5-drawer · judge · en |
| 04-demo-flow_s5-drawer_judge_en_phone-s03.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 844 px | s5-drawer · judge · en |
| 04-demo-flow_s5-drawer_judge_en_phone-s04.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 1266 px | s5-drawer · judge · en |
| 04-demo-flow_s5-drawer_judge_en_phone-s05.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 1688 px | s5-drawer · judge · en |
| 04-demo-flow_s5-drawer_judge_en_phone-s06.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 2110 px | s5-drawer · judge · en |
| 04-demo-flow_s5-drawer_judge_en_phone-s07.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 2532 px | s5-drawer · judge · en |
| 04-demo-flow_s5-drawer_judge_en_phone-s08.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 2884 px | s5-drawer · judge · en |
| 04-demo-flow_s5-drawer_judge_en_phone-long-p1.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s5-drawer · judge · en |
| 04-demo-flow_s5-drawer_judge_en_phone-long-p2.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s5-drawer · judge · en |
| 04-demo-flow_s5-drawer_judge_en_phone-long-p3.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s5-drawer · judge · en |
| 04-demo-flow_s5-drawer_judge_en_phone-long-p4.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s5-drawer · judge · en |
| 04-demo-flow_s5-drawer_judge_en_phone-long-annotated-p1.png | Long image with numbered boxes | 390 x 844 @2x | full page | s5-drawer · judge · en |
| 04-demo-flow_s5-drawer_judge_en_phone-long-annotated-p2.png | Long image with numbered boxes | 390 x 844 @2x | full page | s5-drawer · judge · en |
| 04-demo-flow_s5-drawer_judge_en_phone-long-annotated-p3.png | Long image with numbered boxes | 390 x 844 @2x | full page | s5-drawer · judge · en |
| 04-demo-flow_s5-drawer_judge_en_phone-long-annotated-p4.png | Long image with numbered boxes | 390 x 844 @2x | full page | s5-drawer · judge · en |
| 04-demo-flow_s5-drawer_judge_en_phone-hscroll.png | A wide row or table scrolled to its end | 390 x 844 @2x | sideways | s5-drawer · judge · en |
| 05-demo-flow_s5-approved_judge_en_phone.png | First viewport, clean | 390 x 844 @2x | top | s5-approved · judge · en |
| 05-demo-flow_s5-approved_judge_en_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | s5-approved · judge · en |
| 05-demo-flow_s5-approved_judge_en_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | s5-approved · judge · en |
| 05-demo-flow_s5-approved_judge_en_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 422 px | s5-approved · judge · en |
| 05-demo-flow_s5-approved_judge_en_phone-s03.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 844 px | s5-approved · judge · en |
| 05-demo-flow_s5-approved_judge_en_phone-s04.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 1266 px | s5-approved · judge · en |
| 05-demo-flow_s5-approved_judge_en_phone-s05.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 1688 px | s5-approved · judge · en |
| 05-demo-flow_s5-approved_judge_en_phone-s06.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 2110 px | s5-approved · judge · en |
| 05-demo-flow_s5-approved_judge_en_phone-s07.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 2532 px | s5-approved · judge · en |
| 05-demo-flow_s5-approved_judge_en_phone-s08.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 2812 px | s5-approved · judge · en |
| 05-demo-flow_s5-approved_judge_en_phone-long-p1.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s5-approved · judge · en |
| 05-demo-flow_s5-approved_judge_en_phone-long-p2.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s5-approved · judge · en |
| 05-demo-flow_s5-approved_judge_en_phone-long-p3.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s5-approved · judge · en |
| 05-demo-flow_s5-approved_judge_en_phone-long-p4.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s5-approved · judge · en |
| 05-demo-flow_s5-approved_judge_en_phone-long-annotated-p1.png | Long image with numbered boxes | 390 x 844 @2x | full page | s5-approved · judge · en |
| 05-demo-flow_s5-approved_judge_en_phone-long-annotated-p2.png | Long image with numbered boxes | 390 x 844 @2x | full page | s5-approved · judge · en |
| 05-demo-flow_s5-approved_judge_en_phone-long-annotated-p3.png | Long image with numbered boxes | 390 x 844 @2x | full page | s5-approved · judge · en |
| 05-demo-flow_s5-approved_judge_en_phone-long-annotated-p4.png | Long image with numbered boxes | 390 x 844 @2x | full page | s5-approved · judge · en |
| 06-demo-flow_s6-counts_judge_en_phone.png | First viewport, clean | 390 x 844 @2x | top | s6-counts · judge · en |
| 06-demo-flow_s6-counts_judge_en_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | s6-counts · judge · en |
| 06-demo-flow_s6-counts_judge_en_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | s6-counts · judge · en |
| 06-demo-flow_s6-counts_judge_en_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 422 px | s6-counts · judge · en |
| 06-demo-flow_s6-counts_judge_en_phone-s03.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 457 px | s6-counts · judge · en |
| 06-demo-flow_s6-counts_judge_en_phone-long-p1.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s6-counts · judge · en |
| 06-demo-flow_s6-counts_judge_en_phone-long-p2.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s6-counts · judge · en |
| 06-demo-flow_s6-counts_judge_en_phone-long-annotated-p1.png | Long image with numbered boxes | 390 x 844 @2x | full page | s6-counts · judge · en |
| 06-demo-flow_s6-counts_judge_en_phone-long-annotated-p2.png | Long image with numbered boxes | 390 x 844 @2x | full page | s6-counts · judge · en |
| 07-demo-flow_s7-cohorts_judge_en_phone.png | First viewport, clean | 390 x 844 @2x | top | s7-cohorts · judge · en |
| 07-demo-flow_s7-cohorts_judge_en_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | s7-cohorts · judge · en |
| 07-demo-flow_s7-cohorts_judge_en_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | s7-cohorts · judge · en |
| 07-demo-flow_s7-cohorts_judge_en_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 422 px | s7-cohorts · judge · en |
| 07-demo-flow_s7-cohorts_judge_en_phone-s03.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 844 px | s7-cohorts · judge · en |
| 07-demo-flow_s7-cohorts_judge_en_phone-s04.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 1266 px | s7-cohorts · judge · en |
| 07-demo-flow_s7-cohorts_judge_en_phone-s05.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 1358 px | s7-cohorts · judge · en |
| 07-demo-flow_s7-cohorts_judge_en_phone-long-p1.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s7-cohorts · judge · en |
| 07-demo-flow_s7-cohorts_judge_en_phone-long-p2.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s7-cohorts · judge · en |
| 07-demo-flow_s7-cohorts_judge_en_phone-long-annotated-p1.png | Long image with numbered boxes | 390 x 844 @2x | full page | s7-cohorts · judge · en |
| 07-demo-flow_s7-cohorts_judge_en_phone-long-annotated-p2.png | Long image with numbered boxes | 390 x 844 @2x | full page | s7-cohorts · judge · en |
| 08-demo-flow_s8-lesson_judge_en_phone.png | First viewport, clean | 390 x 844 @2x | top | s8-lesson · judge · en |
| 08-demo-flow_s8-lesson_judge_en_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | s8-lesson · judge · en |
| 08-demo-flow_s8-lesson_judge_en_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | s8-lesson · judge · en |
| 08-demo-flow_s8-lesson_judge_en_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 422 px | s8-lesson · judge · en |
| 08-demo-flow_s8-lesson_judge_en_phone-s03.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 844 px | s8-lesson · judge · en |
| 08-demo-flow_s8-lesson_judge_en_phone-s04.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 1266 px | s8-lesson · judge · en |
| 08-demo-flow_s8-lesson_judge_en_phone-s05.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 1688 px | s8-lesson · judge · en |
| 08-demo-flow_s8-lesson_judge_en_phone-s06.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 2110 px | s8-lesson · judge · en |
| 08-demo-flow_s8-lesson_judge_en_phone-s07.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 2532 px | s8-lesson · judge · en |
| 08-demo-flow_s8-lesson_judge_en_phone-s08.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 2723 px | s8-lesson · judge · en |
| 08-demo-flow_s8-lesson_judge_en_phone-long-p1.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s8-lesson · judge · en |
| 08-demo-flow_s8-lesson_judge_en_phone-long-p2.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s8-lesson · judge · en |
| 08-demo-flow_s8-lesson_judge_en_phone-long-p3.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s8-lesson · judge · en |
| 08-demo-flow_s8-lesson_judge_en_phone-long-annotated-p1.png | Long image with numbered boxes | 390 x 844 @2x | full page | s8-lesson · judge · en |
| 08-demo-flow_s8-lesson_judge_en_phone-long-annotated-p2.png | Long image with numbered boxes | 390 x 844 @2x | full page | s8-lesson · judge · en |
| 08-demo-flow_s8-lesson_judge_en_phone-long-annotated-p3.png | Long image with numbered boxes | 390 x 844 @2x | full page | s8-lesson · judge · en |
| 09-demo-flow_s9-practice_judge_en_phone.png | First viewport, clean | 390 x 844 @2x | top | s9-practice · judge · en |
| 09-demo-flow_s9-practice_judge_en_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | s9-practice · judge · en |
| 09-demo-flow_s9-practice_judge_en_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | s9-practice · judge · en |
| 09-demo-flow_s9-practice_judge_en_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 247 px | s9-practice · judge · en |
| 09-demo-flow_s9-practice_judge_en_phone-long.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s9-practice · judge · en |
| 09-demo-flow_s9-practice_judge_en_phone-long-annotated.png | Long image with numbered boxes | 390 x 844 @2x | full page | s9-practice · judge · en |
| 10-demo-flow_s10-chat_judge_en_phone.png | First viewport, clean | 390 x 844 @2x | top | s10-chat · judge · en |
| 10-demo-flow_s10-chat_judge_en_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | s10-chat · judge · en |
| 10-demo-flow_s10-chat_judge_en_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | s10-chat · judge · en |
| 10-demo-flow_s10-chat_judge_en_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 422 px | s10-chat · judge · en |
| 10-demo-flow_s10-chat_judge_en_phone-s03.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 492 px | s10-chat · judge · en |
| 10-demo-flow_s10-chat_judge_en_phone-long-p1.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s10-chat · judge · en |
| 10-demo-flow_s10-chat_judge_en_phone-long-p2.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s10-chat · judge · en |
| 10-demo-flow_s10-chat_judge_en_phone-long-annotated-p1.png | Long image with numbered boxes | 390 x 844 @2x | full page | s10-chat · judge · en |
| 10-demo-flow_s10-chat_judge_en_phone-long-annotated-p2.png | Long image with numbered boxes | 390 x 844 @2x | full page | s10-chat · judge · en |
| 11-demo-flow_s11-coach_judge_en_phone.png | First viewport, clean | 390 x 844 @2x | top | s11-coach · judge · en |
| 11-demo-flow_s11-coach_judge_en_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | s11-coach · judge · en |
| 11-demo-flow_s11-coach_judge_en_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | s11-coach · judge · en |
| 11-demo-flow_s11-coach_judge_en_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 422 px | s11-coach · judge · en |
| 11-demo-flow_s11-coach_judge_en_phone-s03.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 844 px | s11-coach · judge · en |
| 11-demo-flow_s11-coach_judge_en_phone-s04.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 1266 px | s11-coach · judge · en |
| 11-demo-flow_s11-coach_judge_en_phone-s05.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 1688 px | s11-coach · judge · en |
| 11-demo-flow_s11-coach_judge_en_phone-s06.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 2110 px | s11-coach · judge · en |
| 11-demo-flow_s11-coach_judge_en_phone-s07.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 2532 px | s11-coach · judge · en |
| 11-demo-flow_s11-coach_judge_en_phone-s08.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 2954 px | s11-coach · judge · en |
| 11-demo-flow_s11-coach_judge_en_phone-s09.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 3035 px | s11-coach · judge · en |
| 11-demo-flow_s11-coach_judge_en_phone-long-p1.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s11-coach · judge · en |
| 11-demo-flow_s11-coach_judge_en_phone-long-p2.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s11-coach · judge · en |
| 11-demo-flow_s11-coach_judge_en_phone-long-p3.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s11-coach · judge · en |
| 11-demo-flow_s11-coach_judge_en_phone-long-p4.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s11-coach · judge · en |
| 11-demo-flow_s11-coach_judge_en_phone-long-annotated-p1.png | Long image with numbered boxes | 390 x 844 @2x | full page | s11-coach · judge · en |
| 11-demo-flow_s11-coach_judge_en_phone-long-annotated-p2.png | Long image with numbered boxes | 390 x 844 @2x | full page | s11-coach · judge · en |
| 11-demo-flow_s11-coach_judge_en_phone-long-annotated-p3.png | Long image with numbered boxes | 390 x 844 @2x | full page | s11-coach · judge · en |
| 11-demo-flow_s11-coach_judge_en_phone-long-annotated-p4.png | Long image with numbered boxes | 390 x 844 @2x | full page | s11-coach · judge · en |
| 12-demo-flow_s11-officer_judge_en_phone.png | First viewport, clean | 390 x 844 @2x | top | s11-officer · judge · en |
| 12-demo-flow_s11-officer_judge_en_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | s11-officer · judge · en |
| 12-demo-flow_s11-officer_judge_en_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | s11-officer · judge · en |
| 12-demo-flow_s11-officer_judge_en_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 446 px | s11-officer · judge · en |
| 12-demo-flow_s11-officer_judge_en_phone-s03.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 608 px | s11-officer · judge · en |
| 12-demo-flow_s11-officer_judge_en_phone-long-p1.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s11-officer · judge · en |
| 12-demo-flow_s11-officer_judge_en_phone-long-p2.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s11-officer · judge · en |
| 12-demo-flow_s11-officer_judge_en_phone-long-annotated-p1.png | Long image with numbered boxes | 390 x 844 @2x | full page | s11-officer · judge · en |
| 12-demo-flow_s11-officer_judge_en_phone-long-annotated-p2.png | Long image with numbered boxes | 390 x 844 @2x | full page | s11-officer · judge · en |
| 13-demo-flow_s12-post_judge_en_phone.png | First viewport, clean | 390 x 844 @2x | top | s12-post · judge · en |
| 13-demo-flow_s12-post_judge_en_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | s12-post · judge · en |
| 13-demo-flow_s12-post_judge_en_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | s12-post · judge · en |
| 13-demo-flow_s12-post_judge_en_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 422 px | s12-post · judge · en |
| 13-demo-flow_s12-post_judge_en_phone-s03.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 791 px | s12-post · judge · en |
| 13-demo-flow_s12-post_judge_en_phone-long-p1.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s12-post · judge · en |
| 13-demo-flow_s12-post_judge_en_phone-long-p2.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | s12-post · judge · en |
| 13-demo-flow_s12-post_judge_en_phone-long-annotated-p1.png | Long image with numbered boxes | 390 x 844 @2x | full page | s12-post · judge · en |
| 13-demo-flow_s12-post_judge_en_phone-long-annotated-p2.png | Long image with numbered boxes | 390 x 844 @2x | full page | s12-post · judge · en |
| demo-flow-sheet.png | Contact sheet of the main states | — | — | all |

## 3. Layout

Top to bottom in the first state ("s2-paper"), by region, with the numbered elements in each:

- **header**: E1 to E5 (5 elements)
- **demo bar**: E6 to E10 (5 elements)
- **main**: E11 to E54 (44 elements)
- **bottom bar**: E55 to E59 (5 elements)
- The page scrolls inside one container: 457 px visible of 3913 px (the header and bottom bar stay fixed).

## 4. Elements

Position is the box's top-left as a share of the viewport, then its size in CSS pixels. Style is the font size / weight, text colour, background, radius; a design token name in brackets means the value matches that token.

### State "s2-paper" · judge · en · phone

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | Cohort Coach | header | 4.1%, 0.9% · 168 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | image |  | header | 4.1%, 1.7% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E3 | button | Assistant | header | 4.1%, 6.6% · 125 x 44 | 18px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E4 | status | Online Good signal · 9.2 Mbps | header | 38.2%, 7.2% · 137 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E5 | element | Good signal · 9.2 Mbps | header | 48.2%, 7.8% · 85 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | element | Demo step 2 of 11 | demo bar | 3.1%, 13.4% · 135 x 21 | 15.75px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 220, 196) (--warn-container); radius 0px | Shows text or a value. |
| E7 | button | Back | demo bar | 3.1%, 24.7% · 71 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Goes to the previous demo step. |
| E8 | button | Next | demo bar | 22.2%, 24.7% · 71 x 44 | 18px / 400; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Goes to the next demo step, as the right role. |
| E9 | link | Judge guide for this step | demo bar | 3.1%, 30.4% · 231 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Opens the judge guide's question for this step. |
| E10 | button | Reset demo | demo bar | 63.2%, 30.4% · 128 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Resets the demo: clears this session's server rows and this phone's demo class. |
| E11 | heading | Start a check | main | 4.1%, 47.1% · 358 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E12 | element | Class 3A (demo) · Term 1 | main | 4.1%, 63.1% · 358 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E13 | radio | Pre-test · suggested | main | 4.1%, 72% · 192 x 44 | 18px / 400; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Choice: selects this option. |
| E14 | radio | Post-test | main | 55.4%, 72% · 104 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Choice: selects this option. |
| E15 | radio | Termly check | main | 4.1%, 78.1% · 136 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Choice: selects this option. |
| E16 | label | Date of the check | main | 4.1%, 86.2% · 166 x 79 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E17 | textbox | Date of the check | main | 4.1%, 45.2% · 166 x 48 | 18px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E18 | label | How many papers? (optional) | main | 4.1%, 53.2% · 233 x 79 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E19 | textbox | How many papers? (optional) | main | 4.1%, 56.9% · 233 x 48 | 18px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E20 | heading | Saved for this class | main | 4.1%, 65.9% · 358 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E21 | element | No check is saved yet for this class. | main | 4.1%, 69.8% · 358 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E22 | element | Print a paper for this check Which paper? The pilot paper (Form A): an | main | 4.1%, 74.1% · 358 x 2879 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 16px (--s4) | Opens the panel for printing a paper for this check. |
| E23 | button | Print a paper for this check | main | 8.5%, 75.6% · 324 x 44 | 18px / 600; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Button: tap to print a paper for this check. |
| E24 | label | The pilot paper (Form A): answers can be entered on this phone | main | 8.5%, 43.2% · 324 x 62 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E25 | radio | The pilot paper (Form A): answers can be entered on this phone [checked] | main | 9.7%, 88.5% · 24 x 24 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(247, 250, 250) (--paper); radius 50% | Choice: selects this option. |
| E26 | label | A new paper for this class: print it and mark it by hand with its answ | main | 8.5%, 51.9% · 324 x 89 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E27 | radio | A new paper for this class: print it and mark it by hand with its answ | main | 9.7%, 52.6% · 24 x 24 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(247, 250, 250) (--paper); radius 50% | Choice: selects this option. |
| E28 | label | Language of the paper English हिन्दी (Hindi) தமிழ் (Tamil) | main | 8.5%, 67.2% · 180 x 79 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E29 | combobox | Language of the paper English हिन्दी (Hindi) தமிழ் (Tamil) | main | 8.5%, 70.9% · 180 x 48 | 18px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Dropdown: she chooses one value. |
| E30 | label | Second language (optional) None हिन्दी (Hindi) தமிழ் (Tamil) | main | 8.5%, 78.9% · 219 x 79 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E31 | combobox | Second language (optional) None हिन्दी (Hindi) தமிழ் (Tamil) | main | 8.5%, 82.6% · 219 x 48 | 18px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Dropdown: she chooses one value. |
| E32 | button | Make the paper | main | 8.5%, 56.4% · 324 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Makes the paper by code from the approved rules. |
| E33 | element | Paper A · PRE · 3A · T1 | main | 8.5%, 63.5% · 324 x 2169 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 16px (--s4) | Shows text or a value. |
| E34 | heading | A · PRE · 3A · T1 | main | 12.8%, 65.1% · 290 x 32 | 21.06px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E35 | element | Approved by the rules | main | 12.8%, 70.2% · 178 x 31 | 15.3px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Shows text or a value. |
| E36 | element | The standard paper: no check of this class is saved yet · 10 questions | main | 12.8%, 76.8% · 290 x 96 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E37 | heading | Anchor items | main | 12.8%, 49.1% · 290 x 27 | 18px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E38 | heading | Which items check each error | main | 12.8%, 70.2% · 290 x 27 | 18px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E39 | region | Which items check each error | main | 12.8%, 78.6% · 290 x 967 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E40 | element | Error 1 2 3 4 5 6 7 8 9 10 Items PV-HEARD ● ● 2 PV-REVERSE ● ● 2 ADD-N | main | 12.8%, 78.6% · 290 x 967 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E41 | element | PV-HEARD ● ● 2 | main | 12.9%, 46% · 289 x 173 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E42 | element | PV-REVERSE ● ● 2 | main | 12.9%, 66.5% · 289 x 149 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E43 | element | ADD-NOCARRY ● ● ● 3 | main | 12.9%, 84.1% · 289 x 245 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E44 | element | SUB-SFL ● ● ● ● 4 | main | 12.9%, 68.5% · 289 x 125 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E45 | element | SUB-NODEC ● ● ● ● 4 | main | 12.9%, 83.3% · 289 x 173 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E46 | heading | Automatic checks | main | 12.8%, 64.4% · 290 x 27 | 18px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E47 | element | Every automatic check passed. | main | 12.8%, 71.9% · 290 x 27 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E48 | button | Print the paper | main | 12.8%, 79.3% · 91 x 126 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Button: tap to print the paper. |
| E49 | button | Print the answer key | main | 38.3%, 79.3% · 91 x 126 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to print the answer key. |
| E50 | button | Show the answers | main | 63.8%, 79.3% · 91 x 126 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to show the answers. |
| E51 | element | Paper A · PRE · 3A · T1 | main | 4.1%, 59.8% · 358 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E52 | button | Paper A · suggested | main | 4.1%, 67.7% · 358 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to paper a · suggested. |
| E53 | button | Paper B | main | 4.1%, 74.8% · 358 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to paper b. |
| E54 | button | Use sample sheets | main | 4.1%, 82.8% · 358 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Button: tap to use sample sheets. |
| E55 | link | Home | bottom bar | 0%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to Home. |
| E56 | link | Enter check [current] | bottom bar | 20%, 90.3% · 78 x 82 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the check entry. |
| E57 | link | My class | bottom bar | 40%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to What my class gets wrong. |
| E58 | link | Practice | bottom bar | 60%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the Practice Class. |
| E59 | button | More [collapsed] | bottom bar | 80%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens the menu of the other screens. |

### State "s3-sheets" · judge · en · phone

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | Cohort Coach | header | 4.1%, 0.9% · 168 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | image |  | header | 4.1%, 1.7% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E3 | button | Assistant | header | 4.1%, 6.6% · 125 x 44 | 18px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E4 | status | Online Good signal · 9.2 Mbps | header | 38.2%, 7.2% · 137 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E5 | element | Good signal · 9.2 Mbps | header | 48.2%, 7.8% · 85 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | element | Demo step 3 of 11 | demo bar | 3.1%, 13.4% · 135 x 21 | 15.75px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 220, 196) (--warn-container); radius 0px | Shows text or a value. |
| E7 | button | Back | demo bar | 3.1%, 19.3% · 71 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Goes to the previous demo step. |
| E8 | button | Next | demo bar | 22.2%, 19.3% · 71 x 44 | 18px / 400; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Goes to the next demo step, as the right role. |
| E9 | link | Judge guide for this step | demo bar | 3.1%, 25% · 231 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Opens the judge guide's question for this step. |
| E10 | button | Reset demo | demo bar | 63.2%, 25% · 128 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Resets the demo: clears this session's server rows and this phone's demo class. |
| E11 | heading | Demo flow | main | 4.1%, 34.6% · 358 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E12 | element | Demo: made-up class 3A, 20 simulated children, no real child | main | 4.1%, 41% · 358 x 54 | 15.3px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Shows text or a value. |
| E13 | heading | Step 3: make demo sheets | main | 4.1%, 54% · 358 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E14 | button | Generate 20 filled sheets for this paper | main | 4.1%, 78.1% · 358 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Makes 20 synthetic sheets for class 3A. |
| E15 | element | Demo sheets: synthetic, made by code. Not real children's work. | main | 4.1%, 85.3% · 358 x 54 | 15.3px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Shows text or a value. |
| E16 | button | Download all as ZIP | main | 4.1%, 45.9% · 175 x 99 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Downloads the sheets as one zip. |
| E17 | link | Download the demo answer file (reads.json) | main | 51%, 45.9% · 175 x 99 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Opens a link. |
| E18 | button | 3A-roll01.png | main | 4.1%, 60.5% · 143 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to 3a-roll01.png. |
| E19 | button | 3A-roll02.png | main | 41.7%, 60.5% · 143 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to 3a-roll02.png. |
| E20 | button | 3A-roll03.png | main | 4.1%, 66.2% · 143 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to 3a-roll03.png. |
| E21 | button | 3A-roll04.png | main | 41.7%, 66.2% · 143 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to 3a-roll04.png. |
| E22 | button | 3A-roll05.png | main | 4.1%, 71.8% · 143 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to 3a-roll05.png. |
| E23 | button | 3A-roll06.png | main | 41.7%, 71.8% · 143 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to 3a-roll06.png. |
| E24 | button | 3A-roll07.png | main | 4.1%, 77.5% · 143 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to 3a-roll07.png. |
| E25 | button | 3A-roll08.png | main | 41.7%, 77.5% · 143 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Button: tap to 3a-roll08.png. |
| E26 | button | 3A-roll09.png | main | 4.1%, 83.2% · 143 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to 3a-roll09.png. |
| E27 | button | 3A-roll10.png | main | 41.7%, 83.2% · 143 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to 3a-roll10.png. |
| E28 | button | 3A-roll11.png | main | 4.1%, 49.5% · 143 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to 3a-roll11.png. |
| E29 | button | 3A-roll12.png | main | 41.7%, 49.5% · 143 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to 3a-roll12.png. |
| E30 | button | 3A-roll13.png | main | 4.1%, 55.1% · 143 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to 3a-roll13.png. |
| E31 | button | 3A-roll14.png | main | 41.7%, 55.1% · 143 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to 3a-roll14.png. |
| E32 | button | 3A-roll15.png | main | 4.1%, 60.8% · 143 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to 3a-roll15.png. |
| E33 | button | 3A-roll16.png | main | 41.7%, 60.8% · 143 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to 3a-roll16.png. |
| E34 | button | 3A-roll17.png | main | 4.1%, 66.5% · 143 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to 3a-roll17.png. |
| E35 | button | 3A-roll18.png | main | 41.7%, 66.5% · 143 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to 3a-roll18.png. |
| E36 | button | 3A-roll19.png | main | 4.1%, 72.2% · 143 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to 3a-roll19.png. |
| E37 | button | 3A-roll20.png | main | 41.7%, 72.2% · 143 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to 3a-roll20.png. |
| E38 | link | Go to step 4 | main | 4.1%, 78.8% · 358 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Opens #/demo?step=4. |
| E39 | link | Home | bottom bar | 0%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to Home. |
| E40 | link | Enter check | bottom bar | 20%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the check entry. |
| E41 | link | My class | bottom bar | 40%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to What my class gets wrong. |
| E42 | link | Practice | bottom bar | 60%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the Practice Class. |
| E43 | button | More [collapsed] | bottom bar | 80%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens the menu of the other screens. |

### State "s4-entry" · judge · en · phone

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | Cohort Coach | header | 4.1%, 0.9% · 168 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | image |  | header | 4.1%, 1.7% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E3 | button | Assistant | header | 4.1%, 6.6% · 125 x 44 | 18px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E4 | status | Online Good signal · 9.2 Mbps | header | 38.2%, 7.2% · 137 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E5 | element | Good signal · 9.2 Mbps | header | 48.2%, 7.8% · 85 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | element | Demo step 4 of 11 | demo bar | 3.1%, 13.4% · 135 x 21 | 15.75px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 220, 196) (--warn-container); radius 0px | Shows text or a value. |
| E7 | button | Back | demo bar | 3.1%, 19.3% · 71 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Goes to the previous demo step. |
| E8 | button | Next | demo bar | 22.2%, 19.3% · 71 x 44 | 18px / 400; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Goes to the next demo step, as the right role. |
| E9 | link | Judge guide for this step | demo bar | 3.1%, 25% · 231 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Opens the judge guide's question for this step. |
| E10 | button | Reset demo | demo bar | 63.2%, 25% · 128 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Resets the demo: clears this session's server rows and this phone's demo class. |
| E11 | heading | Demo flow | main | 4.1%, 34.6% · 358 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E12 | element | Demo: made-up class 3A, 20 simulated children, no real child | main | 4.1%, 41% · 358 x 54 | 15.3px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Shows text or a value. |
| E13 | heading | Steps 4 and 5: enter the check and review it | main | 4.1%, 54% · 358 x 50 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E14 | element | Demo sheets: synthetic, made by code. Not real children's work. | main | 4.1%, 62.3% · 358 x 54 | 15.3px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Shows text or a value. |
| E15 | heading | Sheet 1: read by the AI | main | 8.5%, 75.5% · 324 x 32 | 21.06px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E16 | label | Upload sheet 1 | main | 8.5%, 48.8% · 158 x 72 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Label for the field next to it. |
| E17 | button | Use sheet 1 from step 3 | main | 51%, 48.8% · 158 x 72 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Sends sheet 1 to the AI reader. |
| E18 | heading | The other sheets: auto-fill | main | 8.5%, 67.7% · 324 x 32 | 21.06px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E19 | label | Upload the other sheets | main | 8.5%, 43.8% · 158 x 72 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Label for the field next to it. |
| E20 | button | Auto-fill the other sheets | main | 51%, 43.8% · 158 x 72 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Loads the other sheets from the demo answer file with no AI call. |
| E21 | status | 19 sheets loaded from the demo answer file, with no AI call. | main | 4.1%, 58.6% · 358 x 54 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Message shown to the user (read out by a screen reader). |
| E22 | heading | Roll numbers | main | 4.1%, 70.4% · 358 x 32 | 21.06px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E23 | element | 0 approved, 20 to review, of 20. | main | 4.1%, 78% · 358 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E24 | button | Open roll 1's sheet | main | 25.5%, 38.8% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 1's sheet. |
| E25 | button | Open roll 2's sheet | main | 56.9%, 50.2% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 2's sheet. |
| E26 | button | Open roll 3's sheet | main | 56.9%, 61.5% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 3's sheet. |
| E27 | button | Open roll 4's sheet | main | 56.9%, 72.9% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 4's sheet. |
| E28 | button | Open roll 5's sheet | main | 56.9%, 84.3% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 5's sheet. |
| E29 | button | Open roll 6's sheet | main | 56.9%, 45.6% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 6's sheet. |
| E30 | button | Open roll 7's sheet | main | 56.9%, 57% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Button: tap to open roll 7's sheet. |
| E31 | button | Open roll 8's sheet | main | 56.9%, 68.4% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 8's sheet. |
| E32 | button | Open roll 9's sheet | main | 56.9%, 79.7% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 9's sheet. |
| E33 | button | Open roll 10's sheet | main | 56.9%, 41.1% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 10's sheet. |
| E34 | button | Open roll 11's sheet | main | 56.9%, 52.5% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 11's sheet. |
| E35 | button | Open roll 12's sheet | main | 56.9%, 63.8% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 12's sheet. |
| E36 | button | Open roll 13's sheet | main | 56.9%, 75.2% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 13's sheet. |
| E37 | button | Open roll 14's sheet | main | 56.9%, 86.6% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 14's sheet. |
| E38 | button | Open roll 15's sheet | main | 56.9%, 47.9% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 15's sheet. |
| E39 | button | Open roll 16's sheet | main | 56.9%, 59.3% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Button: tap to open roll 16's sheet. |
| E40 | button | Open roll 17's sheet | main | 56.9%, 70.7% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 17's sheet. |
| E41 | button | Open roll 18's sheet | main | 56.9%, 82% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 18's sheet. |
| E42 | button | Open roll 19's sheet | main | 56.9%, 51.7% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 19's sheet. |
| E43 | button | Open roll 20's sheet | main | 56.9%, 63.1% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 20's sheet. |
| E44 | button | Finish entering [disabled] | main | 4.1%, 70.3% · 358 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Submits the check. |
| E45 | link | Home | bottom bar | 0%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to Home. |
| E46 | link | Enter check | bottom bar | 20%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the check entry. |
| E47 | link | My class | bottom bar | 40%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to What my class gets wrong. |
| E48 | link | Practice | bottom bar | 60%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the Practice Class. |
| E49 | button | More [collapsed] | bottom bar | 80%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens the menu of the other screens. |

### State "s5-drawer" · judge · en · phone

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | Cohort Coach | header | 4.1%, 0.9% · 168 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | image |  | header | 4.1%, 1.7% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E3 | button | Assistant | header | 4.1%, 6.6% · 125 x 44 | 18px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E4 | status | Online Good signal · 9.2 Mbps | header | 38.2%, 7.2% · 137 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E5 | element | Good signal · 9.2 Mbps | header | 48.2%, 7.8% · 85 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | element | Demo step 5 of 11 | demo bar | 3.1%, 13.4% · 135 x 21 | 15.75px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 220, 196) (--warn-container); radius 0px | Shows text or a value. |
| E7 | button | Back | demo bar | 3.1%, 19.3% · 71 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Goes to the previous demo step. |
| E8 | button | Next | demo bar | 22.2%, 19.3% · 71 x 44 | 18px / 400; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Goes to the next demo step, as the right role. |
| E9 | link | Judge guide for this step | demo bar | 3.1%, 25% · 231 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Opens the judge guide's question for this step. |
| E10 | button | Reset demo | demo bar | 63.2%, 25% · 128 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Resets the demo: clears this session's server rows and this phone's demo class. |
| E11 | heading | Demo flow | main | 4.1%, 34.6% · 358 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E12 | element | Demo: made-up class 3A, 20 simulated children, no real child | main | 4.1%, 41% · 358 x 54 | 15.3px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Shows text or a value. |
| E13 | heading | Steps 4 and 5: enter the check and review it | main | 4.1%, 54% · 358 x 50 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E14 | dialog | Roll 6 Read from demo answer file Close Zoom in Zoom out Rotate Box 1  | dialog | 0%, 60% · 390 x 338 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Shows text or a value. |
| E15 | heading | Roll 6 | dialog | 3.1%, 61.2% · 54 x 63 | 21.06px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E16 | button | Close | dialog | 77.2%, 62.3% · 77 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to close. |
| E17 | element | Read from demo answer file | dialog | 18.9%, 63.1% · 219 x 31 | 15.3px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Shows text or a value. |
| E18 | region | The sheet | dialog | 3.1%, 68.7% · 366 x 487 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Shows text or a value. |
| E19 | image | Demo sheet for roll 6 | dialog | 3.3%, 68.8% · 364 x 485 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Picture. |
| E20 | label | Upload sheet 1 | main | 8.5%, 48.8% · 158 x 72 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Label for the field next to it. |
| E21 | button | Use sheet 1 from step 3 | main | 51%, 48.8% · 158 x 72 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Sends sheet 1 to the AI reader. |
| E22 | label | Upload the other sheets | main | 8.5%, 43.8% · 158 x 72 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Label for the field next to it. |
| E23 | button | Auto-fill the other sheets | main | 51%, 43.8% · 158 x 72 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Loads the other sheets from the demo answer file with no AI call. |
| E24 | button | Open roll 1's sheet | main | 25.5%, 38.8% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 1's sheet. |
| E25 | button | Open roll 2's sheet | main | 56.9%, 50.2% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 2's sheet. |
| E26 | button | Open roll 5's sheet | main | 56.9%, 34.3% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 5's sheet. |
| E27 | button | Open roll 6's sheet | main | 56.9%, 45.6% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 6's sheet. |
| E28 | button | Open roll 7's sheet | main | 56.9%, 57% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 7's sheet. |
| E29 | button | Open roll 9's sheet | main | 56.9%, 29.7% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 9's sheet. |
| E30 | button | Open roll 10's sheet | main | 56.9%, 41.1% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 10's sheet. |
| E31 | button | Open roll 11's sheet | main | 56.9%, 52.5% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 11's sheet. |
| E32 | button | Open roll 14's sheet | main | 56.9%, 36.6% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 14's sheet. |
| E33 | button | Open roll 15's sheet | main | 56.9%, 47.9% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 15's sheet. |
| E34 | button | Open roll 17's sheet | main | 56.9%, 29% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 17's sheet. |
| E35 | button | Open roll 18's sheet | main | 56.9%, 40.3% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 18's sheet. |
| E36 | button | Open roll 19's sheet | main | 56.9%, 51.7% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 19's sheet. |

### State "s5-approved" · judge · en · phone

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | Cohort Coach | header | 4.1%, 0.9% · 168 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | image |  | header | 4.1%, 1.7% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E3 | button | Assistant | header | 4.1%, 6.6% · 125 x 44 | 18px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E4 | status | Online Good signal · 9.2 Mbps | header | 38.2%, 7.2% · 137 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E5 | element | Good signal · 9.2 Mbps | header | 48.2%, 7.8% · 85 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | element | Demo step 5 of 11 | demo bar | 3.1%, 13.4% · 135 x 21 | 15.75px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 220, 196) (--warn-container); radius 0px | Shows text or a value. |
| E7 | button | Back | demo bar | 3.1%, 19.3% · 71 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Goes to the previous demo step. |
| E8 | button | Next | demo bar | 22.2%, 19.3% · 71 x 44 | 18px / 400; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Goes to the next demo step, as the right role. |
| E9 | link | Judge guide for this step | demo bar | 3.1%, 25% · 231 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Opens the judge guide's question for this step. |
| E10 | button | Reset demo | demo bar | 63.2%, 25% · 128 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Resets the demo: clears this session's server rows and this phone's demo class. |
| E11 | heading | Demo flow | main | 4.1%, 34.6% · 358 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E12 | element | Demo: made-up class 3A, 20 simulated children, no real child | main | 4.1%, 41% · 358 x 54 | 15.3px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Shows text or a value. |
| E13 | heading | Steps 4 and 5: enter the check and review it | main | 4.1%, 54% · 358 x 50 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E14 | element | Demo sheets: synthetic, made by code. Not real children's work. | main | 4.1%, 62.3% · 358 x 54 | 15.3px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Shows text or a value. |
| E15 | heading | Sheet 1: read by the AI | main | 8.5%, 75.5% · 324 x 32 | 21.06px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E16 | label | Upload sheet 1 | main | 8.5%, 48.8% · 158 x 72 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Label for the field next to it. |
| E17 | button | Use sheet 1 from step 3 | main | 51%, 48.8% · 158 x 72 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Sends sheet 1 to the AI reader. |
| E18 | heading | The other sheets: auto-fill | main | 8.5%, 67.7% · 324 x 32 | 21.06px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E19 | label | Upload the other sheets | main | 8.5%, 43.8% · 158 x 72 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Label for the field next to it. |
| E20 | button | Auto-fill the other sheets | main | 51%, 43.8% · 158 x 72 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Loads the other sheets from the demo answer file with no AI call. |
| E21 | status | 19 sheets loaded from the demo answer file, with no AI call. | main | 4.1%, 58.6% · 358 x 54 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Message shown to the user (read out by a screen reader). |
| E22 | heading | Roll numbers | main | 4.1%, 70.4% · 358 x 32 | 21.06px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E23 | element | 20 approved, 0 to review, of 20. | main | 4.1%, 78% · 358 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E24 | button | Open roll 1's sheet | main | 4.1%, 38.8% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 1's sheet. |
| E25 | button | Open roll 2's sheet | main | 56.9%, 50.2% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 2's sheet. |
| E26 | button | Open roll 3's sheet | main | 56.9%, 61.5% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 3's sheet. |
| E27 | button | Open roll 4's sheet | main | 56.9%, 72.9% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 4's sheet. |
| E28 | button | Open roll 5's sheet | main | 56.9%, 84.3% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 5's sheet. |
| E29 | button | Open roll 6's sheet | main | 56.9%, 45.6% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 6's sheet. |
| E30 | button | Open roll 7's sheet | main | 56.9%, 57% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 7's sheet. |
| E31 | button | Open roll 8's sheet | main | 56.9%, 68.4% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 8's sheet. |
| E32 | button | Open roll 9's sheet | main | 56.9%, 79.7% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 9's sheet. |
| E33 | button | Open roll 10's sheet | main | 56.9%, 41.1% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 10's sheet. |
| E34 | button | Open roll 11's sheet | main | 56.9%, 52.5% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 11's sheet. |
| E35 | button | Open roll 12's sheet | main | 56.9%, 63.8% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 12's sheet. |
| E36 | button | Open roll 13's sheet | main | 56.9%, 75.2% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 13's sheet. |
| E37 | button | Open roll 14's sheet | main | 56.9%, 86.6% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 14's sheet. |
| E38 | button | Open roll 15's sheet | main | 56.9%, 47.9% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 15's sheet. |
| E39 | button | Open roll 16's sheet | main | 56.9%, 59.3% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 16's sheet. |
| E40 | button | Open roll 17's sheet | main | 56.9%, 70.7% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 17's sheet. |
| E41 | button | Open roll 18's sheet | main | 56.9%, 82% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 18's sheet. |
| E42 | button | Open roll 19's sheet | main | 56.9%, 60.2% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 19's sheet. |
| E43 | button | Open roll 20's sheet | main | 56.9%, 71.6% · 78 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to open roll 20's sheet. |
| E44 | button | Finish entering | main | 4.1%, 78.8% · 358 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Submits the check. |
| E45 | link | Home | bottom bar | 0%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to Home. |
| E46 | link | Enter check | bottom bar | 20%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the check entry. |
| E47 | link | My class | bottom bar | 40%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to What my class gets wrong. |
| E48 | link | Practice | bottom bar | 60%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the Practice Class. |
| E49 | button | More [collapsed] | bottom bar | 80%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens the menu of the other screens. |

### State "s6-counts" · judge · en · phone

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | Cohort Coach | header | 4.1%, 0.9% · 168 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | image |  | header | 4.1%, 1.7% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E3 | button | Assistant | header | 4.1%, 6.6% · 125 x 44 | 18px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E4 | status | 1 result waiting to send Good signal · 9.2 Mbps | header | 38.2%, 7.2% · 137 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E5 | element | Good signal · 9.2 Mbps | header | 48.2%, 7.8% · 85 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | element | Demo step 6 of 11 | demo bar | 3.1%, 13.4% · 135 x 21 | 15.75px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 220, 196) (--warn-container); radius 0px | Shows text or a value. |
| E7 | button | Back | demo bar | 3.1%, 19.3% · 71 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Goes to the previous demo step. |
| E8 | button | Next | demo bar | 22.2%, 19.3% · 71 x 44 | 18px / 400; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Goes to the next demo step, as the right role. |
| E9 | link | Judge guide for this step | demo bar | 3.1%, 25% · 231 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Opens the judge guide's question for this step. |
| E10 | button | Reset demo | demo bar | 63.2%, 25% · 128 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Resets the demo: clears this session's server rows and this phone's demo class. |
| E11 | heading | Demo flow | main | 4.1%, 34.6% · 358 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E12 | element | Demo: made-up class 3A, 20 simulated children, no real child | main | 4.1%, 41% · 358 x 54 | 15.3px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Shows text or a value. |
| E13 | heading | Step 6: submit the check | main | 4.1%, 54% · 358 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E14 | element | Your class, 20 children checked (simulated): PV-HEARD 2 of 20 · ADD-NO | main | 4.1%, 69.7% · 358 x 81 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E15 | link | See your class's error cards | main | 4.1%, 82.2% · 358 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Opens #/cards. |
| E16 | heading | Demo reading summary | main | 8.5%, 43.3% · 324 x 32 | 21.06px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E17 | button | Simulate other classes' results | main | 4.1%, 83% · 358 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Simulates the other 24 classes and forms cohorts with the real rules. |
| E18 | link | Home | bottom bar | 0%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to Home. |
| E19 | link | Enter check | bottom bar | 20%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the check entry. |
| E20 | link | My class | bottom bar | 40%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to What my class gets wrong. |
| E21 | link | Practice | bottom bar | 60%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the Practice Class. |
| E22 | button | More [collapsed] | bottom bar | 80%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens the menu of the other screens. |

### State "s7-cohorts" · judge · en · phone

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | Cohort Coach | header | 4.1%, 0.9% · 168 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | image |  | header | 4.1%, 1.7% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E3 | button | Assistant | header | 4.1%, 6.6% · 125 x 44 | 18px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E4 | status | 1 result waiting to send Good signal · 9.2 Mbps | header | 38.2%, 7.2% · 137 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E5 | element | Good signal · 9.2 Mbps | header | 48.2%, 7.8% · 85 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | element | Demo step 7 of 11 | demo bar | 3.1%, 13.4% · 135 x 21 | 15.75px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 220, 196) (--warn-container); radius 0px | Shows text or a value. |
| E7 | button | Back | demo bar | 3.1%, 19.3% · 71 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Goes to the previous demo step. |
| E8 | button | Next | demo bar | 22.2%, 19.3% · 71 x 44 | 18px / 400; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Goes to the next demo step, as the right role. |
| E9 | link | Judge guide for this step | demo bar | 3.1%, 25% · 231 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Opens the judge guide's question for this step. |
| E10 | button | Reset demo | demo bar | 63.2%, 25% · 128 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Resets the demo: clears this session's server rows and this phone's demo class. |
| E11 | heading | Demo flow | main | 4.1%, 34.6% · 358 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E12 | element | Demo: made-up class 3A, 20 simulated children, no real child | main | 4.1%, 41% · 358 x 54 | 15.3px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Shows text or a value. |
| E13 | heading | Step 7: form cohorts | main | 4.1%, 54% · 358 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E14 | element | Your class qualifies for 2 tracks; it takes one a term: SUB-SFL. | main | 4.1%, 71.7% · 358 x 54 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E15 | heading | Cohort: ADD-NOCARRY | main | 8.5%, 85% · 324 x 32 | 21.06px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E16 | element | Your class also qualifies for ADD-NOCARRY: one track a term, so this o | main | 8.5%, 49.5% · 324 x 81 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E17 | heading | Cohort: PV-HEARD | main | 8.5%, 40.1% · 324 x 32 | 21.06px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E18 | element | Your class is not in this cohort. | main | 8.5%, 54.6% · 324 x 27 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E19 | heading | Cohort: SUB-SFL | main | 9.2%, 38.7% · 321 x 32 | 21.06px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E20 | element | Your class is in this cohort: its track this term is SUB-SFL. | main | 9.2%, 53.2% · 321 x 54 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E21 | link | Go to step 8 | main | 4.1%, 78.8% · 358 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Opens #/demo?step=8. |
| E22 | link | Home | bottom bar | 0%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to Home. |
| E23 | link | Enter check | bottom bar | 20%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the check entry. |
| E24 | link | My class | bottom bar | 40%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to What my class gets wrong. |
| E25 | link | Practice | bottom bar | 60%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the Practice Class. |
| E26 | button | More [collapsed] | bottom bar | 80%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens the menu of the other screens. |

### State "s8-lesson" · judge · en · phone

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | Cohort Coach | header | 4.1%, 0.9% · 168 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | image |  | header | 4.1%, 1.7% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E3 | button | Assistant | header | 4.1%, 6.6% · 125 x 44 | 18px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E4 | status | 1 result waiting to send Good signal · 9.2 Mbps | header | 38.2%, 7.2% · 137 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E5 | element | Good signal · 9.2 Mbps | header | 48.2%, 7.8% · 85 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | element | Demo step 8 of 11 | demo bar | 3.1%, 13.4% · 135 x 21 | 15.75px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 220, 196) (--warn-container); radius 0px | Shows text or a value. |
| E7 | button | Back | demo bar | 3.1%, 19.3% · 71 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Goes to the previous demo step. |
| E8 | button | Next | demo bar | 22.2%, 19.3% · 71 x 44 | 18px / 400; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Goes to the next demo step, as the right role. |
| E9 | link | Judge guide for this step | demo bar | 3.1%, 25% · 231 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Opens the judge guide's question for this step. |
| E10 | button | Reset demo | demo bar | 63.2%, 25% · 128 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Resets the demo: clears this session's server rows and this phone's demo class. |
| E11 | heading | Demo flow | main | 4.1%, 34.6% · 358 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E12 | element | Demo: made-up class 3A, 20 simulated children, no real child | main | 4.1%, 41% · 358 x 54 | 15.3px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Shows text or a value. |
| E13 | heading | Step 8: the first audio lesson | main | 4.1%, 54% · 358 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E14 | button | Make the first audio lesson | main | 4.1%, 74.9% · 358 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Makes lesson 1 (pre-approved for the demo) and plays it. |
| E15 | element | Demo: pre-approved Drafted by AI, checked by code Hello, and welcome.  | main | 4.1%, 82.1% · 358 x 2728 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 16px (--s4) | Shows text or a value. |
| E16 | element | Demo: pre-approved | main | 8.5%, 83.6% · 169 x 31 | 15.3px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Shows text or a value. |
| E17 | link | Try it in Practice Class | main | 8.5%, 71.1% · 158 x 72 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Opens #/practice?next=ask_explain. |
| E18 | button | Make it again | main | 51%, 71.1% · 158 x 72 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to make it again. |
| E19 | link | Home | bottom bar | 0%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to Home. |
| E20 | link | Enter check | bottom bar | 20%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the check entry. |
| E21 | link | My class | bottom bar | 40%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to What my class gets wrong. |
| E22 | link | Practice | bottom bar | 60%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the Practice Class. |
| E23 | button | More [collapsed] | bottom bar | 80%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens the menu of the other screens. |

### State "s9-practice" · judge · en · phone

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | Cohort Coach | header | 4.1%, 0.9% · 168 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | image |  | header | 4.1%, 1.7% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E3 | button | Assistant | header | 4.1%, 6.6% · 125 x 44 | 18px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E4 | status | 1 result waiting to send Good signal · 9.2 Mbps | header | 38.2%, 7.2% · 137 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E5 | element | Good signal · 9.2 Mbps | header | 48.2%, 7.8% · 85 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | element | Demo step 9 of 11 | demo bar | 3.1%, 13.4% · 135 x 21 | 15.75px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 220, 196) (--warn-container); radius 0px | Shows text or a value. |
| E7 | button | Back | demo bar | 3.1%, 19.3% · 71 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Goes to the previous demo step. |
| E8 | button | Next | demo bar | 22.2%, 19.3% · 71 x 44 | 18px / 400; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Goes to the next demo step, as the right role. |
| E9 | link | Judge guide for this step | demo bar | 3.1%, 25% · 231 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Opens the judge guide's question for this step. |
| E10 | button | Reset demo | demo bar | 63.2%, 25% · 128 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Resets the demo: clears this session's server rows and this phone's demo class. |
| E11 | heading | Practice class | main | 4.1%, 32.7% · 358 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E12 | tab | Practise [selected] | main | 4.1%, 37.6% · 179 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E13 | tab | Review | main | 50%, 37.6% · 179 x 48 | 18px / 600; rgb(63, 73, 72) (--muted); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E14 | status | From your lesson: ask a child to explain how they got the answer befor | main | 4.1%, 53.9% · 358 x 107 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 16px (--s4) | Message shown to the user (read out by a screen reader). |
| E15 | element | Help children who take the smaller digit from the larger. Teach as you | main | 4.1%, 79.5% · 358 x 108 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E16 | button | Start practice | main | 4.1%, 64.4% · 358 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Starts a rehearsal with five simulated children. |
| E17 | label | Share this session to improve the simulator | main | 4.1%, 71.5% · 358 x 54 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E18 | checkbox | Share this session to improve the simulator | main | 5.1%, 73.3% · 23 x 24 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(247, 250, 250) (--paper); radius 0px | Tick box: turns an option on or off. |
| E19 | link | Home | bottom bar | 0%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to Home. |
| E20 | link | Enter check | bottom bar | 20%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the check entry. |
| E21 | link | My class | bottom bar | 40%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to What my class gets wrong. |
| E22 | link | Practice [current] | bottom bar | 60%, 90.3% · 78 x 82 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the Practice Class. |
| E23 | button | More [collapsed] | bottom bar | 80%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens the menu of the other screens. |

### State "s10-chat" · judge · en · phone

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | Cohort Coach | header | 4.1%, 0.9% · 168 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | image |  | header | 4.1%, 1.7% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E3 | button | Assistant | header | 4.1%, 6.6% · 125 x 44 | 18px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E4 | status | 1 result waiting to send Good signal · 9.2 Mbps | header | 38.2%, 7.2% · 137 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E5 | element | Good signal · 9.2 Mbps | header | 48.2%, 7.8% · 85 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | element | Demo step 10 of 11 | demo bar | 3.1%, 13.4% · 145 x 21 | 15.75px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 220, 196) (--warn-container); radius 0px | Shows text or a value. |
| E7 | button | Back | demo bar | 3.1%, 19.3% · 71 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Goes to the previous demo step. |
| E8 | button | Next | demo bar | 22.2%, 19.3% · 71 x 44 | 18px / 400; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Goes to the next demo step, as the right role. |
| E9 | link | Judge guide for this step | demo bar | 3.1%, 25% · 231 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Opens the judge guide's question for this step. |
| E10 | button | Reset demo | demo bar | 63.2%, 25% · 128 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Resets the demo: clears this session's server rows and this phone's demo class. |
| E11 | heading | Demo flow | main | 4.1%, 34.6% · 358 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E12 | element | Demo: made-up class 3A, 20 simulated children, no real child | main | 4.1%, 41% · 358 x 54 | 15.3px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Shows text or a value. |
| E13 | heading | Step 10: cohort chat | main | 4.1%, 54% · 358 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E14 | label | Your question | main | 4.1%, 78.1% · 358 x 130 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E15 | textbox | Your question | main | 4.1%, 81.8% · 358 x 99 | 18px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E16 | button | Ask the cohort [disabled] | main | 4.1%, 46.4% · 358 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Sends the question to the cohort chat. |
| E17 | status | Waiting for a mentor or coach: 0 seconds before the AI may answer. | main | 8.5%, 55% · 324 x 54 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Message shown to the user (read out by a screen reader). |
| E18 | button | Skip the wait | main | 8.5%, 63.8% · 324 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Stops waiting for a person and checks whether the AI may answer. |
| E19 | element | Waiting for a mentor or coach to answer. | main | 8.5%, 85.1% · 324 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E20 | link | Home | bottom bar | 0%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to Home. |
| E21 | link | Enter check | bottom bar | 20%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the check entry. |
| E22 | link | My class | bottom bar | 40%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to What my class gets wrong. |
| E23 | link | Practice | bottom bar | 60%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the Practice Class. |
| E24 | button | More [collapsed] | bottom bar | 80%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens the menu of the other screens. |

### State "s11-coach" · judge · en · phone

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | Cohort Coach | header | 4.1%, 0.9% · 168 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | image |  | header | 4.1%, 1.7% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E3 | button | Assistant | header | 4.1%, 6.6% · 125 x 44 | 18px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E4 | status | 1 result waiting to send Good signal · 9.2 Mbps | header | 38.2%, 7.2% · 137 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E5 | element | Good signal · 9.2 Mbps | header | 48.2%, 7.8% · 85 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | element | Demo step 11 of 11 | demo bar | 3.1%, 13.4% · 145 x 21 | 15.75px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 220, 196) (--warn-container); radius 0px | Shows text or a value. |
| E7 | button | Back | demo bar | 3.1%, 19.3% · 71 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Goes to the previous demo step. |
| E8 | button | Next: optional post-test | demo bar | 22.2%, 19.3% · 222 x 44 | 18px / 400; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Goes to the next demo step, as the right role. |
| E9 | link | Judge guide for this step | demo bar | 3.1%, 25% · 231 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Opens the judge guide's question for this step. |
| E10 | button | Reset demo | demo bar | 63.2%, 25% · 128 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Resets the demo: clears this session's server rows and this phone's demo class. |
| E11 | heading | Demo flow | main | 4.1%, 34.6% · 358 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E12 | element | Demo: made-up class 3A, 20 simulated children, no real child | main | 4.1%, 41% · 358 x 54 | 15.3px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Shows text or a value. |
| E13 | heading | Step 11: coach and SCERT views | main | 4.1%, 54% · 358 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E14 | tab | Coach [selected] | main | 4.1%, 60.3% · 83 x 44 | 18px / 400; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Shows text or a value. |
| E15 | tab | SCERT officer | main | 27.5%, 60.3% · 138 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Shows text or a value. |
| E16 | heading | Cohorts | main | 4.1%, 72.2% · 358 x 32 | 21.06px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E17 | heading | Cohort: ADD-NOCARRY | main | 8.5%, 83.9% · 324 x 32 | 21.06px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E18 | element | Your class also qualifies for ADD-NOCARRY: one track a term, so this o | main | 8.5%, 48.4% · 324 x 81 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E19 | heading | Cohort: PV-HEARD | main | 8.5%, 39% · 324 x 32 | 21.06px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E20 | element | Your class is not in this cohort. | main | 8.5%, 53.5% · 324 x 27 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E21 | heading | Cohort: SUB-SFL | main | 9.2%, 87.6% · 321 x 32 | 21.06px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E22 | element | Your class is in this cohort: its track this term is SUB-SFL. | main | 9.2%, 52.1% · 321 x 54 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E23 | heading | Review queue | main | 4.1%, 41.1% · 358 x 32 | 21.06px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E24 | element | The teacher's question How do I help children who take the smaller dig | main | 4.1%, 48.8% · 358 x 545 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 16px (--s4) | Shows text or a value. |
| E25 | heading | The teacher's question | main | 8.5%, 53.2% · 324 x 27 | 18px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E26 | element | The AI found no approved material for this error yet, so it did not dr | main | 8.5%, 71.8% · 324 x 96 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E27 | label | Answer in your own words | main | 8.5%, 86% · 324 x 130 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E28 | textbox | Answer in your own words | main | 8.5%, 39.7% · 324 x 99 | 18px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E29 | button | Send the answer [disabled] | main | 8.5%, 54.2% · 324 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Button: tap to send the answer. |
| E30 | element | Mentor method card Simulated mentor (Teacher 3) awaiting_coach Open a  | main | 4.1%, 66.7% · 358 x 613 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 16px (--s4) | Shows text or a value. |
| E31 | heading | Mentor method card | main | 8.5%, 71% · 324 x 27 | 18px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E32 | button | Approve | main | 8.5%, 80.6% · 158 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Button: tap to approve. |
| E33 | button | Reject | main | 51%, 80.6% · 158 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to reject. |
| E34 | element | Lesson 2, drafted by AI AI draft pending Open it in the review queue A | main | 4.1%, 42.6% · 358 x 300 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 16px (--s4) | Shows text or a value. |
| E35 | heading | Lesson 2, drafted by AI | main | 8.5%, 47% · 324 x 27 | 18px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E36 | link | Open it in the review queue | main | 8.5%, 60.9% · 324 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Opens #/review. |
| E37 | button | Approve | main | 8.5%, 69.5% · 158 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Button: tap to approve. |
| E38 | button | Reject | main | 51%, 69.5% · 158 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to reject. |
| E39 | label | Why is it rejected? | main | 4.1%, 81.4% · 358 x 79 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E40 | textbox | Why is it rejected? | main | 4.1%, 85.1% · 358 x 48 | 18px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E41 | link | Coach | bottom bar | 0%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/coach. |
| E42 | link | Review | bottom bar | 20%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/review. |
| E43 | link | Papers | bottom bar | 40%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/papers. |
| E44 | link | Cohort | bottom bar | 60%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/cohort. |
| E45 | link | My profile | bottom bar | 80%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/profile. |

### State "s11-officer" · judge · en · phone

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | Cohort Coach | header | 4.1%, 0.9% · 168 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | image |  | header | 4.1%, 1.7% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E3 | button | Assistant | header | 4.1%, 6.6% · 125 x 44 | 18px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E4 | status | 1 result waiting to send Good signal · 9.2 Mbps | header | 38.2%, 7.2% · 137 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E5 | element | Good signal · 9.2 Mbps | header | 48.2%, 7.8% · 85 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | element | Demo step 11 of 11 | demo bar | 3.1%, 13.4% · 145 x 21 | 15.75px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 220, 196) (--warn-container); radius 0px | Shows text or a value. |
| E7 | button | Back | demo bar | 3.1%, 19.3% · 71 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Goes to the previous demo step. |
| E8 | button | Next: optional post-test | demo bar | 22.2%, 19.3% · 222 x 44 | 18px / 400; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Goes to the next demo step, as the right role. |
| E9 | link | Judge guide for this step | demo bar | 3.1%, 25% · 231 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Opens the judge guide's question for this step. |
| E10 | button | Reset demo | demo bar | 63.2%, 25% · 128 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Resets the demo: clears this session's server rows and this phone's demo class. |
| E11 | heading | Demo flow | main | 4.1%, 34.6% · 358 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E12 | element | Demo: made-up class 3A, 20 simulated children, no real child | main | 4.1%, 41% · 358 x 54 | 15.3px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Shows text or a value. |
| E13 | heading | Step 11: coach and SCERT views | main | 4.1%, 54% · 358 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E14 | tab | Coach | main | 4.1%, 60.3% · 83 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Shows text or a value. |
| E15 | tab | SCERT officer [selected] | main | 27.5%, 60.3% · 138 x 44 | 18px / 400; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Shows text or a value. |
| E16 | region | Classes per cohort | main | 4.1%, 43.2% · 358 x 141 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E17 | element | Classes per cohort Error Classes ADD-NOCARRY 6 PV-HEARD Hidden (under  | main | 4.1%, 43.2% · 265 x 141 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E18 | region | Classes by track error | main | 4.1%, 63.2% · 358 x 213 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E19 | element | Classes by track error Error Classes Share of classes ADD-NOCARRY 10 4 | main | 4.1%, 63.2% · 358 x 213 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E20 | element | Tracks started this term: 14. Waiting for next term: 10. | main | 4.1%, 71.6% · 358 x 54 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E21 | element | Approvals waiting for the coach: 3. | main | 4.1%, 80.9% · 358 x 27 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E22 | link | Officer | bottom bar | 0%, 93.1% · 130 x 58 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/officer. |
| E23 | link | Review | bottom bar | 33.3%, 93.1% · 130 x 58 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/review. |
| E24 | link | My profile | bottom bar | 66.7%, 93.1% · 130 x 58 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/profile. |

### State "s12-post" · judge · en · phone

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | Cohort Coach | header | 4.1%, 0.9% · 168 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | image |  | header | 4.1%, 1.7% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E3 | button | Assistant | header | 4.1%, 6.6% · 125 x 44 | 18px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E4 | status | 1 result waiting to send Good signal · 9.2 Mbps | header | 38.2%, 7.2% · 137 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E5 | element | Good signal · 9.2 Mbps | header | 48.2%, 7.8% · 85 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | element | Optional step 12 | demo bar | 3.1%, 13.4% · 123 x 21 | 15.75px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 220, 196) (--warn-container); radius 0px | Shows text or a value. |
| E7 | button | Back | demo bar | 3.1%, 19.3% · 71 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Goes to the previous demo step. |
| E8 | button | Next [disabled] | demo bar | 22.2%, 19.3% · 71 x 44 | 18px / 400; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Goes to the next demo step, as the right role. |
| E9 | link | Judge guide for this step | demo bar | 3.1%, 25% · 231 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Opens the judge guide's question for this step. |
| E10 | button | Reset demo | demo bar | 63.2%, 25% · 128 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Resets the demo: clears this session's server rows and this phone's demo class. |
| E11 | heading | Demo flow | main | 4.1%, 34.6% · 378 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E12 | element | Demo: made-up class 3A, 20 simulated children, no real child | main | 4.1%, 41% · 378 x 54 | 15.3px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Shows text or a value. |
| E13 | heading | Optional step 12: the post-test | main | 4.1%, 54% · 378 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E14 | button | Simulate the post-test [disabled] | main | 4.1%, 71.7% · 378 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Simulates the post-test on the twin paper. |
| E15 | heading | Before and after | main | 4.1%, 41.2% · 378 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E16 | element | Demo data | main | 4.1%, 45.1% · 101 x 31 | 15.3px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Shows text or a value. |
| E17 | element | Pre-test Form A (31 Oct 2026) to Post-test Form B (21 Nov 2026) | main | 4.1%, 50.2% · 378 x 54 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E18 | region | Before and after | main | 4.1%, 58% · 378 x 285 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E19 | element | Skill Flagged before No longer flagged Still flagged Newly flagged Pla | main | 4.1%, 58% · 378 x 285 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E20 | element | Place value 2 0 2 1 | main | 4.2%, 67.2% · 377 x 53 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E21 | element | Adding with carrying 7 2 5 0 | main | 4.2%, 73.5% · 377 x 77 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E22 | element | Taking away with borrowing 9 6 3 1 | main | 4.2%, 82.6% · 377 x 77 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E23 | element | 20 children paired by roll order. 0 left out: away, nothing entered, o | main | 4.1%, 70.3% · 378 x 48 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E24 | link | Home | bottom bar | 0%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to Home. |
| E25 | link | Enter check | bottom bar | 20%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the check entry. |
| E26 | link | My class | bottom bar | 40%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to What my class gets wrong. |
| E27 | link | Practice | bottom bar | 60%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the Practice Class. |
| E28 | button | More [collapsed] | bottom bar | 80%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens the menu of the other screens. |

## 5. Content and data

Each step is a real product screen with the demo bar on top. Sheets are synthetic and labelled "Not real children's work". The review drawer shows the sheet beside what was read. The officer dashboard hides cells under 5.

The text on screen, copied exactly from the page in the first state:

```text
Simulated data: this class and these children are made up for the demo.

Start a check

Say which check these papers belong to, so every result is tied to the right paper and date.

Class 3A (demo) · Term 1

What kind of check is this?
Pre-test · suggested
Post-test
Termly check
Date of the check
How many papers? (optional)
Saved for this class

No check is saved yet for this class.

Print a paper for this check
Which paper?
The pilot paper (Form A): answers can be entered on this phone
A new paper for this class: print it and mark it by hand with its answer key
Language of the paper
English
हिन्दी (Hindi)
தமிழ் (Tamil)
Second language (optional)
None
हिन्दी (Hindi)
தமிழ் (Tamil)

With two languages, every instruction on the paper is printed in the first, then the second.

Make the paper
A · PRE · 3A · T1

Approved by the rules

The standard paper: no check of this class is saved yet · 10 questions, the same skills as the pilot paper · rules version 1 · English

Anchor items

The same skills and level on every paper. Before and after are compared on these only.

1. Say aloud: 346
2. Say aloud: 728
3. 38 + 47
4. 46 + 28
5. 59 + 23
6. 87 − 52
7. 74 − 36
8. 45 − 19
9. 82 − 39
10. 81 − 27
Which items check each error
Error	1	2	3	4	5	6	7	8	9	10	Items
PV-HEARD	●	●									2
PV-REVERSE	●	●									2
ADD-NOCARRY			●	●	●						3
SUB-SFL							●	●	●	●	4
SUB-NODEC							●	●	●	●	4
Automatic checks

Every automatic check passed.

Print the paper
Print the answer key
Show the answers

Paper A · PRE · 3A · T1

Which paper did the children write?
Paper A · suggested
Paper B

Enter the papers in roll order. Only your phone knows which paper is which child.

Use sample sheets
```

Dynamic parts: counts, dates, names of the demo class and every number come from the demo class loaded in Judge mode or from the 12-step demo session; the code computes them.

## 6. States and transitions

- **s2-paper**: reached in the 12-step demo session, in order.
- **s3-sheets**: reached in the 12-step demo session, in order.
- **s4-entry**: reached in the 12-step demo session, in order.
- **s5-drawer**: reached in the 12-step demo session, in order.
- **s5-approved**: reached in the 12-step demo session, in order.
- **s6-counts**: reached in the 12-step demo session, in order.
- **s7-cohorts**: reached in the 12-step demo session, in order.
- **s8-lesson**: reached in the 12-step demo session, in order.
- **s9-practice**: reached in the 12-step demo session, in order.
- **s10-chat**: reached in the 12-step demo session, in order.
- **s11-coach**: reached in the 12-step demo session, in order.
- **s11-officer**: reached in the 12-step demo session, in order.
- **s12-post**: reached in the 12-step demo session, in order.
- Empty, loading, error and offline states were not captured in this pack (core scope). The loaders and messages are listed in the product's own strings (`strings/en.json`).

## 7. What works and what to change

Measured from the numbered elements (touch targets, font sizes, sideways scroll, labels). There is no current UI audit of this app: `docs/design/audit/AUDIT.md` describes the original front end before the re-skin, so it is not used here.

- A wide table or row scrolls sideways in state "s5-drawer" (phone): see the -hscroll image.
- Touch target under 44 px: "The pilot paper (Form A): answers can be" (s2-paper/en: 24 x 24 px).
- Touch target under 44 px: "A new paper for this class: print it and" (s2-paper/en: 24 x 24 px).
- Touch target under 44 px: "Share this session to improve the simula" (s9-practice/en: 23 x 24 px).
- 8 distinct font sizes among the numbered elements in s2-paper, en, phone: 13.3333px, 15.3px, 15.75px, 16px, 18px, 20px, 21.06px, 24px.

## 8. Constraints

- Phone first at 390 px; desktop for coach, officer, judge and mentor screens.
- Touch targets at least 44 px, primary buttons 48 px.
- English, Hindi and Tamil text must fit without cutting.
- Use the tokens in `../00-tokens.md`: Material 3, Calm Institutional palette (teal primary), no new colours.
- Teacher-facing numbers are counts, never percentages. Simulated data stays labelled.
- No new features: redesign what exists.
