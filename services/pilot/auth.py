"""Pilot sign-in: the existing auth stub, made real enough for a public pilot URL.

Accounts come from the environment (PILOT_ACCOUNTS), never the code or the database:

    PILOT_ACCOUNTS="seema:coordinator+coach:KEY1,shivani:coordinator:KEY2"

name : roles joined by "+" : key. A key may not contain "," or ":". The account type for the
person who uploads photos is `coordinator`; `coach` and `officer` keep the permissions they have
elsewhere (the coach approves; the officer only looks). One person may hold more than one role.
Sign-in returns a signed, expiring token; the API reads roles only from that token.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Header, HTTPException

TOKEN_TTL_S = 12 * 60 * 60
NAME = re.compile(r"^[a-z0-9._-]{2,24}$")
MAX_FAILURES = 5
FAILURE_WINDOW_S = 10 * 60
PILOT_ROLES = ("coordinator", "coach", "officer")

_clock: Callable[[], float] = time.time
_failures: dict[str, deque[float]] = defaultdict(deque)


@dataclass(frozen=True)
class Principal:
    name: str
    roles: tuple[str, ...]


def set_clock(clock: Callable[[], float]) -> None:
    """Tests move time with this; production never calls it."""
    global _clock
    _clock = clock


def reset_throttle() -> None:
    _failures.clear()


def _secret() -> bytes:
    secret = os.environ.get("PILOT_TOKEN_SECRET") or os.environ.get("LINK_SECRET")
    if not secret:
        raise HTTPException(503, "Sign-in is not set up on this server.")
    return secret.encode()


def accounts() -> dict[str, tuple[tuple[str, ...], str]]:
    """name -> (roles, key), parsed from PILOT_ACCOUNTS. A malformed entry is skipped."""
    out: dict[str, tuple[tuple[str, ...], str]] = {}
    for entry in (os.environ.get("PILOT_ACCOUNTS") or "").split(","):
        parts = entry.strip().split(":")
        if len(parts) != 3:
            continue
        name, roles_text, key = (p.strip() for p in parts)
        roles = tuple(r for r in roles_text.split("+") if r in PILOT_ROLES)
        if NAME.match(name) and roles and key:
            out[name] = (roles, key)
    return out


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def make_token(principal: Principal, ttl: int = TOKEN_TTL_S) -> str:
    body = _b64(
        json.dumps(
            {"n": principal.name, "r": list(principal.roles), "e": int(_clock()) + ttl},
            separators=(",", ":"),
        ).encode()
    )
    sig = hmac.new(_secret(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64(sig)}"


def now() -> float:
    return _clock()


def sign_claims(claims: dict[str, object]) -> str:
    """A signed claim set for links that carry no sign-in (a lesson link). Staff tokens are
    different: read_token needs a name and roles, which these never hold."""
    body = _b64(json.dumps(claims, separators=(",", ":")).encode())
    return f"{body}.{_b64(hmac.new(_secret(), body.encode(), hashlib.sha256).digest())}"


def read_claims(token: str) -> dict[str, object] | None:
    """The claims of an untampered, unexpired signed link, else None."""
    body, _, sig = token.partition(".")
    try:
        if not hmac.compare_digest(
            hmac.new(_secret(), body.encode(), hashlib.sha256).digest(), _unb64(sig)
        ):
            return None
        claims = json.loads(_unb64(body))
        if not isinstance(claims, dict) or float(claims["e"]) < _clock():
            return None
    except (ValueError, KeyError, TypeError):
        return None
    return claims


def read_token(token: str) -> Principal | None:
    body, _, sig = token.partition(".")
    try:
        if not hmac.compare_digest(
            hmac.new(_secret(), body.encode(), hashlib.sha256).digest(), _unb64(sig)
        ):
            return None
        claims = json.loads(_unb64(body))
        if claims["e"] < _clock():
            return None
        roles = tuple(r for r in claims["r"] if r in PILOT_ROLES)
        name = str(claims["n"])
    except (ValueError, KeyError, TypeError):
        return None
    # The account must still exist and still hold the roles: removing it ends its tokens.
    known = accounts().get(name)
    if not known or not roles or not set(roles) <= set(known[0]):
        return None
    return Principal(name, roles)


def principal_from_header(authorization: str | None) -> Principal:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Sign in first.")
    principal = read_token(authorization[7:].strip())
    if principal is None:
        raise HTTPException(401, "Your sign-in has ended. Sign in again.")
    return principal


def current_principal(authorization: str | None = Header(default=None)) -> Principal:
    return principal_from_header(authorization)


def sign_in(name: str, key: str) -> tuple[str, Principal]:
    """A token for a correct name and key. Five wrong tries in ten minutes pause that name."""
    name = name.strip().lower()
    now = _clock()
    attempts = _failures[name]
    while attempts and attempts[0] < now - FAILURE_WINDOW_S:
        attempts.popleft()
    if len(attempts) >= MAX_FAILURES:
        raise HTTPException(429, "Too many tries. Wait ten minutes, then try again.")
    known = accounts().get(name)
    # compare against something even when the name is unknown, so timing does not tell them apart
    expected = known[1] if known else "x" * 16
    if not (hmac.compare_digest(expected.encode(), key.encode()) and known):
        attempts.append(now)
        raise HTTPException(401, "That name or key is not right.")
    attempts.clear()
    principal = Principal(name, known[0])
    return make_token(principal), principal
