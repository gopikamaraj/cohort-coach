# ruff: noqa: E501
"""The flow engine: per-teacher state, the next step, answers, identity, linking and deletion.

Every teacher flow runs here, once, for every channel. A channel adapter only renders the steps this
returns and passes answers back. The engine never imports a channel. Anything computed (counts, a
track) comes from the engine package through `facts`.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete
from sqlalchemy.orm import Session

from services.api.db import (
    ChannelLink,
    Consent,
    FlowState,
    LessonTap,
    LinkCode,
    ProfileSync,
    Teacher,
)
from services.api.flows import facts
from services.api.flows.steps import Answer, Flow, Step
from services.api.roles import judge_session

CODE_TTL = timedelta(minutes=15)
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I
MAX_AUTO = 20
SEEN_KEEP = 30


@dataclass
class Turn:
    """What to show now: the steps (auto messages first, then the one that waits for an answer)."""

    steps: list[Step]
    lang: str
    teacher_id: str
    consent: dict[str, Any] | None = None


@dataclass
class Ctx:
    db: Session
    teacher: Teacher
    data: dict[str, Any] = field(default_factory=dict)
    engine: FlowEngine | None = None

    @property
    def summary(self) -> facts.Summary | None:
        return facts.summary(self.db, self.teacher)

    def new_code(self) -> str:
        assert self.engine is not None
        return self.engine.new_code(self.teacher)

    def delete_teacher(self) -> None:
        assert self.engine is not None
        self.engine.delete(self.teacher)


class FlowEngine:
    def __init__(self, db: Session, flows: dict[str, Flow] | None = None) -> None:
        from services.api.flows import FLOWS

        self.db = db
        self.flows = flows or FLOWS

    # ---- identity -------------------------------------------------------------------------

    def teacher_for(self, channel: str, external_id: str, *, judge: bool = False) -> Teacher:
        judge = judge and judge_session()  # a request can ask; only the deployment decides
        link = self.db.get(ChannelLink, (channel, external_id))
        if link is not None:
            teacher = self.db.get(Teacher, link.teacher_id)
            assert teacher is not None
            if judge and not teacher.judge:
                teacher.judge = True
                self.db.commit()
            return teacher
        # a signed-in web user IS the teacher id (the normalised nickname); a chat on another channel gets a random one
        teacher = Teacher(teacher_id=external_id if channel == "pwa" else "t-" + secrets.token_hex(8), judge=judge)
        self.db.add(teacher)
        self.db.flush()
        self.db.add(
            ChannelLink(channel=channel, external_id=external_id, teacher_id=teacher.teacher_id)
        )
        self.db.commit()
        return teacher

    def new_code(self, teacher: Teacher) -> str:
        now = datetime.now(UTC)
        for row in self.db.query(LinkCode).filter_by(teacher_id=teacher.teacher_id):
            if row.expires_at.replace(tzinfo=UTC) > now:
                return row.code
            self.db.delete(row)
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))
        self.db.add(LinkCode(code=code, teacher_id=teacher.teacher_id, expires_at=now + CODE_TTL))
        self.db.commit()
        return code

    def link(self, code: str, channel: str, external_id: str) -> Teacher | None:
        """Join this chat or device to the teacher who made the code. Her other record on this
        channel, if any, is erased: there is one teacher, not two."""
        if channel == "pwa":  # a web user is her nickname: there is no second record to join
            return None
        row = self.db.get(LinkCode, code.strip().upper())
        if row is None or row.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
            return None
        target = self.db.get(Teacher, row.teacher_id)
        if target is None:
            return None
        existing = self.db.get(ChannelLink, (channel, external_id))
        if existing is not None and existing.teacher_id != target.teacher_id:
            old = self.db.get(Teacher, existing.teacher_id)
            self.db.delete(existing)
            self.db.flush()
            if old is not None:
                self._erase(old)
        if self.db.get(ChannelLink, (channel, external_id)) is None:
            self.db.add(
                ChannelLink(channel=channel, external_id=external_id, teacher_id=target.teacher_id)
            )
        self.db.delete(row)
        self.db.commit()
        return target

    def delete(self, teacher: Teacher) -> None:
        """The right to erasure: her record, links, state and class counts, on every channel."""
        self._erase(teacher)
        self.db.commit()

    def _erase(self, teacher: Teacher) -> None:
        tid = teacher.teacher_id
        if teacher.class_id:
            self.db.execute(delete(ProfileSync).where(ProfileSync.class_id == teacher.class_id))
        devices = [
            r.external_id
            for r in self.db.query(ChannelLink).filter_by(teacher_id=tid, channel="pwa")
        ]
        if devices:  # her consent history goes too: erasure means erasure
            self.db.execute(delete(Consent).where(Consent.subject_id.in_(devices)))
        self.db.execute(delete(LessonTap).where(LessonTap.teacher_id == tid))
        self.db.execute(delete(LinkCode).where(LinkCode.teacher_id == tid))
        self.db.execute(delete(ChannelLink).where(ChannelLink.teacher_id == tid))
        self.db.execute(delete(FlowState).where(FlowState.teacher_id == tid))
        self.db.execute(delete(Teacher).where(Teacher.teacher_id == tid))
        self.db.expire_all()

    # ---- flow ------------------------------------------------------------------------------

    def _state(self, teacher: Teacher) -> FlowState:
        st = self.db.get(FlowState, teacher.teacher_id)
        if st is None:
            flow = self.flows["onboarding"]
            st = FlowState(
                teacher_id=teacher.teacher_id,
                flow_id=flow.id,
                version=flow.version,
                step_id=flow.start,
                data={},
            )
            self.db.add(st)
            self.db.flush()
        return st

    def _ctx(self, teacher: Teacher, st: FlowState) -> Ctx:
        return Ctx(self.db, teacher, dict(st.data or {}), self)

    def _emit(self, teacher: Teacher, st: FlowState, ctx: Ctx) -> list[Step]:
        steps: list[Step] = []
        for _ in range(MAX_AUTO):
            flow = self.flows[st.flow_id]
            node = flow.nodes[st.step_id]
            step = node.build(ctx)
            unknown = step.all_keys() - set(node.keys)
            assert not unknown, f"{flow.id}:{st.step_id} shows keys it did not declare: {unknown}"
            steps.append(step)
            if not node.auto:
                break
            self._go(st, node.advance(ctx, Answer(value="auto")))
        self._save(teacher, st, ctx)
        return steps

    def _go(self, st: FlowState, target: str | None) -> None:
        if target is None:
            return
        if ":" in target:
            flow_id, step_id = target.split(":", 1)
            st.flow_id, st.step_id, st.version = flow_id, step_id, self.flows[flow_id].version
        else:
            st.step_id = target

    def _save(self, teacher: Teacher, st: FlowState, ctx: Ctx) -> None:
        st.data = dict(ctx.data)
        st.updated_at = datetime.now(UTC)
        self.db.commit()

    def _turn(self, teacher: Teacher, steps: list[Step]) -> Turn:
        return Turn(
            steps=steps, lang=teacher.lang, teacher_id=teacher.teacher_id, consent=teacher.consent
        )

    def start(self, teacher: Teacher) -> Turn:
        """Show where she is now. Safe to call again."""
        st = self._state(teacher)
        back = self.flows[st.flow_id].nodes[st.step_id].reentry
        if back:
            st.step_id = back
        return self._turn(teacher, self._emit(teacher, st, self._ctx(teacher, st)))

    def ask_delete(self, teacher: Teacher) -> Turn:
        """/stop: go to the delete confirmation. Nothing is deleted until she confirms."""
        st = self._state(teacher)
        self._go(st, "t1:confirm_delete")
        return self._turn(teacher, self._emit(teacher, st, self._ctx(teacher, st)))

    def answer(self, teacher: Teacher, step_id: str, value: str, key: str | None = None) -> Turn:
        """Apply an answer to the step she is on. An answer to any other step, or a replay of a key
        already used, changes nothing and shows where she is. A value that is not an option raises
        ValueError."""
        st = self._state(teacher)
        ctx = self._ctx(teacher, st)
        seen: list[str] = list(ctx.data.get("_seen", []))
        if st.step_id != step_id or (key and key in seen):
            return self._turn(teacher, self._emit(teacher, st, ctx))
        node = self.flows[st.flow_id].nodes[st.step_id]
        current = node.build(ctx)
        if current.options and value not in current.option_ids():
            raise ValueError(f"{value!r} is not an option of step {step_id}")
        target = node.advance(ctx, Answer(value=value))
        if key:
            ctx.data["_seen"] = (seen + [key])[-SEEN_KEEP:]
        if target == "end:deleted":  # the teacher no longer exists: show the goodbye once
            return self._goodbye(teacher)
        self._go(st, target)
        self.db.merge(teacher)
        return self._turn(teacher, self._emit(teacher, st, ctx))

    def _goodbye(self, teacher: Teacher) -> Turn:
        from services.api.flows.t1 import goodbye

        lang = teacher.lang
        tid = teacher.teacher_id
        self.delete(teacher)
        return Turn(steps=[goodbye()], lang=lang, teacher_id=tid)
