"""Rule versions, papers and their approval, in the database.

Rules: a change is a new version (draft -> in_review -> published -> retired). Only its author
submits it; a second person publishes it; a published version never changes (models.py guards).
Papers: built by code from a published version. A paper that passes every automatic check, uses
only published rules, has no custom edits and is in reviewed words is auto-approved and logged;
one in five of those (PAPER_SPOT_CHECK_EVERY) is also queued for a spot check after the fact.
Anything else waits in the review queue before it can be printed. A paper is frozen when the first
sheet of its check is entered, and a pre-test's post-test twin is frozen when it is made.
"""

from __future__ import annotations

import dataclasses
import hashlib
import os
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, object_session

from services.papers import explain, render, verifier
from services.papers import generator as gen
from services.papers.models import (
    BlueprintRow,
    BlueprintSlot,
    ClassProfileRow,
    PaperEvent,
    PaperItemRow,
    PaperReview,
    PaperRow,
    RuleBug,
    RuleTemplate,
    RuleVersion,
    StringPackRow,
)
from services.papers.rules import (
    LAYOUTS,
    RuleSet,
    diff,
    from_data,
    from_yaml,
    rules_hash,
    seed_rules,
    to_data,
)

SEED_AUTHOR = "seed: engine/bugs.py and the pilot test pack"
SEED_APPROVER = "pilot test pack (team-approved, 16 Oct)"
PRINTABLE = ("auto_approved", "approved")


class NotAllowed(Exception):
    """This person may not do this (author approving their own change, a retired version)."""


class BadState(Exception):
    """Not in a state where this can happen (a draft published, a failing paper approved)."""


def _now() -> datetime:
    return datetime.now(UTC)


def _event(db: Session, event: str, actor: str, paper: PaperRow | None = None, **kw: Any) -> None:
    if paper is not None:
        kw = {
            "paper_id": paper.id,
            "class_id": paper.class_id,
            "check_id": paper.check_id,
            "blueprint": paper.blueprint,
            "rules_version": paper.rules_version,
            "seed": paper.seed,
            "hash": paper.hash,
            **kw,
        }
    db.add(PaperEvent(event=event, actor=actor, **kw))


# --- rules ---------------------------------------------------------------------------------


def _write_rows(db: Session, number: int, rules: RuleSet) -> None:
    for t in rules.templates:
        db.add(
            RuleTemplate(
                rule_version=number,
                template_id=t.id,
                competency=t.competency,
                skill=t.skill,
                operation=t.operation,
                digit_pattern=t.digit_pattern,
                range_lo=t.number_range[0],
                range_hi=t.number_range[1],
                box_format=t.answer_format,
                constraints=t.constraints,
                bugs=t.bugs,
                difficulty=t.difficulty,
                retired=t.retired,
            )
        )
    for b in rules.bugs:
        db.add(
            RuleBug(
                rule_version=number,
                bug_id=b.id,
                error_codes=b.counts_for,
                fn=b.fn,
                params=b.params,
                tracked=b.tracked,
            )
        )
    for bp in rules.blueprints:
        db.add(
            BlueprintRow(
                rule_version=number,
                blueprint_id=bp.id,
                title=bp.title,
                adaptive_count=bp.adaptive_count,
                coverage_min=bp.coverage_min,
                coverage_codes=bp.coverage_codes,
                adaptive_templates=dict(bp.adaptive_templates),
            )
        )
        for s in bp.slots:
            db.add(
                BlueprintSlot(
                    rule_version=number,
                    blueprint_id=bp.id,
                    n=s.n,
                    section=s.section,
                    kind=s.kind,
                    template_id=s.template,
                    difficulty=s.difficulty,
                )
            )
    for p in rules.string_packs:
        db.add(
            StringPackRow(
                rule_version=number,
                lang=p.lang,
                strings=p.strings,
                source=p.source,
                reviewed_by=p.reviewed_by,
            )
        )


def _upgrade_columns(db: Session) -> None:
    """A database made before 30 Oct has rule_template.answer_format; the column is box_format now.
    There are no migrations yet (create_all never changes a table), so rename it once here."""
    from sqlalchemy import inspect, text

    bind = db.get_bind()
    insp = inspect(bind)
    if not insp.has_table("rule_template"):
        return
    cols = {c["name"] for c in insp.get_columns("rule_template")}
    if "answer_format" in cols and "box_format" not in cols:
        db.execute(text("ALTER TABLE rule_template RENAME COLUMN answer_format TO box_format"))
        db.commit()


def ensure_seeded(db: Session) -> int:
    """Version 1: the engine's error functions and the pilot pack's items, as the team approved
    them for the pilot. Returns the number of the latest published version."""
    _upgrade_columns(db)
    if db.get(RuleVersion, 1) is None:
        rules = seed_rules()
        db.add(
            RuleVersion(
                number=1,
                status="published",
                author=SEED_AUTHOR,
                approver=SEED_APPROVER,
                body=to_data(rules),
                body_hash=rules_hash(rules),
                diff=diff(None, rules),
                note="Seeded from the pilot. The Hindi and Tamil wording waits for a reader of "
                "each language.",
                submitted_at=_now(),
                published_at=_now(),
            )
        )
        db.flush()
        _write_rows(db, 1, rules)
        db.commit()
    return published(db).number


def published(db: Session) -> RuleVersion:
    v = db.scalars(
        select(RuleVersion)
        .where(RuleVersion.status == "published")
        .order_by(RuleVersion.number.desc())
    ).first()
    if v is None:
        raise BadState("no published rules version")
    return v


def version(db: Session, number: int) -> RuleVersion:
    v = db.get(RuleVersion, number)
    if v is None:
        raise KeyError(f"no rules version {number}")
    return v


def create_draft(db: Session, body: dict[str, Any], author: str, note: str = "") -> RuleVersion:
    rules = from_data(body)  # schema and references validated; raises ValueError
    parent = published(db)
    number = (db.scalar(select(func.max(RuleVersion.number))) or 0) + 1
    v = RuleVersion(
        number=number,
        status="draft",
        author=author,
        parent=parent.number,
        body=to_data(rules),
        body_hash=rules_hash(rules),
        diff=diff(from_data(parent.body), rules),
        note=note,
    )
    db.add(v)
    db.flush()
    _event(db, "rules_draft", author, rules_version=number, detail="; ".join(v.diff)[:2000])
    db.commit()
    return v


def import_yaml(db: Session, text: str, author: str) -> RuleVersion:
    return create_draft(db, to_data(from_yaml(text)), author, note="imported from YAML")


def submit(db: Session, number: int, actor: str) -> RuleVersion:
    v = version(db, number)
    if v.author != actor:
        raise NotAllowed("only the author submits a draft for review")
    if v.status != "draft":
        raise BadState(f"version {number} is {v.status}, not a draft")
    v.status, v.submitted_at = "in_review", _now()
    _event(db, "rules_submitted", actor, rules_version=number)
    db.commit()
    return v


def publish(db: Session, number: int, approver: str) -> RuleVersion:
    v = version(db, number)
    if v.status != "in_review":
        raise BadState(f"version {number} is {v.status}; only a version in review is published")
    if v.author == approver:
        raise NotAllowed("the author of a change cannot approve it: a second person publishes")
    v.status, v.approver, v.published_at = "published", approver, _now()
    db.flush()
    _write_rows(db, number, from_data(v.body))
    _event(db, "rules_published", approver, rules_version=number)
    db.commit()
    return v


def return_draft(db: Session, number: int, actor: str, reason: str) -> RuleVersion:
    v = version(db, number)
    if v.status != "in_review":
        raise BadState(f"version {number} is {v.status}")
    if v.author == actor:
        raise NotAllowed("the author cannot review their own change")
    v.status, v.note = "draft", f"Returned by {actor}: {reason}"
    _event(db, "rules_returned", actor, rules_version=number, detail=reason)
    db.commit()
    return v


def retire(db: Session, number: int, actor: str) -> RuleVersion:
    v = version(db, number)
    if v.status != "published":
        raise BadState(f"version {number} is {v.status}; only a published version is retired")
    v.status, v.retired_at = "retired", _now()
    _event(db, "rules_retired", actor, rules_version=number)
    db.commit()
    return v


def usable_rules(db: Session, number: int | None) -> tuple[RuleSet, RuleVersion]:
    v = published(db) if number is None else version(db, number)
    if v.status == "retired":
        raise NotAllowed(f"rules version {v.number} is retired and cannot be used")
    if v.status != "published":
        raise NotAllowed(
            f"rules version {v.number} is a {v.status.replace('_', ' ')} and cannot "
            "be used until a second person publishes it"
        )
    return from_data(v.body), v


# --- papers --------------------------------------------------------------------------------


def _profile(spec: dict[str, Any]) -> gen.Profile:
    lang = spec.get("language", "en")
    match spec.get("source", "baseline"):
        case "past":
            return gen.profile_from_counts(
                {k: int(v) for k, v in (spec.get("counts") or {}).items()},
                int(spec.get("checked") or 0),
                lang,
                spec.get("built_from") or [],
                spec.get("not_assessed") or [],
            )
        case "intake":
            return gen.profile_from_intake(
                spec.get("struggles") or [], spec.get("taught") or [], lang, spec.get("strength")
            )
        case _:
            return gen.baseline_profile(lang)


def _check(spec: dict[str, Any]) -> gen.CheckRef:
    kind = spec.get("kind", "pre")
    if kind not in gen.KIND_CODE:
        raise ValueError(f"no check kind {kind}")
    return gen.CheckRef(
        id=str(spec["id"]),
        kind=kind,
        form=str(spec.get("form", "A")),
        class_label=str(spec.get("class_label", "")).strip()[:20] or "class",
        term=int(spec.get("term", 1)),
    )


def spot_checked(paper_hash: str) -> bool:
    every = int(os.environ.get("PAPER_SPOT_CHECK_EVERY", "5"))
    return every > 0 and int(paper_hash[:8], 16) % every == 0


def _layout_langs(lang: str) -> tuple[str, ...]:
    return render.LAYOUT_LANGS[lang]


def run_checks(
    paper: dict[str, Any], rules: RuleSet, lang: str, twin_source: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """Every automatic check, before anyone sees the paper. Each finding names the rule."""
    found = verifier.verify_items(paper, twin_source)
    packs = {p.lang: p.strings for p in rules.string_packs if p.lang in _layout_langs(lang)}
    found += verifier.verify_strings(packs, verifier.FONTS)
    _, layout_map = render.render_paper(paper, rules, lang)
    found += verifier.verify_layout(layout_map)
    return [dataclasses.asdict(f) for f in found]


def _store(
    db: Session,
    paper: gen.Paper,
    rules: RuleSet,
    rv: RuleVersion,
    lang: str,
    profile: gen.Profile,
    actor: str,
    findings: list[dict[str, Any]],
    twin_of: str | None = None,
    frozen: bool = False,
) -> PaperRow:
    pid = "P-" + hashlib.sha256(f"{paper.check_id}|{paper.hash}".encode()).hexdigest()[:12]
    existing = db.get(PaperRow, pid)
    if existing is not None:
        return existing
    class_id = paper.check_id.split(":", 1)[0]
    prof = ClassProfileRow(
        class_id=class_id,
        source=profile.source,
        skill_weights=profile.weights,
        not_assessed=list(profile.not_assessed),
        language=profile.language,
        strength=profile.strength,
        built_from=list(profile.built_from),
    )
    db.add(prof)
    db.flush()
    unreviewed = [
        p.lang for p in rules.string_packs if p.lang in _layout_langs(lang) and not p.reviewed_by
    ]
    reason = (
        "failed_check"
        if findings
        else "custom"
        if paper.custom
        else "unreviewed_words"
        if unreviewed
        else None
    )
    row = PaperRow(
        id=pid,
        check_id=paper.check_id,
        class_id=class_id,
        check_code=paper.check_code,
        form=paper.form,
        kind=paper.kind,
        seed=paper.seed,
        blueprint=paper.blueprint,
        blueprint_version=rv.number,
        rules_version=rv.number,
        language=lang,
        profile_id=prof.id,
        status="queued" if reason else "auto_approved",
        hash=paper.hash,
        twin_of=twin_of,
        custom=paper.custom,
        findings=findings,
        body=paper.to_dict(),
        approved_by=None if reason else f"auto (rules v{rv.number})",
        approved_at=None if reason else _now(),
        frozen_at=_now() if frozen else None,
    )
    db.add(row)
    for it in paper.items:
        db.add(
            PaperItemRow(
                paper_id=pid,
                n=it.n,
                slot=it.slot,
                template=it.template,
                a=it.a,
                b=it.b,
                correct=it.correct,
                wrong=it.wrong,
                is_anchor=it.is_anchor,
                twin_of=it.twin_of,
            )
        )
    _event(db, "generated", actor, row, detail=f"profile {profile.source}, layout {lang}")
    if reason:
        db.add(PaperReview(paper_id=pid, reason=reason))
        _event(db, "queued", actor, row, detail=reason)
    else:
        _event(db, "auto_approved", "auto", row)
        if spot_checked(paper.hash):
            db.add(PaperReview(paper_id=pid, reason="spot_check"))
            _event(db, "spot_check", "auto", row)
    if frozen:
        _event(db, "frozen", actor, row, detail="post-test twin, frozen when made")
    db.flush()
    return row


def generate(
    db: Session,
    check: dict[str, Any],
    profile: dict[str, Any],
    blueprint: str,
    language: str,
    actor: str,
    rules_version: int | None = None,
    seed: object | None = None,
) -> PaperRow:
    """A paper for a check (and, for a pre-test, its frozen post-test twin)."""
    if language not in LAYOUTS:
        raise ValueError(f"no layout {language}")
    ref = _check(check)
    frozen = db.scalars(
        select(PaperRow).where(PaperRow.check_id == ref.id, PaperRow.frozen_at.is_not(None))
    ).first()
    if frozen is not None:
        raise BadState(f"this check's paper {frozen.id} is frozen: sheets have been entered")
    rules, rv = usable_rules(db, rules_version)
    prof = dataclasses.replace(_profile(profile), language=language)
    paper = gen.generate_paper(ref, prof, rules, blueprint, rv.number, seed or ref.id)
    row = _store(
        db, paper, rules, rv, language, prof, actor, run_checks(paper.to_dict(), rules, language)
    )
    if ref.kind == "pre" and twin_of(db, row.id) is None:
        post = gen.CheckRef(f"{ref.id}#post", "post", "B", ref.class_label, ref.term + 1)
        twin = gen.make_twin(paper, rules, post, f"{paper.seed}#post")
        _store(
            db,
            twin,
            rules,
            rv,
            language,
            prof,
            actor,
            run_checks(twin.to_dict(), rules, language, paper.to_dict()),
            twin_of=row.id,
            frozen=True,
        )
    db.commit()
    return row


def sample_paper(
    db: Session, check: dict[str, Any], form: str, actor: str, language: str = "en"
) -> PaperRow:
    """The sample paper: the published pilot-test numbers (the pre-test, or its post-test twin)
    as a stored paper on version 1. It is chosen and keyed like any paper; the judge's sample
    sheets and photos were made on these numbers."""
    if language not in LAYOUTS:
        raise ValueError(f"no layout {language}")
    rules, rv = usable_rules(db, 1)
    ref = _check({**check, "form": form, "kind": "pre" if form == "A" else "post"})
    paper = gen.pilot_paper(ref, rules, rv.number, form)
    twin_src = gen.pilot_paper(ref, rules, rv.number, "A").to_dict() if form == "B" else None
    row = _store(
        db,
        paper,
        rules,
        rv,
        language,
        gen.baseline_profile(language),
        actor,
        run_checks(paper.to_dict(), rules, language, twin_src),
    )
    db.commit()
    return row


def twin_of(db: Session, paper_id: str) -> PaperRow | None:
    return db.scalars(select(PaperRow).where(PaperRow.twin_of == paper_id)).first()


def _edited(db: Session, base: PaperRow, edits: list[dict[str, int]]):  # type: ignore[no-untyped-def]
    """The base paper with hand-chosen numbers: every answer, wrong answer and check worked out
    by the generator's own functions. Returns the paper, its findings, the rules and the profile."""
    rules, rv = usable_rules(db, base.rules_version)
    body = base.body
    by_n = {int(e["n"]): (int(e["a"]), int(e.get("b", 0))) for e in edits}
    items = []
    extra: list[dict[str, Any]] = []
    for raw in body["items"]:
        it = gen.PaperItem(**raw)
        if it.n in by_n:
            a, b = by_n[it.n]
            t = rules.template(it.template)
            wrong, untracked, problems = gen.item_answers(rules, t, a, b)
            if not gen._fits(t, a, b):  # noqa: SLF001
                extra.append(
                    {
                        "rule": "constraints",
                        "item": it.n,
                        "detail": f"{a}, {b} do not fit {t.id}: {t.digit_pattern}",
                    }
                )
            it = dataclasses.replace(
                it,
                a=a,
                b=b,
                correct=gen._correct(t.operation, a, b),  # noqa: SLF001
                wrong=wrong,
                untracked=untracked,
                difficulty=gen._difficulty(t, a, b),  # noqa: SLF001
            )
        items.append(it)
    fields = {k: v for k, v in body.items() if k not in ("items", "hash")}
    fields["items"] = tuple(items)
    fields["custom"] = True
    fields["seed"] = (
        body["seed"] if str(body["seed"]).endswith("+custom") else f"{body['seed']}+custom"
    )
    fields["not_assessed"] = tuple(fields["not_assessed"])
    paper = gen._with_hash(gen.Paper(**fields))  # noqa: SLF001
    prof = gen.Profile(
        **{
            **body["profile"],
            "not_assessed": tuple(body["profile"]["not_assessed"]),
            "built_from": tuple(body["profile"]["built_from"]),
        }
    )
    findings = run_checks(paper.to_dict(), rules, base.language) + extra
    return paper, findings, rules, rv, prof


def custom_paper(db: Session, base_id: str, edits: list[dict[str, int]], actor: str) -> PaperRow:
    """An exception: a paper with hand-chosen numbers, as a new paper, always reviewed."""
    base = db.get(PaperRow, base_id)
    if base is None:
        raise KeyError(base_id)
    paper, findings, rules, rv, prof = _edited(db, base, edits)
    row = _store(db, paper, rules, rv, base.language, prof, actor, findings)
    db.commit()
    return row


def edit_in_place(db: Session, paper_id: str, edits: list[dict[str, int]], actor: str) -> PaperRow:
    """Change the numbers of a paper nobody has used, in the same paper: no copy. Hand-chosen
    numbers are always reviewed by a person, so the paper goes back to the review queue and cannot
    be printed until a reviewer approves it. A frozen paper does not change."""
    row = db.get(PaperRow, paper_id)
    if row is None:
        raise KeyError(paper_id)
    if row.frozen_at is not None:
        raise BadState("a frozen paper cannot change")
    paper, findings, _rules, _rv, _prof = _edited(db, row, edits)
    row.body = paper.to_dict()
    row.hash = paper.hash
    row.seed = paper.seed
    row.custom = True
    row.findings = findings
    row.status, row.approved_by, row.approved_at, row.rejected_reason = "queued", None, None, None
    for old in db.scalars(select(PaperItemRow).where(PaperItemRow.paper_id == row.id)).all():
        db.delete(old)
    db.flush()
    for it in paper.items:
        db.add(
            PaperItemRow(
                paper_id=row.id,
                n=it.n,
                slot=it.slot,
                template=it.template,
                a=it.a,
                b=it.b,
                correct=it.correct,
                wrong=it.wrong,
                is_anchor=it.is_anchor,
                twin_of=it.twin_of,
            )
        )
    _close(db, row.id, "superseded", actor, "numbers changed")
    reason = "failed_check" if findings else "custom"
    db.add(PaperReview(paper_id=row.id, reason=reason))
    _event(db, "edited", actor, row, detail=f"{len(edits)} item(s) changed in place; {reason}")
    db.flush()
    db.commit()
    return row


def imported(row: PaperRow) -> bool:
    return (row.body or {}).get("source") == "imported_pdf"


def printable(row: PaperRow) -> bool:
    """Approved papers the system made. An imported paper is already printed: never printed here."""
    return row.status in PRINTABLE and not imported(row)


def usable(row: PaperRow) -> bool:
    """A paper a check may use: printable, or an imported paper a teacher confirmed (or a reviewer
    approved)."""
    return printable(row) or (imported(row) and row.status in ("confirmed", "approved"))


def _close(db: Session, paper_id: str, decision: str, actor: str, note: str | None) -> None:
    for q in db.scalars(
        select(PaperReview).where(PaperReview.paper_id == paper_id, PaperReview.status == "open")
    ):
        q.status, q.decision, q.decided_by, q.decided_at, q.note = (
            "done",
            decision,
            actor,
            _now(),
            note,
        )


def approve_paper(db: Session, paper_id: str, actor: str) -> PaperRow:
    row = db.get(PaperRow, paper_id)
    if row is None:
        raise KeyError(paper_id)
    if row.findings:
        raise BadState(
            "this paper failed an automatic check and cannot be approved: "
            + "; ".join(f"{f['rule']}: {f['detail']}" for f in row.findings[:3])
        )
    if row.status == "auto_approved":  # a spot check: it stays approved
        _close(db, paper_id, "ok", actor, None)
        _event(db, "spot_check_ok", actor, row)
    elif row.status == "confirmed" and imported(row):
        if (row.body or {}).get("imported_by") == actor:
            raise BadState(
                "an imported paper is reviewed by someone else, never by the person who imported it"
            )
        row.status, row.approved_by, row.approved_at = "approved", actor, _now()
        _close(db, paper_id, "approved", actor, None)
        _event(db, "approved", actor, row, detail="imported paper confirmed by a reviewer")
    elif row.status == "queued":
        row.status, row.approved_by, row.approved_at = "approved", actor, _now()
        _close(db, paper_id, "approved", actor, None)
        _event(db, "approved", actor, row)
    else:
        raise BadState(f"paper {paper_id} is {row.status}")
    db.commit()
    return row


def reject_paper(db: Session, paper_id: str, actor: str, reason: str) -> PaperRow:
    row = db.get(PaperRow, paper_id)
    if row is None:
        raise KeyError(paper_id)
    if not reason.strip():
        raise ValueError("say why the paper is rejected")
    if row.frozen_at is not None:
        raise BadState("a frozen paper cannot be rejected: its sheets are in")
    row.status, row.rejected_reason = "rejected", reason.strip()
    _close(db, paper_id, "rejected", actor, reason.strip())
    _event(db, "rejected", actor, row, detail=reason.strip())
    db.commit()
    return row


def freeze(db: Session, paper_id: str, actor: str) -> PaperRow:
    """The first sheet of the check is in: the paper can no longer change."""
    row = db.get(PaperRow, paper_id)
    if row is None:
        raise KeyError(paper_id)
    if row.frozen_at is None:
        if not usable(row):
            raise BadState("only an approved paper is used for a check")
        row.frozen_at = _now()
        _event(db, "frozen", actor, row, detail="first sheet entered")
        db.commit()
    elif not db.scalars(
        select(PaperEvent).where(
            PaperEvent.paper_id == row.id,
            PaperEvent.event == "frozen",
            PaperEvent.detail == "first sheet entered",
        )
    ).first():
        # frozen when made (a post-test twin): the first sheet entered on it is still recorded,
        # so the paper is known to be in use
        _event(db, "frozen", actor, row, detail="first sheet entered")
        db.commit()
    return row


def phone_key(row: PaperRow) -> dict[str, Any]:
    """The paper's answer key in the shape the phone diagnoses with (generated/answer_keys.json),
    plus which items are anchors. Built by the engine, so the phone only looks answers up."""
    from engine.export_keys import _item_key
    from engine.model import Form, Item, ItemType

    def item_type(it: dict[str, Any]) -> ItemType:
        if it["operation"] == "dictate":
            return ItemType.DICTATION
        if it["operation"] == "add":
            return ItemType.ADD_CARRY
        return ItemType.SUB_BORROW if it["a"] % 10 < it["b"] % 10 else ItemType.SUB_ANCHOR

    body = row.body
    form = Form(
        row.check_code,
        tuple(Item(it["n"], item_type(it), it["a"], it["b"]) for it in body["items"]),
    )
    items = []
    for i, it in enumerate(body["items"]):
        key = _item_key(form, i)
        key.update(anchor=it["is_anchor"], slot=it["slot"], twin_of=it["twin_of"])
        items.append(key)
    return {
        "label": row.check_code,
        "paper_id": row.id,
        "hash": row.hash,
        "form": row.form,
        "not_assessed": body["not_assessed"],
        "items": items,
    }


_SKILLS: dict[str, dict[str, str]] = {}


def template_skills(row: PaperRow) -> dict[str, str]:
    """Template id -> its description, from the rules version this paper was made from. A published
    version never changes, so the answer is kept by the version's hash."""
    db = object_session(row)
    if db is None or row.rules_version is None:
        return {}
    v = db.scalar(select(RuleVersion).where(RuleVersion.number == row.rules_version))
    if v is None:
        return {}
    if v.body_hash not in _SKILLS:
        _SKILLS[v.body_hash] = {t.id: t.skill for t in from_data(v.body).templates}
    return _SKILLS[v.body_hash]


def summary(row: PaperRow) -> dict[str, Any]:
    body = row.body
    return {
        "id": row.id,
        "check_id": row.check_id,
        "check_code": row.check_code,
        "form": row.form,
        "kind": row.kind,
        "language": row.language,
        "status": row.status,
        "printable": printable(row),
        "frozen": row.frozen_at is not None,
        "custom": row.custom,
        "blueprint": row.blueprint,
        "rules_version": row.rules_version,
        "seed": row.seed,
        "hash": row.hash,
        "twin_of": row.twin_of,
        "profile_source": body["profile"]["source"],
        "not_assessed": body["not_assessed"],
        "coverage": body["coverage"],
        "items": explain.attach(body, template_skills(row)),
        "findings": row.findings,
        "approved_by": row.approved_by,
        "rejected_reason": row.rejected_reason,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
