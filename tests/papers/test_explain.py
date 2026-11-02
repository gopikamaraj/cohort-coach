"""Why each question is on a paper: lines made by code from facts the paper already holds."""

from __future__ import annotations

from services.papers import explain
from services.papers import generator as gen
from services.papers.rules import seed_rules

RULES = seed_rules()


def paper(profile: gen.Profile) -> dict:
    ref = gen.CheckRef("c-x:1", "pre", "A", "3A", 1)
    return gen.generate_paper(ref, profile, RULES, "standard_10_5", 1, 7).to_dict()


def keys(lines: list[dict]) -> list[str]:
    return [line["key"] for line in lines]


def test_an_anchor_says_it_is_the_same_on_every_paper_and_names_its_rule_and_skill() -> None:
    body = paper(gen.Profile("baseline", {}, (), "en"))
    anchor = next(i for i in body["items"] if i["is_anchor"])
    lines = explain.why(body, anchor)
    assert (
        keys(lines)[0] == "ph.why.rule"
        and "ph.why.anchor" in keys(lines)
        and "ph.why.skill" in keys(lines)
    )
    rule = lines[0]["params"]
    assert rule["template"] == anchor["template"] and rule["version"] == body["rules_version"]


def test_an_adaptive_item_from_a_past_check_says_how_many_children_never_a_percentage() -> None:
    body = paper(gen.profile_from_counts({"SUB-SFL": 9}, 18, "en", built_from=("c-x:1",)))
    adaptive = next(i for i in body["items"] if not i["is_anchor"] and i["competency"] == "C3")
    line = next(w for w in explain.why(body, adaptive) if w["key"].startswith("ph.why.adaptive"))
    assert line["key"] == "ph.why.adaptive_past" and line["params"] == {"n": 9, "checked": 18}


def test_the_profile_source_changes_the_reason_for_an_adaptive_item() -> None:
    base = paper(gen.Profile("baseline", {}, (), "en"))
    item = next(i for i in base["items"] if not i["is_anchor"])
    assert "ph.why.adaptive_baseline" in keys(explain.why(base, item))
    intake = {**base, "profile": {**base["profile"], "source": "intake"}}
    assert "ph.why.adaptive_intake" in keys(explain.why(intake, item))


def test_the_errors_an_item_can_show_are_listed_and_an_item_with_none_says_so() -> None:
    body = paper(gen.Profile("baseline", {}, (), "en"))
    for it in body["items"]:
        lines = explain.why(body, it)
        probes = [w for w in lines if w["key"] == "ph.why.probes"]
        if it["wrong"]:
            assert probes and probes[0]["codes"] == sorted(it["wrong"])
        else:
            assert "ph.why.no_probe" in keys(lines)


def test_a_hand_edited_paper_and_an_imported_one_say_so() -> None:
    body = paper(gen.Profile("baseline", {}, (), "en"))
    assert "ph.why.hand" in keys(explain.why({**body, "custom": True}, body["items"][0]))
    imported = {**body, "source": "imported_pdf"}
    lines = explain.why(imported, body["items"][2])
    assert keys(lines)[0] == "ph.why.imported" and "ph.why.anchor" not in keys(lines)


def test_attach_leaves_the_stored_items_alone() -> None:
    body = paper(gen.Profile("baseline", {}, (), "en"))
    out = explain.attach(body)
    assert all("why" in i for i in out) and all("why" not in i for i in body["items"])


def test_the_rule_line_says_what_the_template_is_in_the_words_of_the_rules() -> None:
    body = paper(gen.Profile("baseline", {}, (), "en"))
    first = body["items"][0]
    skills = {t.id: t.skill for t in RULES.templates}
    line = explain.why(body, first, skills)[0]
    assert line["params"]["what"] == "Write a 3-digit number said aloud"
    # without the rules to hand, the id stands in, never a blank
    assert explain.why(body, first)[0]["params"]["what"] == first["template"]
