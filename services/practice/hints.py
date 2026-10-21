"""Try with hints (judge mode): three replies each turn, built by code from the move list.

One is a strong move, one a common mistake, one neutral; each is a sample line stored with its move
in content/movelists. The order is shuffled by a seed so the strong one is not always first, and
nothing says which is which until the move tag shows after she chooses. No AI call is made.
"""

from __future__ import annotations

import random
from typing import Any

from services.practice.session import PracticeSession

QUALITIES = ("strong", "common_mistake", "neutral")


def _pick(session: PracticeSession, quality: str, used: set[str], turn: int) -> Any | None:
    lang = session.language
    pool = [
        m
        for m in session.loaded.movelist.moves
        if m.quality == quality and m.sample_lines.get(lang)
    ]
    if quality == "neutral":
        pool = [m for m in pool if m.id != "pose_problem"] or pool  # a problem is posed first
    fresh = [m for m in pool if m.id not in used]
    chosen = fresh or pool
    return chosen[turn % len(chosen)] if chosen else None


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
    picks = [_pick(session, q, used, turn) for q in QUALITIES]
    out = [{"move": m.id, "line": m.sample_lines[lang][0]} for m in picks if m is not None]
    random.Random(f"hints:{session.seed}:{turn}").shuffle(out)
    return out
