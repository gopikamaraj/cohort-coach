"""Answer one question inside one scope: pre-written, extracted, model-written, or no answer.

* A suggested question (an id in the role's bank) gets a pre-written answer built by code at deploy
  time from the rubric rows and the role's help pages. It needs no network and no model.
* Typed text is masked (names, roll numbers, phones, emails), searched inside the scope, and, when
  the deployment has a live model and the caps allow, answered by call 14. Code then checks every
  quote and rubric row. If the model is off, over a cap, or fails the checks twice, the answer is an
  extract from the best passage. If nothing is found, the assistant says so and says where to look.
* Every status label, how-to-check line and limit comes from docs/RUBRIC_MAP.md through code, never
  from the model, and a status is never stronger than the row's.
* The assistant is read-only and states nothing it cannot cite.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

from ai import config
from ai.calls import c14_assistant_answer as c14
from ai.client import CallContext
from ai.schemas import AssistantAnswer
from ai.validators.mask import mask_personal
from services.assistant import cite, guard, limits, questions, retrieve
from services.assistant.index import INDEX_DIR, Chunk
from services.assistant.scopes import Scope

log = logging.getLogger("assistant")

MAX_QUESTION_CHARS = 500
EXTRACT_WORDS = 90
MAX_FOLLOW_UPS = 3
OFFLINE_LABEL = {
    "en": "pre-written from the docs",
    "hi": "दस्तावेज़ों से पहले से लिखा गया",
    "ta": "ஆவணங்களிலிருந்து முன்கூட்டியே எழுதப்பட்டது",
}
EXTRACT_LABEL = {
    "en": "an extract from the docs, not written by a model",
    "hi": "दस्तावेज़ों का अंश, किसी मॉडल ने नहीं लिखा",
    "ta": "ஆவணங்களிலிருந்து எடுத்த பகுதி, மாதிரி எழுதியது அல்ல",
}
ENGLISH_PAGES = {
    "en": "",
    "hi": "ये सहायता पन्ने अभी अंग्रेज़ी में हैं; हिंदी की समीक्षा बाकी है।",
    "ta": "இந்த உதவிப் பக்கங்கள் இப்போது ஆங்கிலத்தில் உள்ளன; தமிழ் மதிப்பாய்வு நிலுவையில் உள்ளது.",
}
CAN_PREFIX = {
    "en": "I can help with:",
    "hi": "मैं इनमें मदद कर सकता हूँ:",
    "ta": "நான் இவற்றில் உதவ முடியும்:",
}
CANNOT = {
    "en": "I can't answer that from the pages I can read.",
    "hi": "मैं अपने पढ़ने योग्य पन्नों से इसका उत्तर नहीं दे सकता।",
    "ta": "நான் படிக்கக்கூடிய பக்கங்களிலிருந்து இதற்குப் பதில் சொல்ல முடியாது.",
}
WHERE = {
    "teacher": {
        "en": "Ask your mentor in the cohort chat, or open the screen the question is about.",
        "hi": "अपने मेंटर से कोहॉर्ट चैट में पूछें, या जिस स्क्रीन के बारे में सवाल है उसे खोलें।",
        "ta": "உங்கள் வழிகாட்டியிடம் குழு அரட்டையில் கேளுங்கள், அல்லது கேள்விக்குரிய திரையைத் திறங்கள்.",
    },
    "mentor": {
        "en": "Ask your coach.",
        "hi": "अपने कोच से पूछें।",
        "ta": "உங்கள் பயிற்சியாளரிடம் கேளுங்கள்.",
    },
    "coach": {
        "en": "Ask the programme officer, or open the screen the question is about.",
        "hi": "कार्यक्रम अधिकारी से पूछें, या जिस स्क्रीन के बारे में सवाल है उसे खोलें।",
        "ta": "திட்ட அதிகாரியிடம் கேளுங்கள், அல்லது கேள்விக்குரிய திரையைத் திறங்கள்.",
    },
    "officer": {"en": "Ask the Cohort Coach team, or read the programme help page."},
    "judge": {
        "en": "Try one of the suggested questions, or read docs/RUBRIC_MAP.md and the README."
    },
}
DIFFERS_NOTE = "The deck or video wording for this row differs from the rubric map; the stricter status is shown."
SOURCE_ORDER = {"slide": 0, "video": 1, "file": 2}


@dataclass
class Answer:
    answer: str
    status_labels: list[dict[str, Any]] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
    how_to_check: str = ""
    limits: str = ""
    abstained: bool = False
    mode: str = "curated"  # curated, extract, model or abstain
    role: str = ""
    scope: str = ""
    question_id: str | None = None
    label: str | None = None  # "pre-written from the docs" and the like
    notes: list[str] = field(default_factory=list)
    commit: str | None = None
    provisional: bool = False  # slide numbers and video times are not final yet
    capped: str | None = None
    follow_ups: list[dict[str, Any]] = field(
        default_factory=list
    )  # {text, id|None}: what to ask next

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Library:
    rows: dict[str, dict[str, Any]]
    submission: dict[str, Any]
    banks: dict[str, list[questions.Question]]
    path: dict[str, Any]
    curated: dict[str, dict[str, dict[str, Any]]]
    meta: dict[str, Any]
    index_dir: Path = INDEX_DIR


@cache
def library(index_dir: Path = INDEX_DIR) -> Library:
    def load(name: str, default: Any) -> Any:
        f = index_dir / f"{name}.json"
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else default

    raw = load("questions", {})
    return Library(
        rows={r["id"]: r for r in load("rubric", [])},
        submission=load("submission", {}),
        banks={k: questions.parse_bank(v) for k, v in raw.items() if isinstance(v, list)},
        path=raw.get("judge_path", {}),
        curated=load("curated", {}),
        meta=load("META", {}),
        index_dir=index_dir,
    )


def reload() -> None:
    library.cache_clear()
    retrieve.reload()


def commit_sha(lib: Library) -> str | None:
    return os.environ.get("GIT_SHA") or lib.meta.get("source_commit")


def _lang(scope: Scope, lang: str) -> str:
    return lang if scope.answers_in == "own" and lang in ("en", "hi", "ta") else "en"


# ---------------------------------------------------------------------------------------------
# Rubric rows


def row_text(r: dict[str, Any]) -> str:
    return f"{r['claim']} Status: {r['status']}. Known limit: {r['limit']}"


def search_rows(lib: Library, query: str, k: int = 4) -> list[dict[str, Any]]:
    q = list(dict.fromkeys(retrieve.tokens(query)))
    if not q:
        return []
    need = 2 if len(q) >= 2 else 1
    scored: list[tuple[int, str, dict[str, Any]]] = []
    for r in lib.rows.values():
        bag = set(
            retrieve.tokens(" ".join((r["claim"], r["feature"], r["bullet"], r["criterion"])))
        )
        m = sum(1 for t in q if t in bag)
        if m >= need:
            scored.append((-m, r["id"], r))
    scored.sort(key=lambda s: (s[0], s[1]))
    return [r for *_, r in scored[:k]]


def status_labels(lib: Library, ids: list[str]) -> list[dict[str, Any]]:
    return [
        {"row": i, "status": r["status"], "feature": r["feature"], "differs": bool(r["differs"])}
        for i in ids
        if (r := lib.rows.get(i))
    ]


def check_line(lib: Library, ids: list[str]) -> str:
    parts: list[str] = []
    tests: list[str] = []
    reads: list[str] = []
    for i in ids:
        r = lib.rows.get(i)
        if not r:
            continue
        parts.append(f"{i}: {r['demo']}")
        for t in r["tests"]:
            (tests if t.startswith("tests/") else reads).append(t)
    if tests:
        parts.append("Run: python -m pytest " + " ".join(dict.fromkeys(tests)))
    if reads:
        parts.append("Read: " + ", ".join(dict.fromkeys(reads)))
    return " ".join(parts)


def limit_line(lib: Library, ids: list[str]) -> str:
    said = [
        f"{i}: {lib.rows[i]['limit']}"
        for i in ids
        if i in lib.rows and lib.rows[i]["limit"] not in ("", "—")
    ]
    if said:
        return " ".join(said)
    return "No known limit is recorded for " + ", ".join(ids) + " in the rubric map."


def sentence(r: dict[str, Any]) -> str:
    """One row as a sentence that cannot be read as stronger than it is: the status comes first, and a
    row that is not fully built says what is missing."""
    s = f"{r['status']}: {r['claim']}"
    if r["status"] != "Built" and r["limit"] not in ("", "—"):
        s += f" What is missing: {r['limit']}"
    return s


def path_citation(path: str, sha: str | None) -> dict[str, Any]:
    kind = "blob" if "." in path.rsplit("/", 1)[-1] else "tree"
    return {
        "type": "file",
        "id": f"file:{path}",
        "label": path,
        "path": path,
        "heading": None,
        "line": None,
        "url": f"{cite.REPO_URL}/{kind}/{sha or 'main'}/{path}",
    }


def row_sources(lib: Library, r: dict[str, Any], sha: str | None) -> list[dict[str, Any]]:
    out = [cite.slide_citation(n, lib.submission, sha) for n in r["slides"]]
    out += [cite.video_citation(t, lib.submission) for t in r["video"]]
    out += [path_citation(p, sha) for p in r["code"][:2]]
    return out


def tidy(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One of each: a page and heading shown once however many of its passages were used."""
    seen: dict[str, dict[str, Any]] = {}
    for s in sources:
        key = s["id"] if s["type"] != "file" else f"{s.get('path')}#{s.get('heading')}"
        seen.setdefault(key, s)
    return sorted(seen.values(), key=lambda s: SOURCE_ORDER[s["type"]])  # stable within a type


def first_words(text: str, n: int = EXTRACT_WORDS) -> str:
    w = text.split()
    return text if len(w) <= n else " ".join(w[:n]).rstrip(",;:") + " ..."


# ---------------------------------------------------------------------------------------------
# The kinds of answer


def _base(scope: Scope, lib: Library, lang: str, question_id: str | None) -> Answer:
    return Answer(
        answer="",
        role=scope.role,
        scope=scope.role,
        question_id=question_id,
        commit=commit_sha(lib),
        provisional=bool(lib.submission.get("provisional", True)),
    )


def abstain(
    scope: Scope, lib: Library, lang: str, question_id: str | None = None, capped: str | None = None
) -> Answer:
    lg = _lang(scope, lang)
    where = WHERE[scope.role].get(lg) or WHERE[scope.role]["en"]
    a = _base(scope, lib, lg, question_id)
    a.answer = f"{CANNOT[lg]} {CAN_PREFIX[lg]} {scope.line('can', lg)} {where}"
    a.abstained, a.mode, a.capped = True, "abstain", capped
    a.limits = scope.line("cannot", lg)
    return a


def from_rows(
    scope: Scope,
    lib: Library,
    rows: list[dict[str, Any]],
    q: questions.Question | None,
    query: str,
    lang: str,
) -> Answer:
    sha = commit_sha(lib)
    ids = [r["id"] for r in rows]
    a = _base(scope, lib, lang, q.id if q else None)
    a.answer = " ".join(sentence(r) for r in rows)
    a.status_labels = status_labels(lib, ids)
    sources = [s for r in rows for s in row_sources(lib, r, sha)]
    for hit in retrieve.search(scope, query, k=1, index_dir=lib.index_dir):
        sources.append(cite.file_citation(hit.chunk, sha))
    a.sources = tidy(sources)
    a.how_to_check = check_line(lib, ids)
    a.limits = limit_line(lib, ids)
    if any(r["differs"] for r in rows):
        a.notes.append(DIFFERS_NOTE)
    return a


def from_passages(
    scope: Scope, lib: Library, query: str, lang: str, q: questions.Question | None
) -> Answer | None:
    sha = commit_sha(lib)
    hits = retrieve.search(scope, query, k=2, index_dir=lib.index_dir)
    if not hits:
        return None
    top = hits[0].chunk
    a = _base(scope, lib, lang, q.id if q else None)
    a.answer = first_words(top.text)
    a.sources = tidy([cite.file_citation(h.chunk, sha) for h in hits])
    a.how_to_check = (
        f"Open {top.path}"
        + (f", section {cite.short_heading(top.heading)}" if top.heading else "")
        + "."
    )
    a.limits = (
        "Extracted word for word from the page above; related pages may say more. "
        "Help pages describe what is built, and say where something is not."
    )
    note = ENGLISH_PAGES.get(_lang(scope, lang), "")
    if note:
        a.notes.append(note)
    return a


def curated(scope: Scope, lib: Library, q: questions.Question, lang: str) -> Answer:
    """The pre-written answer to a suggested question, built by code from the rubric and the help pages."""
    rows = [lib.rows[i] for i in q.rubric_rows if i in lib.rows]
    a = (
        from_rows(scope, lib, rows, q, q.query, lang)
        if rows
        else from_passages(scope, lib, q.query, lang, q)
    )
    if a is None:
        return abstain(scope, lib, lang, q.id)
    a.mode, a.label = "curated", OFFLINE_LABEL[_lang(scope, lang)]
    return a


def build_curated(scope: Scope, lib: Library) -> dict[str, dict[str, Any]]:
    """Every suggested answer for a scope, as plain data (written into the bundle at deploy time)."""
    return {q.id: curated(scope, lib, q, "en").to_dict() for q in lib.banks.get(scope.role, [])}


# ---------------------------------------------------------------------------------------------
# Free text


def _model_available(ctx: CallContext | None) -> bool:
    if ctx is not None:
        return True
    return config.ai_mode() == "live" and bool(os.environ.get("ANTHROPIC_API_KEY"))


def follow_ups_for(
    scope: Scope,
    lib: Library,
    lang: str,
    asked: str,
    asked_id: str | None,
    answer_text: str,
    suggested: list[str],
) -> list[dict[str, Any]]:
    """Up to three next questions, every one of them answerable. The model's own suggestions are kept
    only if they pass the policy refusals and the pages in this scope can answer them; the rest are
    filled from the role's own question bank, ranked by words shared with this exchange. A bank
    question has an id, so its answer is the pre-written one."""
    lg = _lang(scope, lang)
    out: list[dict[str, Any]] = []
    seen = {asked.strip().lower()}
    for s in suggested:
        t = mask_personal(s[:MAX_QUESTION_CHARS]).text.strip()
        if not t or t.lower() in seen or guard.refusal(t):
            continue
        if not retrieve.search(scope, t, k=1, index_dir=lib.index_dir):
            continue
        seen.add(t.lower())
        out.append({"text": t, "id": None})
    bank = [q for q in lib.banks.get(scope.role, []) if q.id != asked_id]
    have = set(retrieve.tokens(f"{asked} {answer_text}"))
    ranked = sorted(
        enumerate(bank),
        key=lambda iq: (
            -len(have & set(retrieve.tokens(iq[1].query + " " + iq[1].text["en"]))),
            iq[0],
        ),
    )
    for _, q in ranked:
        if len(out) >= MAX_FOLLOW_UPS:
            break
        label = q.label(lg)
        if label.lower() not in seen:
            seen.add(label.lower())
            out.append({"text": label, "id": q.id})
    return out[:MAX_FOLLOW_UPS]


def _try_model(
    scope: Scope,
    lib: Library,
    text: str,
    lang: str,
    hits: list[retrieve.Hit],
    rows: list[dict[str, Any]],
    ctx: CallContext | None,
    session: str,
    caps: limits.Caps,
) -> Answer | None:
    caps.check(scope.role, session)  # raises Capped
    passages = [
        c14.Passage(f"S{i}", cite.short_heading(h.chunk.heading) or h.chunk.path, h.chunk.text)
        for i, h in enumerate(hits, 1)
    ]
    passages += [c14.Passage(f"R:{r['id']}", r["feature"], row_text(r)) for r in rows]
    context = ctx or CallContext(judge=config.judge_mode())
    result = c14.answer_question(text, scope.role, lang, passages, context=context)
    caps.record(
        scope.role, session, result.usage.input_tokens, result.usage.output_tokens, result.cost_usd
    )
    out = result.output
    if not result.ok or not isinstance(out, AssistantAnswer) or not (out.answer or "").strip():
        return None
    sha = commit_sha(lib)
    ids = [i for i in dict.fromkeys(out.rubric_rows) if i in lib.rows]
    a = _base(scope, lib, lang, None)
    a.answer, a.mode = (out.answer or "").strip(), "model"
    a.follow_ups = [{"text": f, "id": None} for f in out.follow_ups]  # filtered in ask()
    a.status_labels = status_labels(lib, ids)
    sources: list[dict[str, Any]] = []
    by_alias = {f"S{i}": h.chunk for i, h in enumerate(hits, 1)}
    for c in out.citations:
        if c.source_id in by_alias:
            cit = cite.file_citation(by_alias[c.source_id], sha)
            cit["quote"] = c.quote
            sources.append(cit)
    for i in ids:
        sources += row_sources(lib, lib.rows[i], sha)
    a.sources = tidy(sources)
    if ids:
        a.how_to_check, a.limits = check_line(lib, ids), limit_line(lib, ids)
        if any(lib.rows[i]["differs"] for i in ids):
            a.notes.append(DIFFERS_NOTE)
    else:
        top = hits[0].chunk if hits else None
        a.how_to_check = f"Open {top.path}." if top else ""
        a.limits = "Written by a model from the pages cited; every quote was checked word for word."
    return a


def free_text(
    scope: Scope,
    lib: Library,
    text: str,
    lang: str,
    ctx: CallContext | None,
    session: str,
    caps: limits.Caps,
) -> Answer:
    masked = mask_personal(text[:MAX_QUESTION_CHARS])
    query = masked.text
    why = guard.refusal(query)
    if why:  # a policy refusal: no search, no source, and it says why
        a = abstain(scope, lib, lang)
        lg = _lang(scope, lang)
        a.answer = f"{guard.REASON[why]} {CAN_PREFIX[lg]} {scope.line('can', lg)}"
        a.notes.append("refused: " + why)
        return a
    hits = retrieve.search(scope, query, k=5, index_dir=lib.index_dir)
    rows = search_rows(lib, query) if scope.role == "judge" else []
    notes = ["Names and numbers were removed from your question."] if masked.kinds else []
    if not hits and not rows:
        a = abstain(scope, lib, lang)
        a.notes += notes
        return a
    a: Answer | None = None
    capped: str | None = None
    if _model_available(ctx):
        try:
            a = _try_model(scope, lib, query, _lang(scope, lang), hits, rows, ctx, session, caps)
        except limits.Capped as e:
            capped = e.which
        except Exception:  # noqa: BLE001  the app never hangs or breaks on a model fault
            log.warning("assistant model call failed role=%s", scope.role)
            a = None
    if a is None:
        a = (
            from_rows(scope, lib, rows[:2], None, query, lang)
            if rows
            else from_passages(scope, lib, query, lang, None)
        )
        if a is None:
            a = abstain(scope, lib, lang)
        else:
            a.mode, a.label = "extract", EXTRACT_LABEL[_lang(scope, lang)]
    a.capped = capped
    a.notes += notes
    return a


# ---------------------------------------------------------------------------------------------
# Entry point


def ask(
    scope: Scope,
    *,
    question_id: str | None = None,
    text: str | None = None,
    lang: str = "en",
    session: str = "anon",
    ctx: CallContext | None = None,
    index_dir: Path = INDEX_DIR,
    caps: limits.Caps = limits.CAPS,
) -> Answer:
    """Answer inside `scope`. The role's own bank decides whether an id exists: another role's id
    is simply unknown here, so it falls through to an abstention."""
    lib = library(index_dir)
    if question_id:
        q = next((x for x in lib.banks.get(scope.role, []) if x.id == question_id), None)
        if q is None:
            a = abstain(scope, lib, lang)
        else:
            pre = lib.curated.get(scope.role, {}).get(q.id)
            if pre is not None:
                a = Answer(**pre)
                a.label = OFFLINE_LABEL[_lang(scope, lang)]
                a.commit = commit_sha(lib)
                if _lang(scope, lang) != "en":
                    note = ENGLISH_PAGES.get(_lang(scope, lang), "")
                    if note and note not in a.notes:
                        a.notes.append(note)
            else:
                a = curated(scope, lib, q, lang)
    elif text and text.strip():
        a = free_text(scope, lib, text.strip(), lang, ctx, session, caps)
    else:
        a = abstain(scope, lib, lang)
    a.follow_ups = follow_ups_for(
        scope, lib, lang, text or "", question_id, a.answer, [f["text"] for f in a.follow_ups]
    )
    # What the log may hold: the effective role, the scope and the question id. Never the text.
    log.info(
        "assistant role=%s scope=%s question=%s mode=%s",
        scope.role,
        scope.role,
        a.question_id or "free",
        a.mode,
    )
    return a


def suggested(
    scope: Scope, screen: str, step: int | None, lang: str, index_dir: Path = INDEX_DIR
) -> list[dict[str, Any]]:
    lib = library(index_dir)
    lg = _lang(scope, lang)
    out = []
    for q in questions.top_five(lib.banks.get(scope.role, []), screen, step):
        out.append(
            {
                "id": q.id,
                "text": q.label(lg),
                "criteria": [questions.CRITERION_LABEL[c] for c in q.criteria]
                if scope.role == "judge"
                else [],
                "criteria_keys": list(q.criteria) if scope.role == "judge" else [],
            }
        )
    return out


def chunk_in_scope(scope: Scope, chunk_id: str, index_dir: Path = INDEX_DIR) -> Chunk | None:
    return retrieve.get_chunk(scope, chunk_id, index_dir)
