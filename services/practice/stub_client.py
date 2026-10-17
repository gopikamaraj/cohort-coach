"""A rule-based stand-in for the Claude API: same `.messages.parse(...)` shape, no network.

Used for offline rehearsals (`scripts/practice_cli.py --stub`), CI and demos with no API key. It
is not a model and makes no claim about model quality: it reads the same facts a real call
reads and answers by simple rules, so the engine, validators, gates and API can be exercised
end to end. Calls made through it are audited with mode "stub" and cost nothing.
"""

from __future__ import annotations

import json
import re
from types import SimpleNamespace
from typing import Any

from ai.schemas import ChildLine, Feedback, FeedbackPoint, PosedProblem, TryNext, Verdict

_SUM = re.compile(r"(\d+)\s*(minus|plus|-|\+)\s*(\d+)", re.IGNORECASE)
_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("scold", ("wrong again", "pay attention", "stupid", "silly", "shut up")),
    ("exchange_ten", ("open a bundle", "exchange", "regroup")),
    ("check_back", ("check", "add back", "adding back", "read back", "take away from")),
    ("ask_explain", ("explain", "how you got", "how did you", "what did you do")),
    ("show_bundles", ("bundle", "sticks")),
    ("praise", ("well done", "well tried", "good job", "thank you", "shabash", "great")),
    ("tell_rule", ("the rule", "always take", "remember to")),
]


def _facts_and_text(kwargs: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    content = kwargs["messages"][0]["content"][-1]["text"]
    facts_raw = re.search(r"<facts>\n(.*?)\n</facts>", content, re.DOTALL)
    facts: dict[str, Any] = json.loads(facts_raw.group(1)) if facts_raw else {}
    tags = {
        m.group(1): m.group(2) for m in re.finditer(r"<(\w+)>\n(.*?)\n</\1>", content, re.DOTALL)
    }
    return facts, tags


class _Messages:
    def parse(self, **kwargs: Any) -> Any:
        facts, tags = _facts_and_text(kwargs)
        name = kwargs["output_format"].__name__
        if name == "Verdict":
            out: Any = Verdict(
                passed=True, reason_short="stub: no rule broken", reason_for_user="ok"
            )
        elif name == "ChildLine":
            out = self._child(facts)
        elif name == "Feedback":
            out = self._feedback(facts, tags.get("transcript", ""))
        else:
            out = self._label(kwargs["output_format"], facts, tags.get("teacher_line", ""))
        usage = SimpleNamespace(
            input_tokens=0,
            output_tokens=0,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
        )
        return SimpleNamespace(parsed_output=out, usage=usage)

    @staticmethod
    def _child(facts: dict[str, Any]) -> ChildLine:
        intent, answer = facts["intent"], facts.get("answer")
        if intent == "answer" and answer is not None:
            return ChildLine(text=f"{answer}, Miss!")
        if intent in {"explain", "work_aloud", "doubt"} and facts.get("steps"):
            return ChildLine(text=". ".join(s["meaning"] for s in facts["steps"]) + ".")
        lines = {
            "agree": "OK Miss, let me look again.",
            "thanks": "Thank you, Miss!",
            "quiet": "Yes, Miss.",
        }
        return ChildLine(text=lines.get(intent, "Miss, I did not understand."))

    @staticmethod
    def _label(model: Any, facts: dict[str, Any], line: str) -> Any:
        low = line.lower()
        kids = list(facts.get("children", []))
        addressed = next((k for k in kids if k.lower() in low), "none")
        ids = {m["id"] for m in facts.get("moves", [])}
        if any(w in low for w in ("ignore", "answer key", "system prompt", "you are now")):
            return model(move_id="off_task", addressed_child="none", confidence=0.95)
        for move, words in _RULES:
            if move in ids and any(w in low for w in words):
                return model(move_id=move, addressed_child=addressed, confidence=0.9)
        m = _SUM.search(line)
        if m and "pose_problem" in ids:
            op = "-" if m.group(2).lower() in {"minus", "-"} else "+"
            posed = PosedProblem(a=int(m.group(1)), op=op, b=int(m.group(3)))  # type: ignore[arg-type]
            return model(move_id="pose_problem", addressed_child=addressed, posed_problem=posed,
                         confidence=0.9)  # fmt: skip
        if "?" in line and "pose_problem" in ids:
            return model(move_id="pose_problem", addressed_child=addressed, confidence=0.7)
        return model(move_id="other", addressed_child=addressed, confidence=0.2)

    @staticmethod
    def _feedback(facts: dict[str, Any], transcript: str) -> Feedback:
        turns = {
            int(m.group(1)): m.group(2)
            for m in re.finditer(r"^T(\d+) teacher: (.*)$", transcript, re.MULTILINE)
        }
        label_of = {x["turn"]: x["move_id"] for x in facts["labels"]}
        used: list[tuple[dict[str, Any], int]] = []
        for point in facts["rubric"]:
            tid = next((t for t, m in label_of.items() if m in point["moves"] and t in turns), None)
            if tid is not None:
                used.append((point, tid))
        strengths = [
            FeedbackPoint(
                rubric_point=p["id"],
                turn_id=t,
                quote=" ".join(turns[t].split()[:8]),
                comment=p["text"],
            )
            for p, t in used[:2]
        ]
        spare = [p for p in facts["rubric"] if p["id"] not in {u[0]["id"] for u in used}]
        pick = (spare or facts["rubric"])[0]
        return Feedback.model_construct(
            strengths=strengths,
            try_next=TryNext(rubric_point=pick["id"], suggestion=pick["try_next"]),
        )


class StubClient:
    def __init__(self) -> None:
        self.messages = _Messages()
