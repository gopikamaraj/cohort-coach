# ruff: noqa: E501
"""The AI review of a teacher's note about a module (call 17), and what code does with it.

Private: the review, the follow-up questions and her answers are visible only to her. The model sees the
masked note and facts about the module, never a name or class data. Everything it returns is checked
against closed lists in content/modules/feedback_review.v1.yaml; output that does not validate is
dropped, and AI off, offline or any failure means only the branch table applies.

What the tags DO is code (`focus_effects` in the library): prefer certain approaches among the
alternatives for "not yet", and put certain sections first. No AI text reaches the teacher except a
validated follow-up question.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from ai import config as ai_config
from ai.calls.c17_feedback_review import review_note
from ai.client import CallContext
from ai.schemas import FeedbackReview
from ai.validators.mask import mask_personal
from ai.validators.thread import check_thread_post
from services.api import strings
from services.modules import service
from services.modules.models import ModuleReview, Track, TrackModule

VOCAB = Path(__file__).resolve().parents[2] / "content" / "modules" / "feedback_review.v1.yaml"
CONFIDENCE_FLOOR = 0.5
MAX_FOLLOW_UPS = 2
MAX_ANSWER_CHARS = 200


@cache
def vocab() -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(VOCAB.read_text(encoding="utf-8"))
    return data


def reset() -> None:
    vocab.cache_clear()


def max_free_chars() -> int:
    return int(vocab()["free_question"]["max_chars"])


# ---- the free-text question checker ---------------------------------------------------------------

_JUDGE = re.compile(
    r"(you should have|you failed|your fault|why didn.?t you|why did you not|bad teacher|careless|negligen|"
    r"आपकी गलती|आपकी ग़लती|तुमने क्यों नहीं|आपने क्यों नहीं|உங்கள் தவறு|ஏன் செய்யவில்லை)",
    re.IGNORECASE,
)
_DIAGNOSE = re.compile(
    r"(dyslex|disorder|slow learner|retard|lazy|stupid|\bdull\b|disabled|autis|adhd|backward|"
    r"मंदबुद्धि|आलसी|मूर्ख|மந்த|சோம்பேறி|முட்டாள்)",
    re.IGNORECASE,
)
_ADVICE = re.compile(
    r"(^\s*(try|use|make sure|consider|please|do not|don.?t|always|never)\b|\byou (should|must|need to|ought)\b|"
    r"करना चाहिए|कीजिए|कीजिये|आपको चाहिए|செய்ய வேண்டும்|செய்யுங்கள்|வேண்டும் என்று)",
    re.IGNORECASE,
)


def check_free_question(text: str, language: str) -> list[str]:
    """Why a model-written free question may not be shown: an empty list means it passes."""
    t = text.strip()
    problems: list[str] = []
    if not t or len(t) > max_free_chars():
        problems.append("length")
    if not t.endswith(("?", "？")):
        problems.append("not_a_question")
    if mask_personal(t).kinds or check_thread_post(t, language):
        problems.append("names_or_numbers")
    if _JUDGE.search(t):
        problems.append("judges_the_teacher")
    if _DIAGNOSE.search(t):
        problems.append("diagnoses_a_child")
    if _ADVICE.search(t):
        problems.append("gives_advice")
    return problems


# ---- validating the model's output ----------------------------------------------------------------


@dataclass
class Validated:
    barrier_tags: list[str] = field(default_factory=list)
    focus_tags: list[str] = field(default_factory=list)
    follow_ups: list[dict[str, Any]] = field(default_factory=list)  # {id, kind, text?}
    safety: bool = False
    confidence: float = 0.0
    dropped: list[str] = field(default_factory=list)


def validate(out: FeedbackReview, language: str) -> Validated | None:
    """None when the output does not validate (an unknown tag or question id, or more than one free
    question): it is dropped whole. Below the confidence floor the tags are ignored. A free question that
    fails the checker is dropped alone."""
    v = vocab()
    if any(t not in v["barrier_tags"] for t in out.barrier_tags):
        return None
    if any(t not in v["focus_tags"] for t in out.focus_tags):
        return None
    free = [f for f in out.follow_ups if f.free_text and not f.bank_id]
    if len(free) > 1 or len(out.follow_ups) > MAX_FOLLOW_UPS:
        return None
    if any(f.bank_id and f.bank_id not in v["follow_up_bank"] for f in out.follow_ups):
        return None
    res = Validated(safety=out.safety, confidence=out.confidence)
    if out.safety:
        return res  # a gentle message; no tags, no questions
    if out.confidence < CONFIDENCE_FLOOR:
        res.dropped.append("low_confidence")
        return res
    res.barrier_tags = list(dict.fromkeys(out.barrier_tags))
    res.focus_tags = list(dict.fromkeys(out.focus_tags))
    for f in out.follow_ups:
        if f.bank_id:
            res.follow_ups.append({"id": f.bank_id, "kind": "bank"})
        elif f.free_text:
            problems = check_free_question(f.free_text, language)
            if problems:
                res.dropped.append("free_question:" + ",".join(problems))
            else:
                res.follow_ups.append({"id": "free-1", "kind": "free", "text": f.free_text.strip()})
    return res


# ---- running it -----------------------------------------------------------------------------------


def _bank_english() -> dict[str, str]:
    return {k: b["text"]["en"] for k, b in vocab()["follow_up_bank"].items()}


def ai_allowed() -> bool:
    return ai_config.ai_mode() != "off"


def should_run(answer: str, note: str) -> bool:
    """Skipped silently when there is no note and it worked."""
    return bool(note.strip()) or answer != "worked"


def run(
    db: Session,
    track: Track,
    module: TrackModule,
    answer: str,
    masked_note: str,
    language: str,
    online: bool = True,
    context: CallContext | None = None,
) -> ModuleReview:
    """Review one answer. Saves a ModuleReview either way; never raises."""
    existing = db.get(ModuleReview, module.id)
    row = existing or ModuleReview(module_id=module.id)
    row.status, row.barrier_tags, row.focus_tags, row.follow_ups, row.answers = (
        "none",
        [],
        [],
        [],
        [],
    )
    row.safety, row.confidence = False, 0.0
    try:
        if not (online and ai_allowed() and should_run(answer, masked_note)):
            return _save(db, row, existing)
        again = mask_personal(masked_note).text  # masked again before it leaves
        rows = service.modules_of(db, track.id)
        used = [m.approach_id or "" for m in service._generated(rows)]
        sections = [p["id"] for p in (module.text or {}).get("parts", [])]
        safe = service_safety(again)
        if safe:
            row.status, row.safety = "safety", True
            return _save(db, row, existing)
        got = review_note(
            **facts(track, module, answer, again, language, used, sections), context=context
        )
        checked = None if got.fell_back else validate(got.output, language)
        if checked is None:
            row.status = "failed"
        else:
            row.barrier_tags, row.focus_tags = checked.barrier_tags, checked.focus_tags
            row.follow_ups, row.safety, row.confidence = (
                checked.follow_ups,
                checked.safety,
                checked.confidence,
            )
            row.status = "safety" if checked.safety else ("asked" if checked.follow_ups else "none")
    except Exception:  # noqa: BLE001 - AI must never block saving her answer
        row.status = "failed"
    return _save(db, row, existing)


def facts(
    track: Track,
    module: TrackModule,
    answer: str,
    masked_note: str,
    language: str,
    used: list[str],
    sections: list[str],
) -> dict[str, Any]:
    """Everything the model is told, and nothing else: the masked note and facts about the module."""
    v = vocab()
    return {
        "masked_note": masked_note,
        "answer": answer,
        "error": track.error,
        "approach": module.approach_id or "",
        "sections": sections,
        "approaches_used": used,
        "language": language,
        "barrier_ids": list(v["barrier_tags"]),
        "focus_ids": list(v["focus_tags"]),
        "bank": _bank_english(),
    }


def service_safety(text: str) -> bool:
    """Welfare and safety words, checked in code first (the same list the chat uses)."""
    from services.chat.classify import _hits

    return bool(_hits("safety", text))


def _save(db: Session, row: ModuleReview, existing: ModuleReview | None) -> ModuleReview:
    if existing is None:
        db.add(row)
    db.commit()
    return row


# ---- her answers to the follow-ups ----------------------------------------------------------------


def answer_follow_ups(
    db: Session, module: TrackModule, answers: list[dict[str, str]], skip: bool, language: str
) -> ModuleReview:
    """One round, never blocking. A chip must belong to its question; a free answer is masked and short."""
    row = db.get(ModuleReview, module.id)
    if row is None or row.status != "asked":
        raise service.ModulesError("no_questions", "There are no questions to answer.")
    if skip:
        row.status = "skipped"
        db.commit()
        return row
    asked = {f["id"]: f for f in row.follow_ups}
    kept: list[dict[str, Any]] = []
    for a in answers[:MAX_FOLLOW_UPS]:
        q = asked.get(a.get("id", ""))
        if q is None:
            raise service.ModulesError("bad_answer", "That question was not asked.")
        if q["kind"] == "bank":
            chips = vocab()["follow_up_bank"][q["id"]]["chips"]
            if a.get("chip") not in chips:
                raise service.ModulesError("bad_answer", "Choose one of the answers.")
            kept.append({"id": q["id"], "chip": a["chip"]})
        else:
            text = mask_personal((a.get("text") or "").strip()[:MAX_ANSWER_CHARS]).text
            kept.append({"id": q["id"], "text": text})
    row.answers, row.status = kept, "answered"
    db.commit()
    return row


# ---- what code does with the tags -----------------------------------------------------------------


@dataclass(frozen=True)
class Prefs:
    approaches: tuple[str, ...] = ()
    sections: tuple[str, ...] = ()
    barrier: tuple[str, ...] = ()
    focus: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.approaches or self.sections)


def prefs_for(db: Session, module: TrackModule | None) -> Prefs:
    """Preferences from the review of the module before the one being made. Empty when there is no
    review, it was a safety case, or no tag matches the library: the branch default stands."""
    if module is None:
        return Prefs()
    row = db.get(ModuleReview, module.id)
    if row is None or row.safety or not row.focus_tags:
        return Prefs()
    eff = vocab()["focus_effects"]
    approaches: list[str] = []
    sections: list[str] = []
    for tag in row.focus_tags:
        for a in eff.get(tag, {}).get("approaches", []):
            if a not in approaches:
                approaches.append(a)
        for s in eff.get(tag, {}).get("sections", []):
            if s not in sections:
                sections.append(s)
    return Prefs(tuple(approaches), tuple(sections), tuple(row.barrier_tags), tuple(row.focus_tags))


def tag_label(kind: str, tag: str, language: str) -> str:
    entry = vocab()[kind].get(tag, {})
    return str(entry.get(language) or entry.get("en") or tag)


def changes_line(prefs: Prefs, language: str, approach_changed: bool = False) -> str:
    """ "What changes next", written by code from the validated tags (no AI text)."""
    if not prefs:
        return strings.text(language, "module.changed.none")
    told = ", ".join(tag_label("barrier_tags", t, language) for t in prefs.barrier) or ", ".join(
        tag_label("focus_tags", t, language) for t in prefs.focus
    )
    first = ", ".join(strings.text(language, f"module.part.{s}") for s in prefs.sections[:2])
    parts = [strings.text(language, "module.changed.sections", told=told, sections=first)]
    if approach_changed:
        parts.append(strings.text(language, "module.changed.approach"))
    return " ".join(parts)


# ---- the view -------------------------------------------------------------------------------------


def view(db: Session, module: TrackModule, language: str) -> dict[str, Any]:
    row = db.get(ModuleReview, module.id)
    if row is None:
        return {"state": "none", "follow_ups": [], "safety": False, "changes": None}
    qs: list[dict[str, Any]] = []
    for f in row.follow_ups if row.status == "asked" else []:
        if f["kind"] == "bank":
            b = vocab()["follow_up_bank"][f["id"]]
            qs.append(
                {
                    "id": f["id"],
                    "kind": "bank",
                    "text": b["text"].get(language) or b["text"]["en"],
                    "chips": [
                        {"id": c, "label": lab.get(language) or lab["en"]}
                        for c, lab in b["chips"].items()
                    ],
                }
            )
        else:
            qs.append({"id": f["id"], "kind": "free", "text": f["text"], "chips": []})
    prefs = prefs_for(db, module)
    return {
        "state": row.status,
        "follow_ups": qs,
        "safety": row.safety,
        "changes": changes_line(prefs, language) if row.status != "safety" else None,
    }
