"""Signed links: a short token carrying a few facts (her language, the error to practise) so a
button in the bot can open the Practice Class in the web app as she left it. Signed with an HMAC;
nothing in the token is secret and none of it names a person."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any

_PROCESS_SECRET = secrets.token_bytes(32)


def _key() -> bytes:
    configured = os.environ.get("LINK_SECRET")
    return configured.encode() if configured else _PROCESS_SECRET


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def sign(payload: dict[str, Any], ttl_s: int = 7 * 24 * 3600) -> str:
    body = _b64(json.dumps({**payload, "exp": int(time.time()) + ttl_s}, sort_keys=True).encode())
    mac = _b64(hmac.new(_key(), body.encode(), hashlib.sha256).digest()[:16])
    return f"{body}.{mac}"


def verify(token: str) -> dict[str, Any] | None:
    try:
        body, mac = token.split(".", 1)
        good = _b64(hmac.new(_key(), body.encode(), hashlib.sha256).digest()[:16])
        if not hmac.compare_digest(mac, good):
            return None
        data = json.loads(_unb64(body))
        if not isinstance(data, dict) or int(data.get("exp", 0)) < time.time():
            return None
        data.pop("exp")
        return data
    except (ValueError, TypeError, json.JSONDecodeError):
        return None
