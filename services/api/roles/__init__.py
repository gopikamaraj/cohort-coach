"""Roles: one config the server enforces and the landing-page dialog displays.

`require("<id>")` is a FastAPI dependency. A session's role comes from the `X-Role` header, but
only a server-side judge session (the deployment's JUDGE_MODE setting) may use any role other than
teacher; a production session cannot change role by changing client state. Real role assignment
(by the programme officer, with consent) arrives in P12.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from functools import cache
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends, Header, HTTPException

ROLES = ("teacher", "mentor", "coach", "officer")
CONFIG = Path(__file__).with_name("permissions.yaml")

router = APIRouter(prefix="/api", tags=["roles"])


@cache
def config() -> dict[str, Any]:
    data = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def judge_session() -> bool:
    """True when this deployment is the judge-mode demo. Never read from a request."""
    return os.environ.get("JUDGE_MODE", "1") == "1"


def role_of(x_role: str | None = Header(default=None)) -> str:
    role = (x_role or "teacher").lower()
    if role not in ROLES:
        raise HTTPException(403, "This role does not exist.")
    if role != "teacher" and not judge_session():
        raise HTTPException(403, "You do not hold this role.")
    return role


def require(permission: str) -> Callable[..., str]:
    perm = config()["permissions"][permission]

    def guard(role: str = Depends(role_of)) -> str:
        if permission not in config()["roles"][role]["can"]:
            raise HTTPException(403, "Your role cannot do this.")
        if perm.get("judge_only") and not judge_session():
            raise HTTPException(403, "This is available in the demo only.")
        return role

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
