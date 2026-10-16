from scripts.feedback_table import render

LOG = """# Feedback log

| date | round | participant code | what they said or did | what we changed | commit | status |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-10-22 | 3 | T01 | Could not find the play button | Made it larger | abc123 | done |
| 2026-10-22 | 3 | T02 | | | | open |
"""


def test_renders_only_rows_with_a_change() -> None:
    table = render(LOG)
    assert "Could not find the play button | Made it larger | abc123" in table
    assert "T02" not in table
