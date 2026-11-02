"""Model IDs, timeouts, retries and effort per call. IDs are overridable by env var."""

from __future__ import annotations

import os
from dataclasses import dataclass

# Verified 2026-10-16, see DECISIONS.md (P03 verified API facts).
DEFAULT_MODELS: dict[str, str] = {
    "MODEL_CHILD": "claude-sonnet-5-5",
    "MODEL_LABEL": "claude-haiku-5-5",
    "MODEL_FEEDBACK": "claude-sonnet-5-5",
    "MODEL_METHOD": "claude-sonnet-5-5",
    "MODEL_DRAFT": "claude-opus-5-5",
    "MODEL_DIGEST": "claude-haiku-5-5",
    "MODEL_POINTER": "claude-haiku-5-5",  # call 9 (reflection pointer), built in P10
    "MODEL_DEMO_TEACHER": "claude-haiku-5-5",  # call 10, judge mode only
    "MODEL_SPRITE": "claude-sonnet-5-5",  # call 11 (sprite item authoring), offline only
    "MODEL_FEEDBACK_REVIEW": "claude-haiku-5-5",  # call 17 (read a note about a module)
    "MODEL_NARRATION": "claude-haiku-5-5",  # call 18 (word a module so it can be followed by ear)
    "MODEL_CHAT_CLASS": "claude-haiku-5-5",  # call 12 (class of a teacher's question to her mentor)
    "MODEL_CHAT": "claude-sonnet-5-5",  # call 13 (draft of a reply from approved material)
    "MODEL_ASSIST": "claude-haiku-5-5",  # call 14 (the role-scoped assistant's answer)
    "MODEL_PAPER_READ": "claude-haiku-5-5",  # call 16 (Papers page: read the printed questions)
    "MODEL_SCAN": "claude-haiku-5-5",  # call 15 (pilot demo ingest: header and name scan), offline
    "MODEL_CHECK": "claude-haiku-5-5",
    "MODEL_READ": "claude-haiku-5-5",
    "MODEL_READ_RETRY": "claude-sonnet-5-5",
}


def judge_mode() -> bool:
    """True when this deployment is the judge-mode demo. Decided by the server, never a request."""
    return os.environ.get("JUDGE_MODE", "0") == "1"  # off unless the demo deployment sets it


def dev_testing() -> bool:
    """True on a developer's machine that wants testing shortcuts (such as Approve all entered in
    Enter check). Off unless .env sets DEV_TESTING=1; never set it on a public deployment."""
    return os.environ.get("DEV_TESTING", "0").strip().lower() in ("1", "true", "yes")


def practice_skip_checker() -> bool:
    """True when a Practice Class child's line skips call 7. The code validators and the pre-filter
    still run on every AI line; only the model check is left out. Off unless .env turns it on."""
    return os.environ.get("PRACTICE_SKIP_CHECKER", "0").strip().lower() in ("1", "true", "yes")


def practice_ai_intents() -> frozenset[str] | None:
    """Which kinds of child line call 1 writes. None (the default, or "all") means every kind. A
    list such as "explain,work_aloud" means only those: any other line is the engine's template.
    Children who answer or react alongside the first speaker always use templates."""
    raw = os.environ.get("PRACTICE_AI_INTENTS", "all").strip().lower()
    if raw in ("", "all"):
        return None
    return frozenset(x.strip() for x in raw.split(",") if x.strip())


def model_for(env_var: str) -> str:
    return os.environ.get(env_var) or DEFAULT_MODELS[env_var]


@dataclass(frozen=True)
class CallPolicy:
    """How one call behaves at run time. Live turns retry at most once."""

    timeout_s: float
    max_retries: int
    effort: str  # low | medium | high  (set explicitly: defaults differ per model)
    max_tokens: int
    # "off" turns thinking off where a call is a short, rule-bound job and latency matters. See
    # thinking_param: the API spells it differently per model. None leaves adaptive thinking on.
    thinking: str | None = None


# Lowest effort that passes the call's eval (tuned in P04 and P13); live turns are short.
POLICIES: dict[str, CallPolicy] = {
    "c01_child_voice": CallPolicy(6, 1, "low", 400, thinking="off"),
    "c02_move_label": CallPolicy(6, 1, "low", 400, thinking="off"),
    "c03_feedback": CallPolicy(timeout_s=30, max_retries=1, effort="medium", max_tokens=2500),
    "c04_method_capture": CallPolicy(timeout_s=45, max_retries=2, effort="medium", max_tokens=3000),
    "c05_track_draft": CallPolicy(timeout_s=120, max_retries=2, effort="high", max_tokens=8000),
    "c06_digest": CallPolicy(30, 2, "low", 1200, thinking="off"),
    "c07_checker": CallPolicy(6, 1, "low", 800, thinking="off"),
    "c08_answer_reading": CallPolicy(timeout_s=20, max_retries=1, effort="low", max_tokens=600),
    "c10_demo_teacher": CallPolicy(10, 1, "low", 400, thinking="off"),
    "c11_sprite_author": CallPolicy(timeout_s=60, max_retries=2, effort="medium", max_tokens=2500),
    "c12_chat_classify": CallPolicy(10, 1, "low", 200, thinking="off"),
    "c17_feedback_review": CallPolicy(10, 1, "low", 500, thinking="off"),
    "c18_module_narration": CallPolicy(20, 1, "low", 1500, thinking="off"),
    "c13_chat_reply": CallPolicy(timeout_s=40, max_retries=1, effort="medium", max_tokens=1500),
    "c14_assistant_answer": CallPolicy(timeout_s=30, max_retries=1, effort="low", max_tokens=1200),
    "c16_paper_read": CallPolicy(timeout_s=40, max_retries=1, effort="low", max_tokens=3000),
    "c15_pilot_sheet_scan": CallPolicy(timeout_s=30, max_retries=1, effort="low", max_tokens=1000),
}


def thinking_param(model: str, policy: CallPolicy) -> dict[str, str] | None:
    """The `thinking` request value for this model, or None to send nothing.

    Haiku 5.5 takes {type: disabled}; Sonnet 5.5 rejects that and takes {type: between_tools}
    instead (both only at effort high or below); Opus 5.5 cannot switch thinking off.
    """
    if policy.thinking != "off":
        return None
    if "haiku" in model:
        return {"type": "disabled"}
    if "sonnet" in model:
        return {"type": "between_tools"}
    return None


def ai_mode() -> str:
    """live, record, recorded, stub, or off (every call fails as if the service is unreachable)."""
    mode = os.environ.get("AI_MODE", "recorded")
    if mode not in {"recorded", "live", "record", "stub", "off"}:
        raise ValueError(f"AI_MODE must be recorded, live, record, stub or off, not {mode!r}")
    return mode


def budget_total_usd() -> float:
    return float(os.environ.get("AI_BUDGET_USD_TOTAL") or 350)


def budget_daily_usd() -> float:
    return float(os.environ.get("AI_BUDGET_USD_DAILY") or 40)


def budget_hard_usd() -> float:
    return float(os.environ.get("AI_BUDGET_USD_HARD") or 500)


def load_env(path: str | None = None) -> None:
    """Read KEY=VALUE lines from .env into os.environ without overriding what is already set.

    Called by entry points (the API, scripts, eval runners), never at import, so tests stay
    independent of a developer's .env. Values are never printed.
    """
    from pathlib import Path

    env = Path(path) if path else Path(__file__).resolve().parents[1] / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.split(" #")[0].strip().strip("\"'")
        if value:
            os.environ.setdefault(key.strip(), value)
