# Test sheets (made up)

Ten made-up answer sheets for **Form A**, one image per sheet, with no child, no real handwriting and no
pilot data (they come from `scripts/make_synthetic_sheets.py`; `truth_source: rendered_by_code`). They
are the files the team uploads to the shared Google Drive folder named in the deck.

Use them with the standard test paper (the published pilot-test numbers):

1. Open Enter check, choose the standard test paper (run `python scripts/seed_test_paper.py --class-id <id>`
   for a hosted test class), enter the class size, and start.
2. Add the sheets: **Select a folder of pictures** and choose this folder, or **Take a photo** of one.
3. Check each roll against its picture (the image icon), approve it, and finish.

A sheet is matched to a roll number by its file name, then by the class code and roll number in its
header, and otherwise you choose. Nothing here is stored by the app: pictures are read and dropped.
