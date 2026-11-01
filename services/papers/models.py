"""Paper Studio tables. Class-level data only: no child, name, roll number or answer.

A rule version and its rows never change once published: the guards at the bottom refuse an update
or delete of a published version's body and of any rule row, so a change is always a new version.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, event
from sqlalchemy.orm import Mapped, Mapper, mapped_column
from sqlalchemy.orm.attributes import get_history

from services.api.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Immutable(Exception):
    """A published rule version, or a rule row, was about to change."""


class RuleVersion(Base):
    __tablename__ = "rule_version"

    number: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(12))  # draft | in_review | published | retired
    author: Mapped[str] = mapped_column(String(60))
    approver: Mapped[str | None] = mapped_column(String(60))
    parent: Mapped[int | None] = mapped_column(Integer)
    body: Mapped[dict[str, Any]] = mapped_column(JSON)
    body_hash: Mapped[str] = mapped_column(String(64))
    diff: Mapped[list[str]] = mapped_column(JSON, default=list)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RuleTemplate(Base):
    __tablename__ = "rule_template"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_version: Mapped[int] = mapped_column(ForeignKey("rule_version.number"))
    template_id: Mapped[str] = mapped_column(String(40))
    competency: Mapped[str] = mapped_column(String(4))
    skill: Mapped[str] = mapped_column(Text)
    operation: Mapped[str] = mapped_column(String(10))
    digit_pattern: Mapped[str] = mapped_column(Text)
    range_lo: Mapped[int] = mapped_column(Integer)
    range_hi: Mapped[int] = mapped_column(Integer)
    box_format: Mapped[str] = mapped_column(Text)  # what goes in the box (the rule's answer_format)
    constraints: Mapped[dict[str, Any]] = mapped_column(JSON)
    bugs: Mapped[list[str]] = mapped_column(JSON)
    difficulty: Mapped[str] = mapped_column(String(12))
    retired: Mapped[bool] = mapped_column(Boolean, default=False)


class RuleBug(Base):
    __tablename__ = "rule_bug"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_version: Mapped[int] = mapped_column(ForeignKey("rule_version.number"))
    bug_id: Mapped[str] = mapped_column(String(40))
    error_codes: Mapped[list[str]] = mapped_column(JSON)
    fn: Mapped[str] = mapped_column(String(40))
    params: Mapped[dict[str, Any]] = mapped_column(JSON)
    tracked: Mapped[bool] = mapped_column(Boolean)


class BlueprintRow(Base):
    __tablename__ = "blueprint"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_version: Mapped[int] = mapped_column(ForeignKey("rule_version.number"))
    blueprint_id: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(Text)
    adaptive_count: Mapped[int] = mapped_column(Integer)
    coverage_min: Mapped[int] = mapped_column(Integer)
    coverage_codes: Mapped[list[str]] = mapped_column(JSON)
    adaptive_templates: Mapped[dict[str, Any]] = mapped_column(JSON)


class BlueprintSlot(Base):
    __tablename__ = "blueprint_slot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_version: Mapped[int] = mapped_column(ForeignKey("rule_version.number"))
    blueprint_id: Mapped[str] = mapped_column(String(40))
    n: Mapped[int] = mapped_column(Integer)
    section: Mapped[str] = mapped_column(String(12))
    kind: Mapped[str] = mapped_column(String(10))  # anchor | adaptive
    template_id: Mapped[str | None] = mapped_column(String(40))
    difficulty: Mapped[int | None] = mapped_column(Integer)


class StringPackRow(Base):
    __tablename__ = "string_pack"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_version: Mapped[int] = mapped_column(ForeignKey("rule_version.number"))
    lang: Mapped[str] = mapped_column(String(8))
    strings: Mapped[dict[str, str]] = mapped_column(JSON)
    source: Mapped[str] = mapped_column(Text)
    reviewed_by: Mapped[str] = mapped_column(String(80), default="")


class ClassProfileRow(Base):
    """What a paper was built from: class-level weights only (never a child)."""

    __tablename__ = "class_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    class_id: Mapped[str] = mapped_column(String(40))
    source: Mapped[str] = mapped_column(String(10))  # past | intake | baseline
    skill_weights: Mapped[dict[str, float]] = mapped_column(JSON)
    not_assessed: Mapped[list[str]] = mapped_column(JSON)
    language: Mapped[str] = mapped_column(String(8))
    strength: Mapped[int | None] = mapped_column(Integer)
    built_from: Mapped[list[str]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class PaperRow(Base):
    __tablename__ = "paper"

    id: Mapped[str] = mapped_column(String(24), primary_key=True)
    check_id: Mapped[str] = mapped_column(String(60))
    class_id: Mapped[str] = mapped_column(String(40))
    check_code: Mapped[str] = mapped_column(String(60))
    form: Mapped[str] = mapped_column(String(2))
    kind: Mapped[str] = mapped_column(String(8))
    seed: Mapped[str] = mapped_column(String(80))
    blueprint: Mapped[str] = mapped_column(String(40))
    blueprint_version: Mapped[int] = mapped_column(Integer)
    rules_version: Mapped[int] = mapped_column(ForeignKey("rule_version.number"))
    language: Mapped[str] = mapped_column(String(8))
    profile_id: Mapped[int | None] = mapped_column(ForeignKey("class_profile.id"))
    # draft | auto_approved | queued | approved | rejected (frozen is frozen_at, on top)
    status: Mapped[str] = mapped_column(String(14))
    hash: Mapped[str] = mapped_column(String(64))
    twin_of: Mapped[str | None] = mapped_column(String(24))
    custom: Mapped[bool] = mapped_column(Boolean, default=False)
    findings: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    body: Mapped[dict[str, Any]] = mapped_column(JSON)
    approved_by: Mapped[str | None] = mapped_column(String(60))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_reason: Mapped[str | None] = mapped_column(Text)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class PaperItemRow(Base):
    __tablename__ = "paper_item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paper_id: Mapped[str] = mapped_column(ForeignKey("paper.id"))
    n: Mapped[int] = mapped_column(Integer)
    slot: Mapped[int] = mapped_column(Integer)
    template: Mapped[str] = mapped_column(String(40))
    a: Mapped[int] = mapped_column(Integer)
    b: Mapped[int] = mapped_column(Integer)
    correct: Mapped[int] = mapped_column(Integer)
    wrong: Mapped[dict[str, list[int]]] = mapped_column(JSON)
    is_anchor: Mapped[bool] = mapped_column(Boolean)
    twin_of: Mapped[int | None] = mapped_column(Integer)


class PaperReview(Base):
    """The paper review queue: custom papers and failed checks before printing, and a sample of
    auto-approved papers after the fact (spot checks)."""

    __tablename__ = "review_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paper_id: Mapped[str] = mapped_column(ForeignKey("paper.id"))
    reason: Mapped[str] = mapped_column(
        String(20)
    )  # custom | failed_check | unreviewed_words | spot_check
    status: Mapped[str] = mapped_column(String(8), default="open")  # open | done
    decision: Mapped[str | None] = mapped_column(String(10))  # approved | rejected | ok
    decided_by: Mapped[str | None] = mapped_column(String(60))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PaperEvent(Base):
    """Generation, approval and rule events: class, check, blueprint, versions, seed, hash."""

    __tablename__ = "paper_event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    event: Mapped[str] = mapped_column(String(24))
    actor: Mapped[str] = mapped_column(String(60))
    paper_id: Mapped[str | None] = mapped_column(String(24))
    class_id: Mapped[str | None] = mapped_column(String(40))
    check_id: Mapped[str | None] = mapped_column(String(60))
    blueprint: Mapped[str | None] = mapped_column(String(40))
    rules_version: Mapped[int | None] = mapped_column(Integer)
    seed: Mapped[str | None] = mapped_column(String(80))
    hash: Mapped[str | None] = mapped_column(String(64))
    detail: Mapped[str] = mapped_column(Text, default="")


# --- immutability guards ------------------------------------------------------------------

_LOCKED = ("published", "retired")


@event.listens_for(RuleVersion, "before_update")
def _version_update(_m: Mapper[Any], _c: Any, target: RuleVersion) -> None:
    status = get_history(target, "status")
    was = status.deleted[0] if status.deleted else target.status
    if was in _LOCKED:
        for col in ("body", "body_hash", "number", "author", "approver", "parent", "diff"):
            if get_history(target, col).has_changes():
                raise Immutable(f"rule version {target.number} is {was}: {col} cannot change")
        if was == "retired" or target.status not in ("published", "retired"):
            if status.has_changes():
                raise Immutable(
                    f"rule version {target.number} is {was} and cannot become {target.status}"
                )


@event.listens_for(RuleVersion, "before_delete")
def _version_delete(_m: Mapper[Any], _c: Any, target: RuleVersion) -> None:
    if target.status in _LOCKED:
        raise Immutable(f"rule version {target.number} is {target.status} and cannot be deleted")


for _table in (RuleTemplate, RuleBug, BlueprintRow, BlueprintSlot, StringPackRow, PaperItemRow):

    @event.listens_for(_table, "before_update")
    def _row_update(_m: Mapper[Any], _c: Any, target: Any) -> None:
        raise Immutable(f"{type(target).__tablename__} rows are written once and never edited")


@event.listens_for(PaperRow, "before_update")
def _paper_update(_m: Mapper[Any], _c: Any, target: PaperRow) -> None:
    frozen = get_history(target, "frozen_at")
    was_frozen = bool(frozen.unchanged and frozen.unchanged[0]) or bool(
        frozen.deleted and frozen.deleted[0]
    )
    if was_frozen:
        for col in ("body", "hash", "status", "form", "rules_version", "frozen_at"):
            if col == "status" and target.status == "archived":
                continue  # a frozen paper may be archived: its data does not change
            if get_history(target, col).has_changes():
                raise Immutable(f"paper {target.id} is frozen: {col} cannot change")
