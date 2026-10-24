"""Roles: one config the server enforces and the landing-page dialog displays.

`require("<id>")` is a FastAPI dependency. A session's role comes from the `X-Role` header, but
only a server-side judge session (the deployment's JUDGE_MODE setting) may use any role other than
teacher; a production session cannot change role by changing client state. Real role assignment
(by the programme officer, with consent) arrives in P12.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import cache
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends, Header, HTTPException

from ai.config import judge_mode, pilot_mode

ROLES = ("teacher", "mentor", "coach", "officer")
# Pilot mode (PILOT_MODE=1) has its own sign-in: a signed token names the account and its roles.
# The landing page never lists the coordinator; ROLES stays the four the landing page shows.
PILOT_ROLES = ("coordinator", "coach", "officer")
CONFIG = Path(__file__).with_name("permissions.yaml")

router = APIRouter(prefix="/api", tags=["roles"])


@cache
def config() -> dict[str, Any]:
    data = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def judge_session() -> bool:
    """True when this deployment is the judge-mode demo. Never read from a request."""
    return judge_mode()


def role_of(x_role: str | None = Header(default=None)) -> str:
    role = (x_role or "teacher").lower()
    if role not in ROLES:
        raise HTTPException(403, "This role does not exist.")
    if role != "teacher" and not judge_session():
        raise HTTPException(403, "You do not hold this role.")
    return role


def held_roles(
    x_role: str | None = Header(default=None), authorization: str | None = Header(default=None)
) -> tuple[str, ...]:
    """The roles of this request. In pilot mode they come only from the signed sign-in token (the
    X-Role header is ignored); otherwise from role_of, as before."""
    if pilot_mode():
        from services.pilot.auth import principal_from_header

        return principal_from_header(authorization).roles
    return (role_of(x_role),)


def require(permission: str) -> Callable[..., str]:
    perm = config()["permissions"][permission]

    def guard(roles: tuple[str, ...] = Depends(held_roles)) -> str:
        granted = [r for r in roles if permission in config()["roles"][r]["can"]]
        if not granted:
            raise HTTPException(403, "Your role cannot do this.")
        if perm.get("judge_only") and not judge_session():
            raise HTTPException(403, "This is available in the demo only.")
        return granted[0]

    return guard


@router.get("/roles")
def roles() -> dict[str, Any]:
    """The role config for the landing page and its dialog. Production shows only the teacher
    card until role assignment exists (P12)."""
    cfg = config()
    judge = judge_session()
    out = []
    for rid in ROLES if judge else ("teacher",):
        r = cfg["roles"][rid]
        out.append(
            {
                "id": rid,
                "card": r["card"],
                "holders": r["holders"],
                "data": r["data"],
                "also_on": r["also_on"],
                "weekly_minutes": cfg["weekly_minutes"][rid],
                "can": [
                    {
                        "id": p,
                        "key": cfg["permissions"][p]["key"],
                        "planned": cfg["permissions"][p].get("planned"),
                    }
                    for p in r["can"]
                ],
                "cannot": [
                    {
                        "id": b,
                        "key": cfg["boundaries"][b]["key"],
                        "planned": cfg["boundaries"][b].get("planned"),
                    }
                    for b in r["cannot"]
                ],
            }
        )
    return {"judge": judge, "roles": out}
