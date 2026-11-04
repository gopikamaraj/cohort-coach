# ruff: noqa: E501
"""Database models. Class-level counts only: no child, roll number, answer or photo columns.

Alembic migrations arrive with the first real API schema (see DECISIONS.md); until then the dev
and test databases are built with `Base.metadata.create_all`.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Engine,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class School(Base):
    __tablename__ = "school"

    school_id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    school_type: Mapped[str]
    medium: Mapped[str]
    simulated: Mapped[bool] = mapped_column(default=False)


class ClassRoom(Base):
    __tablename__ = "classroom"

    class_id: Mapped[str] = mapped_column(primary_key=True)
    school_id: Mapped[str] = mapped_column(ForeignKey("school.school_id"))
    block_id: Mapped[str]
    grade: Mapped[int]
    section: Mapped[str]
    medium: Mapped[str]
    teacher_id: Mapped[str]
    teacher_name: Mapped[str]  # fictional in the simulated block
    simulated: Mapped[bool] = mapped_column(default=False)


class ClassTermCount(Base):
    """What one class's check produced in one term: how many children showed each error."""

    __tablename__ = "class_term_count"
    __table_args__ = (UniqueConstraint("class_id", "term"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    class_id: Mapped[str] = mapped_column(ForeignKey("classroom.class_id"))
    term: Mapped[str]
    form_label: Mapped[str]
    children_checked: Mapped[int]
    counts: Mapped[dict[str, Any]] = mapped_column(JSON)
    anchor_wrong_count: Mapped[int]
    untracked: Mapped[dict[str, Any]] = mapped_column(JSON)
    simulated: Mapped[bool] = mapped_column(default=False)


class Assignment(Base):
    """A class's track for the coming term and its waitlist arm (computed by the engine)."""

    __tablename__ = "assignment"

    class_id: Mapped[str] = mapped_column(ForeignKey("classroom.class_id"), primary_key=True)
    track: Mapped[str]
    version: Mapped[str]
    arm: Mapped[str]
    stratum: Mapped[int]
    reason: Mapped[str]
    children_checked: Mapped[int]
    children_showing: Mapped[int]
    simulated: Mapped[bool] = mapped_column(default=False)


class Cohort(Base):
    __tablename__ = "cohort"

    cohort_id: Mapped[str] = mapped_column(primary_key=True)
    error: Mapped[str]
    medium: Mapped[str]
    size: Mapped[int]
    class_ids: Mapped[list[str]] = mapped_column(JSON)
    block_id: Mapped[str | None]
    cross_block: Mapped[bool]
    undersized: Mapped[bool]
    mentor_slot: Mapped[bool]
    simulated: Mapped[bool] = mapped_column(default=False)


def _now() -> datetime:
    return datetime.now(UTC)


class AiCall(Base):
    """The audit trail: one row per AI call. Metadata only, never prompt or output text."""

    __tablename__ = "ai_calls"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    call_id: Mapped[int] = mapped_column(Integer)
    call_key: Mapped[str] = mapped_column(String(40), index=True)
    prompt_version: Mapped[int] = mapped_column(Integer)
    model: Mapped[str] = mapped_column(String(60))
    mode: Mapped[str] = mapped_column(String(10))  # recorded | live | record
    judge: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_only: Mapped[bool] = mapped_column(Boolean, default=False)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    tokens_cache_read: Mapped[int] = mapped_column(Integer, default=0)
    tokens_cache_write: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    validator_results: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    checker_verdict: Mapped[str | None] = mapped_column(String(10))  # pass | fail | none
    checker_reason: Mapped[str | None] = mapped_column(String(300))
    retries: Mapped[int] = mapped_column(Integer, default=0)
    fallback_used: Mapped[str | None] = mapped_column(String(40))
    input_hash: Mapped[str] = mapped_column(String(64))
    reviewer_decision: Mapped[str | None] = mapped_column(String(20))
    reviewer_reason: Mapped[str | None] = mapped_column(String(40))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SpeechCall(Base):
    """One speech request (stt or tts). Metadata only: never the audio or the text."""

    __tablename__ = "speech_calls"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    stage: Mapped[str] = mapped_column(String(8))  # stt | tts
    mode: Mapped[str] = mapped_column(String(8))  # live | stub
    language: Mapped[str] = mapped_column(String(4))
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    audio_bytes: Mapped[int] = mapped_column(Integer, default=0)
    characters: Mapped[int] = mapped_column(Integer, default=0)
    seconds: Mapped[float] = mapped_column(Float, default=0.0)
    cost_inr: Mapped[float] = mapped_column(Float, default=0.0)
    from_cache: Mapped[bool] = mapped_column(Boolean, default=False)
    error_kind: Mapped[str | None] = mapped_column(String(16))


class SimObservation(Base):
    """A teacher's view, after trying it in class, of how like her real class the simulated children
    were. Choices only (no free text, no class or teacher id): a signal for tuning the simulator."""

    __tablename__ = "sim_observations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    scenario: Mapped[str] = mapped_column(String(12))
    language: Mapped[str] = mapped_column(String(4))
    likeness: Mapped[str] = mapped_column(String(10))  # like | some | not_like
    differences: Mapped[list[str]] = mapped_column(JSON, default=list)


class Feedback(Base):
    """App, simulation, content and card feedback. Anonymous: no user, class or device id."""

    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    kind: Mapped[str] = mapped_column(
        String(12), index=True
    )  # app | simulation | content | card_flag
    rating: Mapped[int | None] = mapped_column(Integer)
    text: Mapped[str | None] = mapped_column(String(500))
    language: Mapped[str] = mapped_column(String(4))
    role: Mapped[str] = mapped_column(String(10))
    context: Mapped[str | None] = mapped_column(String(40))  # e.g. the error code of a flagged card
    status: Mapped[str] = mapped_column(String(10), default="new", index=True)  # new | reviewed
    admin_note: Mapped[str | None] = mapped_column(String(300))


class ReviewItem(Base):
    """AI content waiting for, or past, human review (track drafts, method cards)."""

    __tablename__ = "review_items"

    item_id: Mapped[str] = mapped_column(primary_key=True)
    content_type: Mapped[str]  # track_draft | method_card | feedback_card
    ai_call_id: Mapped[int | None] = mapped_column(ForeignKey("ai_calls.id"))
    language: Mapped[str]
    target_error: Mapped[str | None]
    content: Mapped[dict[str, Any]] = mapped_column(JSON)
    badge: Mapped[str] = mapped_column(default="none")  # none | checked | checked_reviewed
    status: Mapped[str] = mapped_column(default="pending")  # pending | approved | rejected
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ReviewDecision(Base):
    __tablename__ = "review_decisions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("review_items.item_id"), index=True)
    decision: Mapped[str]  # approve | reject | edit
    reason: Mapped[str | None]  # structured enum, set on reject (ai/guard/rejections.py)
    edit_diff: Mapped[str | None]
    reviewer_role: Mapped[str]  # reviewer | mentor
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class TeacherFlag(Base):
    """A teacher tapped 'this is wrong' on an AI card. No free text is stored."""

    __tablename__ = "teacher_flags"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ai_call_id: Mapped[int | None] = mapped_column(ForeignKey("ai_calls.id"))
    item_id: Mapped[str | None] = mapped_column(ForeignKey("review_items.item_id"))
    kind: Mapped[str]  # wrong_maths | not_my_class | unclear | other
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Consent(Base):
    """What a teacher or mentor agreed to share. Withdrawing adds a row; history is kept."""

    __tablename__ = "consents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    subject_id: Mapped[str] = mapped_column(index=True)
    scope: Mapped[str]  # e.g. counts.v1, practice_ai.v1, share_rehearsal.v1, feedback.v1, core.v1
    granted: Mapped[bool]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


def cloudsql_url() -> str | None:
    """A Cloud SQL (Postgres) URL built from parts, so the password can come from a secret
    reference and never be written into a URL by hand: CLOUDSQL_INSTANCE (project:region:name),
    DB_NAME, DB_PASSWORD."""
    from urllib.parse import quote

    instance, password = os.environ.get("CLOUDSQL_INSTANCE"), os.environ.get("DB_PASSWORD")
    if not instance or not password:
        return None
    user, name = os.environ.get("DB_USER", "postgres"), os.environ.get("DB_NAME", "cohort")
    pw = quote(password, safe="")
    return f"postgresql+psycopg://{user}:{pw}@/{name}?host=/cloudsql/{instance}"


def make_engine(url: str | None = None) -> Engine:
    """Engine from DATABASE_URL, else Cloud SQL parts, else SQLite for local dev and tests."""
    found = url or os.environ.get("DATABASE_URL") or cloudsql_url()
    return create_engine(found or "sqlite:///./dev.sqlite")


class ProfileSync(Base):
    """A class's check result as the phone sends it: counts only, never a per-child answer.

    The class id is a random id made on the phone; no school, teacher or child is named here.
    """

    __tablename__ = "profile_sync"
    __table_args__ = (UniqueConstraint("owner", "class_id", "term"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner: Mapped[str] = mapped_column(String(32), index=True, default="unclaimed")  # the user id
    class_id: Mapped[str] = mapped_column(String(40), index=True)
    term: Mapped[str] = mapped_column(String(8))
    form: Mapped[str] = mapped_column(String(40))  # a paper id (P-…), not just a letter
    children_checked: Mapped[int] = mapped_column(Integer)
    counts: Mapped[dict[str, Any]] = mapped_column(JSON)
    anchor_wrong_count: Mapped[int] = mapped_column(Integer)
    untracked: Mapped[dict[str, Any]] = mapped_column(JSON)
    simulated: Mapped[bool] = mapped_column(Boolean, default=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class User(Base):
    """A person who uses the app. The id is the nickname, normalised (lower case, single spaces), so a nickname
    is unique and is the key every record hangs from. There is no password: whoever types a nickname is that
    user. That is demo-grade identity and is documented as such (docs/privacy.md)."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # the normalised nickname
    nickname: Mapped[str] = mapped_column(String(30))  # as first typed, for display to herself only
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Teacher(Base):
    """One pseudonymous teacher across channels. No name, phone or handle is stored here."""

    __tablename__ = "teachers"

    teacher_id: Mapped[str] = mapped_column(String(32), primary_key=True)  # the user id (the normalised nickname)
    lang: Mapped[str] = mapped_column(String(4), default="en")
    consent: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    judge: Mapped[bool] = mapped_column(Boolean, default=False)
    class_id: Mapped[str | None] = mapped_column(String(20))  # the random class id her phone made
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ChannelLink(Base):
    """Which chat or device is which teacher. Only a channel adapter's entry point reads this table:
    chat ids are personal data and never join to anything shown to other people."""

    __tablename__ = "channel_links"

    channel: Mapped[str] = mapped_column(String(10), primary_key=True)  # pwa | telegram | whatsapp
    external_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    teacher_id: Mapped[str] = mapped_column(ForeignKey("teachers.teacher_id"), index=True)


class LinkCode(Base):
    """A one-time code that joins a second channel to a teacher. Valid for 15 minutes, used once."""

    __tablename__ = "link_codes"

    code: Mapped[str] = mapped_column(String(8), primary_key=True)
    teacher_id: Mapped[str] = mapped_column(ForeignKey("teachers.teacher_id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class FlowState(Base):
    """Where a teacher is in a flow. `data` holds answers that are not child data (language, consent
    choices, a few replay keys), never a child's answers."""

    __tablename__ = "flow_state"

    teacher_id: Mapped[str] = mapped_column(ForeignKey("teachers.teacher_id"), primary_key=True)
    flow_id: Mapped[str] = mapped_column(String(20))
    version: Mapped[int] = mapped_column(Integer, default=1)
    step_id: Mapped[str] = mapped_column(String(30))
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ContentVersion(Base):
    """One version of an item of content (a track, a strategy, a scenario, a setting).

    draft -> in_review -> approved (the coach's key, gate 3) -> active (the officer's key) ->
    retired. The body never changes after it is written: an edit is a new version, and the old one
    stays in use until the new one is active (addendum v3.1 section D).
    """

    __tablename__ = "content_versions"
    __table_args__ = (UniqueConstraint("content_type", "content_id", "version"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    content_type: Mapped[str] = mapped_column(
        String(16), index=True
    )  # track | strategy | scenario | setting
    content_id: Mapped[str] = mapped_column(String(60), index=True)
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(10), default="draft", index=True)
    body: Mapped[dict[str, Any]] = mapped_column(JSON)
    content_hash: Mapped[str] = mapped_column(String(64))
    parent_version: Mapped[int | None] = mapped_column(Integer)
    created_by: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    coach_approved_by: Mapped[str | None] = mapped_column(String(40))
    coach_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    officer_activated_by: Mapped[str | None] = mapped_column(String(40))
    officer_activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ContentAudit(Base):
    """Who did what to which version: role, pseudonymous id, action, version. Ids and codes only;
    never the text of a lesson."""

    __tablename__ = "content_audit"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    role: Mapped[str] = mapped_column(String(12))
    actor: Mapped[str] = mapped_column(String(40))
    action: Mapped[str] = mapped_column(String(20), index=True)
    content_type: Mapped[str] = mapped_column(String(16))
    content_id: Mapped[str] = mapped_column(String(60))
    version: Mapped[int] = mapped_column(Integer)
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class TrackManifest(Base):
    """What was published for one cohort from one track version: parts, audio keys, sizes, scripts
    and badges, and the roles and times of the two keys. The lesson screen and the bot read it."""

    __tablename__ = "track_manifests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    version_id: Mapped[str] = mapped_column(ForeignKey("content_versions.id"), index=True)
    cohort_id: Mapped[str] = mapped_column(String(60), index=True)
    body: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class LessonTap(Base):
    """Her two taps after a lesson (self-report): "Tried it in class?" and "How did it go?". One row
    per teacher per lesson, keyed by her pseudonymous id; no free text. Officers read counts only,
    labelled self-report, and a figure over fewer than 5 classes is hidden."""

    __tablename__ = "lesson_taps"
    __table_args__ = (UniqueConstraint("teacher_id", "track_id", "lesson_day"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    teacher_id: Mapped[str] = mapped_column(String(32), index=True)
    track_id: Mapped[str] = mapped_column(String(20))  # the tracked error, e.g. SUB-SFL
    lesson_day: Mapped[int] = mapped_column(Integer)
    tried: Mapped[bool | None] = mapped_column(Boolean)
    outcome: Mapped[str | None] = mapped_column(String(10))  # worked | partly | didnt
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class CohortSpace(Base):
    """A cohort as a space people belong to: lifecycle, people and thread state. (The `cohort`
    table is the grouping the engine computed from the check; this is what a coach runs.)
    proposed, active, closing, closed; cancelled from proposed or active."""

    __tablename__ = "cohort_spaces"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    error: Mapped[str] = mapped_column(String(16))
    track_version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(10), default="proposed", index=True)
    coach_id: Mapped[str | None] = mapped_column(String(40))
    officer_id: Mapped[str | None] = mapped_column(String(40))
    mentor_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    school_count: Mapped[int] = mapped_column(Integer, default=0)
    post_test_received: Mapped[bool] = mapped_column(Boolean, default=False)
    close_reason: Mapped[str | None] = mapped_column(String(60))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    simulated: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ClassCohort(Base):
    """A cohort of one class: "Just my class, no other teachers yet". Counts only (the errors she
    chose and how many children showed each); no child, no answer, no roll number. A separate,
    labelled path: COHORT_MIN_CLASSES is not touched and cohort formation never reads this table."""

    __tablename__ = "class_cohorts"
    __table_args__ = (UniqueConstraint("teacher_id", "check_id"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    teacher_id: Mapped[str] = mapped_column(String(32), index=True)
    check_id: Mapped[str] = mapped_column(String(80))  # the check it was made from (class:running number)
    group_id: Mapped[str | None] = mapped_column(String(40), index=True)  # a teacher's copy of a group cohort points at the group
    name: Mapped[str] = mapped_column(String(80))
    scope: Mapped[str] = mapped_column(String(16), default="class_only")
    errors: Mapped[list[str]] = mapped_column(JSON, default=list)
    counts: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    children_checked: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(10), default="active")
    simulated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AudioDownloadUse(Base):
    """How many characters of "Download audio" a phone has used: a count and nothing else."""

    __tablename__ = "audio_download_use"

    teacher_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    chars: Mapped[int] = mapped_column(Integer, default=0)


class CohortMember(Base):
    """A teacher in a cohort space. The display name is a label the system made (Teacher 7),
    unique in the cohort and never typed by her; the coach can map it to the teacher (see docs)."""

    __tablename__ = "cohort_members"
    __table_args__ = (UniqueConstraint("cohort_id", "display_name"),)

    cohort_id: Mapped[str] = mapped_column(ForeignKey("cohort_spaces.id"), primary_key=True)
    teacher_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(24))
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class CohortAuditRow(Base):
    """One row per cohort or thread decision: who (a role and a pseudonymous id), what, when."""

    __tablename__ = "cohort_audit"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    cohort_id: Mapped[str] = mapped_column(String(40), index=True)
    role: Mapped[str] = mapped_column(String(10))
    actor: Mapped[str] = mapped_column(String(40))
    action: Mapped[str] = mapped_column(String(30))
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)  # ids, codes, counts only


class ThreadPost(Base):
    """A post in a cohort thread. `body` is emptied by the retention job and on a coach's call."""

    __tablename__ = "thread_posts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    cohort_id: Mapped[str] = mapped_column(ForeignKey("cohort_spaces.id"), index=True)
    author_kind: Mapped[str] = mapped_column(String(8))  # teacher | mentor | coach | system
    author_teacher_id: Mapped[str | None] = mapped_column(String(32))  # never returned by the API
    author_name: Mapped[str] = mapped_column(String(24))
    body: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(10), default="visible", index=True)
    # visible | reported | hidden | deleted
    rule_id: Mapped[str | None] = mapped_column(String(20))
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MentorItem(Base):
    """A mentor's recording or method-card step on its way to teachers. Nothing reaches a teacher
    unless the coach approved it and a published track version includes it (in_use)."""

    __tablename__ = "mentor_items"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    mentor_id: Mapped[str] = mapped_column(String(40), index=True)
    cohort_id: Mapped[str] = mapped_column(ForeignKey("cohort_spaces.id"), index=True)
    kind: Mapped[str] = mapped_column(String(12))  # recording | method_card
    version: Mapped[int] = mapped_column(Integer, default=1)
    parent_id: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    # draft | awaiting_coach | changes_requested | approved | rejected | in_use | retired
    reason_code: Mapped[str | None] = mapped_column(String(30))
    note: Mapped[str | None] = mapped_column(String(300))
    decided_by: Mapped[str | None] = mapped_column(String(40))
    in_use_version_id: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ChatThread(Base):
    """One teacher's private question thread inside a cohort: she, the cohort's mentors and its
    coach. Not the shared cohort thread. The teacher id is never returned by any API."""

    __tablename__ = "chat_threads"
    __table_args__ = (UniqueConstraint("cohort_id", "teacher_id"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    cohort_id: Mapped[str] = mapped_column(ForeignKey("cohort_spaces.id"), index=True)
    teacher_id: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ChatMessage(Base):
    """A question, an answer or a correction. The body holds masked text only (names, roll numbers
    and phone numbers are replaced when the question is posted) and is emptied by retention."""

    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    thread_id: Mapped[str] = mapped_column(ForeignKey("chat_threads.id"), index=True)
    cohort_id: Mapped[str] = mapped_column(String(40), index=True)
    reply_to: Mapped[str | None] = mapped_column(String(32), index=True)
    kind: Mapped[str] = mapped_column(String(10))  # question | answer | correction
    author_role: Mapped[str] = mapped_column(String(8))  # teacher | mentor | coach | ai
    author_label: Mapped[str] = mapped_column(String(24))  # "Teacher 3", "Mentor", "Coach", "AI"
    body: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(4), default="en")
    # question: pending | ai_draft_ready | answered_by_human | ai_sent | corrected
    # answer or correction: sent (an AI answer is ai_sent, then corrected)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    ai_assisted: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    question_class: Mapped[str | None] = mapped_column(String(24))
    flag: Mapped[str | None] = mapped_column(String(16))  # safety
    escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    alert_reason: Mapped[str | None] = mapped_column(String(30))
    alerted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ai_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    seen: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AiReplyDraft(Base):
    """The AI's draft for one question, with the approved sources it cited and what the checks
    found. It reaches the teacher only through a person, or through the auto-send gates."""

    __tablename__ = "ai_reply_drafts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    message_id: Mapped[str] = mapped_column(ForeignKey("chat_messages.id"), unique=True)
    draft_text: Mapped[str | None] = mapped_column(Text)
    sources: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    question_class: Mapped[str | None] = mapped_column(String(24))
    checker_result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    model: Mapped[str | None] = mapped_column(String(40))
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    # drafted | sent_as_is | edited_and_sent | discarded | auto_sent
    status: Mapped[str] = mapped_column(String(16), default="drafted")
    edited_text: Mapped[str | None] = mapped_column(Text)
    edit_reason_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    decided_by: Mapped[str | None] = mapped_column(String(40))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    quality: Mapped[str | None] = mapped_column(String(8))  # good | not_good
    no_reply_reason: Mapped[str | None] = mapped_column(String(60))
    held_codes: Mapped[list[str]] = mapped_column(JSON, default=list)
    ai_call_id: Mapped[int | None] = mapped_column(Integer)
    reply_message_id: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ChatConfig(Base):
    """The coach's settings for how long a question waits for a person, and whether the AI may
    answer when nobody does. `global` is the default; a cohort's own row beats it."""

    __tablename__ = "chat_config"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)  # "global" or a cohort id
    scope: Mapped[str] = mapped_column(String(8))
    cohort_id: Mapped[str | None] = mapped_column(String(40))
    ai_timeout_hours: Mapped[int] = mapped_column(Integer, default=24)
    ai_auto_send_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    set_by: Mapped[str] = mapped_column(String(40))
    set_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# Paper Studio and Demo Studio tables share this Base (imported last, so create_all builds them).
# The demo tables hold judge-demo data only: simulated, keyed by the demo session.
from services.cohort_chat import models as _chat_models  # noqa: E402, F401
from services.content import lesson_audio as _lesson_audio  # noqa: E402, F401
from services.demo import models as _demo_models  # noqa: E402, F401
from services.modules import models as _module_models  # noqa: E402, F401
from services.papers import models as _paper_models  # noqa: E402, F401
from services.papers_hub import models as _hub_models  # noqa: E402, F401
from services.sheets_keep import models as _keep_models  # noqa: E402, F401
