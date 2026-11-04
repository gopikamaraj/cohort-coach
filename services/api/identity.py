# ruff: noqa: E501
"""Who is using the app: the nickname is the user id.

A nickname is normalised (Unicode NFKC, single spaces, lower case) and that string is the user id every record
hangs from, so nicknames are unique. Registering a taken nickname is refused with a clear message; someone who
owns it signs in with it. THERE IS NO PASSWORD: whoever types a nickname is that user. This is demo-grade
identity, said so in docs/privacy.md and on the sign-in screen; a PIN or password is a later decision.

Every request names its user in the `X-User` header (the id, URL-encoded because a nickname can be Tamil or
Hindi). `user_of` is the dependency that reads it; a route that needs a person uses it, and
`services/api/access.py` lists the rule for every route.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import UTC, datetime
from urllib.parse import unquote

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from services.api.db import User
from services.api.dbsession import SESSION

router = APIRouter(prefix="/api/users", tags=["users"])




MIN_LEN, MAX_LEN = 3, 30


def _allowed(text: str) -> bool:
    """Letters (with the combining marks Tamil and Hindi need), numbers, space, dot, dash, underscore."""
    return all(unicodedata.category(ch)[0] in "LMN" or ch in " .-_" for ch in text)

# ids the system itself uses as owners: nobody may register them
RESERVED = frozenset({"unclaimed", "coach-cohorts", "system", "admin", "anonymous", "teacher", "coach", "mentor", "officer"})
UNCLAIMED = "unclaimed"


def normalise(nickname: str) -> str:
    """The user id for a nickname: NFKC, whitespace collapsed to single spaces, lower case."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", nickname)).strip().lower()


def check_nickname(nickname: str) -> str:
    """The user id for a nickname, or HTTP 422 with what to fix."""
    uid = normalise(nickname)
    if not (MIN_LEN <= len(uid) <= MAX_LEN):
        raise HTTPException(422, {"code": "length", "message": f"A nickname has {MIN_LEN} to {MAX_LEN} characters."})
    if not _allowed(uid):
        raise HTTPException(422, {"code": "characters", "message": "Use letters, numbers, spaces, dots, dashes or underscores."})
    if uid in RESERVED:
        raise HTTPException(422, {"code": "reserved", "message": "That nickname is not available. Choose another."})
    return uid


class NicknameIn(BaseModel):
    nickname: str = Field(min_length=1, max_length=60)


def _row(u: User) -> dict[str, str]:
    return {"id": u.id, "nickname": u.nickname}


@router.post("/register", status_code=201)
def register(body: NicknameIn, db: Session = SESSION) -> dict[str, str]:
    uid = check_nickname(body.nickname)
    if db.get(User, uid) is not None:
        raise HTTPException(409, {"code": "taken", "message": "That nickname is taken. If it is yours, sign in with it. Otherwise choose another."})
    user = User(id=uid, nickname=" ".join(body.nickname.split()))
    db.add(user)
    db.commit()
    return _row(user)


@router.post("/signin")
def signin(body: NicknameIn, db: Session = SESSION) -> dict[str, str]:
    uid = normalise(body.nickname)
    user = db.get(User, uid)
    if user is None:
        raise HTTPException(404, {"code": "unknown", "message": "No one has this nickname yet. Check the spelling, or make it new."})
    user.last_seen_at = datetime.now(UTC)
    db.commit()
    return _row(user)


def user_id_from(header: str | None, db: Session) -> str | None:
    """The registered user id a header names, else None."""
    if not header:
        return None
    uid = normalise(unquote(header))
    return uid if db.get(User, uid) is not None else None


def optional_user(x_user: str | None = Header(default=None), db: Session = SESSION) -> str | None:
    return user_id_from(x_user, db)


def user_of(x_user: str | None = Header(default=None), db: Session = SESSION) -> str:
    """The signed-in user's id; 401 when the header is missing or names no one."""
    uid = user_id_from(x_user, db)
    if uid is None:
        raise HTTPException(401, {"code": "sign_in", "message": "Sign in with your nickname first."})
    return uid


@router.get("/me")
def me(uid: str = Depends(user_of), db: Session = SESSION) -> dict[str, str]:
    user = db.get(User, uid)
    assert user is not None
    return _row(user)
