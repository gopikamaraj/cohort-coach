"""Try with hints (judge mode): three replies each turn, built by code from the move list.

One is a strong move, one a common mistake, one neutral; each is a sample line stored with its move
in content/movelists. The picks follow the conversation: a strong move is the next unused one in the
list's own order whose `after` condition holds (so "exchange a bundle" is offered only once bundles
have been shown); a mistake is one that fits what has happened (a rule repeated "louder" only after
the rule was told; scolding last); and when the class is working a problem other than the one the
sample lines are written about, lines that carry that example's numbers are left out. The order is
shuffled by a seed so the strong one is not always first, and nothing says which is which until the
move tag shows after she chooses. No AI call is made.
"""

from __future__ import annotations

import random
import re
from typing import Any

from services.practice.session import PracticeSession

QUALITIES = ("strong", "common_mistake", "neutral")
LAST_RESORT = ("scold",)  # offered as a mistake only when nothing else fits


def _fits(session: PracticeSession, move: Any, used: set[str]) -> bool:
    """The move's `after` condition holds, and the line does not carry example-only numbers."""
    if move.after and not used & set(move.after):
        return False
    state = session.state
    example = session.loaded.config.problems[0]
    if state.problem and (state.problem.a, state.problem.b) != (example.a, example.b):
        return not re.search(r"\d", move.sample_lines[session.language][0])
    return True


def _pick(session: PracticeSession, quality: str, used: set[str], last: str | None) -> Any | None:
    lang = session.language
    pool = [
        m
        for m in session.loaded.movelist.moves
        if m.quality == quality and m.sample_lines.get(lang) and _fits(session, m, used)
    ]
    if quality == "neutral":
        pool = [m for m in pool if m.id != "pose_problem"]  # a problem is posed first
    if quality == "common_mistake":
        pool.sort(key=lambda m: m.id in LAST_RESORT)  # stable: list order, scolding last
    # a move the last move unlocked comes first (bundles shown: now exchange one), then list order
    pool.sort(key=lambda m: not (last and last in m.after))
    fresh = [m for m in pool if m.id not in used and m.id != last]
    return (fresh or [m for m in pool if m.id != last] or pool or [None])[0]


def hints(session: PracticeSession) -> list[dict[str, str]]:
    """Up to three replies for the next turn: {move, line}. Quality is not sent."""
    lang = session.language
    turn = len(session.records) + 1
    moves = {m.id: m for m in session.loaded.movelist.moves}
    if not session.records:  # the first thing to do is pose a problem
        m = moves.get("pose_problem")
        return (
            [{"move": m.id, "line": m.sample_lines[lang][0]}]
            if m and m.sample_lines.get(lang)
            else []
        )
    used = {r.move_id for r in session.records}
    # a hint she took says the sample line word for word, which is more exact than the label
    said = {r.teacher_text: i for i, r in enumerate(session.records)}
    taken = {m.id: said[m.sample_lines[lang][0]] for m in moves.values()
             if m.sample_lines.get(lang) and m.sample_lines[lang][0] in said}  # fmt: skip
    used |= set(taken)
    last = session.records[-1].move_id
    for mid, at in taken.items():
        if at == len(session.records) - 1:
            last = mid
    picks = [_pick(session, q, used, last) for q in QUALITIES]
    out = [{"move": m.id, "line": m.sample_lines[lang][0]} for m in picks if m is not None]
    random.Random(f"hints:{session.seed}:{turn}").shuffle(out)
    return out
