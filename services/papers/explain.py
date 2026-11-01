"""Why each question is on a paper, said by code from facts the paper already holds.

No model writes these lines. Each is a key into the strings file plus the numbers or codes to put in
it, so every screen shows it in the teacher's language. The facts: which rule template made the item
(and which version of the rules), whether it is an anchor or an adaptive item, the skill, the class
profile it was built from (a count of children when the profile came from a past check), the errors
the item can show, and the item it twins. Teacher-facing numbers are counts, never percentages.
"""

from __future__ import annotations

from typing import Any

SKILL = {"C1": "papers.skill.C1", "C2": "papers.skill.C2", "C3": "papers.skill.C3"}


def why(
    body: dict[str, Any], item: dict[str, Any], skills: dict[str, str] | None = None
) -> list[dict[str, Any]]:
    """The reasons for one item, in the order a reader wants them."""
    out: list[dict[str, Any]] = []
    imported = body.get("source") == "imported_pdf"
    skill = SKILL.get(str(item.get("competency")))
    if imported:
        out.append({"key": "ph.why.imported", "params": {"n": item["n"]}})
    else:
        out.append(
            {
                "key": "ph.why.rule",
                "params": {
                    "template": item.get("template", ""),
                    # what the template is, in the words of the rules, so nobody has to look it up
                    "what": (skills or {}).get(item.get("template", ""), item.get("template", "")),
                    "version": body.get("rules_version", ""),
                },
            }
        )
    if body.get("custom") and not imported:
        out.append({"key": "ph.why.hand", "params": {}})
    if skill:
        out.append({"key": "ph.why.skill", "skill": skill, "params": {}})
    if not imported:
        out.append(_role(body, item, skill))
        if item.get("twin_of"):
            out.append({"key": "ph.why.twin", "params": {"n": item["twin_of"]}})
    codes = [c for c, answers in (item.get("wrong") or {}).items() if answers]
    if codes:
        out.append({"key": "ph.why.probes", "codes": sorted(codes), "params": {}})
    else:
        out.append({"key": "ph.why.no_probe", "params": {}})
    return out


def _role(body: dict[str, Any], item: dict[str, Any], skill: str | None) -> dict[str, Any]:
    if item.get("is_anchor"):
        return {"key": "ph.why.anchor", "params": {}}
    profile = body.get("profile") or {}
    source = profile.get("source")
    weight = (profile.get("weights") or {}).get(item.get("competency"))
    strength = profile.get("strength")
    if source == "past" and weight and strength:
        # the profile holds the share of the class; a count of children is what a teacher is shown
        return {
            "key": "ph.why.adaptive_past",
            "skill": skill,
            "params": {"n": round(float(weight) * int(strength)), "checked": int(strength)},
        }
    if source == "intake":
        return {"key": "ph.why.adaptive_intake", "skill": skill, "params": {}}
    return {"key": "ph.why.adaptive_baseline", "skill": skill, "params": {}}


def attach(body: dict[str, Any], skills: dict[str, str] | None = None) -> list[dict[str, Any]]:
    """The paper's items, each with its `why`. The stored items are not changed. `skills` maps a
    template id to its description in the rules version the paper was made from."""
    return [{**it, "why": why(body, it, skills)} for it in body.get("items", [])]
