"""Minimum group sizes and suppressions, and the one switch that turns them off for the demo.

Production keeps them: a figure over fewer than 5 classes is hidden (CLAUDE.md section 4.3), a share needs at least
10 children checked, a cohort needs at least two classes. In demo mode (the judge-mode deployment, `JUDGE_MODE=1`,
where every class is a test or simulated one) every one of them is off and the pages say so. The production values
stay here and in the environment (`OFFICER_MIN_CLASSES`), so turning the demo off puts them back; nothing else reads
the numbers 5, 10 or 2 for these rules.
"""

from __future__ import annotations

import os

from ai.config import judge_mode
from engine.evaluation import MIN_CLASSES_SHOWN
from engine.diagnosis import MIN_CHILDREN_CHECKED

DEMO_LABEL = "Demo: no minimum group sizes"


def caps_off() -> bool:
    """True in demo mode only. Decided by the server, never by a request."""
    return judge_mode()


def min_classes_shown() -> int:
    """Classes needed before an officer figure is shown: 5 in production (`OFFICER_MIN_CLASSES` may set another
    value), 1 in demo mode."""
    if caps_off():
        return 1
    try:
        return max(1, int(os.environ.get("OFFICER_MIN_CLASSES", MIN_CLASSES_SHOWN)))
    except ValueError:
        return MIN_CLASSES_SHOWN


def min_children_checked() -> int:
    return 1 if caps_off() else MIN_CHILDREN_CHECKED


def min_cohort_classes() -> int:
    """Entered classes that must show a mistake before a cohort can be made from them: two, or one in demo mode."""
    return 1 if caps_off() else 2


def describe() -> dict[str, object]:
    """What the pages show next to a figure: whether the minimums are off, and the label to print."""
    return {"off": caps_off(), "label": DEMO_LABEL if caps_off() else None, "min_classes": min_classes_shown(), "min_children": min_children_checked(), "min_cohort_classes": min_cohort_classes()}
