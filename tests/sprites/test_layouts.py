"""Counts are exact by construction: what a layout reports is what the SVG holds."""

from __future__ import annotations

import pytest

from services.api.sprites import layouts as L
from services.api.sprites.items import item_ids, load_item
from services.api.sprites.palette import palette

from .helpers import local, parse, units, with_class

PAL = palette()
BALL = load_item("ball")
STICK = load_item("stick")


def drawn(scene: L.Scene) -> int:
    return len(units(parse(scene.svg)))


# ------------------------------------------------------------------------------- counts
@pytest.mark.parametrize("n", range(0, 101))
def test_row_and_scatter_draw_exactly_n(n: int) -> None:
    for fn in (L.row, L.scatter):
        s = fn(BALL, n, PAL, 7)
        assert s.report["count_drawn"] == n == drawn(s)


@pytest.mark.parametrize("n", range(0, 101))
def test_bundle_group_draws_exactly_n_in_whole_bundles_of_ten(n: int) -> None:
    s = L.bundle_group(STICK, n, PAL)
    root = parse(s.svg)
    assert s.report["count_drawn"] == n == len(units(root))
    assert (s.report["bundles"], s.report["loose"]) == divmod(n, 10)
    assert len(list(with_class(root, "bundle"))) == n // 10


@pytest.mark.parametrize("n", range(0, 100))
def test_place_value_mat_columns_match_the_digits(n: int) -> None:
    s = L.place_value_mat(STICK, n, PAL)
    root = parse(s.svg)
    bundles = list(with_class(root, "bundle"))
    in_bundles = {id(u) for b in bundles for u in units(b)}
    loose = [u for u in units(root) if id(u) not in in_bundles]
    assert (len(bundles), len(loose)) == divmod(n, 10) == (s.report["tens"], s.report["ones"])
    assert len(units(root)) == n == s.report["count_drawn"]


def test_every_bundle_holds_exactly_ten_units() -> None:
    for n in (10, 47, 100):
        for fn in (L.bundle_group, L.place_value_mat):
            if fn is L.place_value_mat and n > 99:
                continue
            root = parse(fn(STICK, n, PAL).svg)
            for b in with_class(root, "bundle"):
                assert len(units(b)) == 10


@pytest.mark.parametrize("n", range(0, 21))
def test_ten_frame_draws_exactly_n_counters(n: int) -> None:
    s = L.ten_frame(load_item("counter"), n, PAL)
    assert s.report["count_drawn"] == n == drawn(s)
    assert s.report["frames"] == (1 if n <= 10 else 2)


@pytest.mark.parametrize(("r", "c"), [(1, 1), (2, 5), (3, 4), (7, 9), (10, 10), (20, 5)])
def test_grid_array_draws_r_times_c(r: int, c: int) -> None:
    s = L.grid_array(BALL, r, c, PAL)
    assert s.report["count_drawn"] == r * c == drawn(s)


@pytest.mark.parametrize(
    ("total", "marked"),
    [(1, 0), (1, 1), (10, 3), (52, 29), (45, 19), (100, 100), (99, 0), (64, 28)],
)
def test_cross_out_draws_N_and_marks_exactly_n(total: int, marked: int) -> None:
    s = L.cross_out(BALL, total, marked, PAL)
    root = parse(s.svg)
    assert drawn(s) == total == s.report["count_drawn"]
    assert len(list(with_class(root, "x"))) == marked == s.report["marked"]
    assert len(list(with_class(root, "mk"))) == marked  # one cross group per marked unit


@pytest.mark.parametrize(
    ("a", "b"), [(0, 0), (1, 0), (0, 9), (23, 45), (50, 50), (100, 100), (7, 3)]
)
def test_two_groups_draw_a_plus_b_with_group_b_framed(a: int, b: int) -> None:
    s = L.two_groups(BALL, a, b, PAL, 3)
    root = parse(s.svg)
    ga, gb = (next(e for e in root.iter() if e.attrib.get("class") == c) for c in ("ga", "gb"))
    assert (len(units(ga)), len(units(gb))) == (a, b) and drawn(s) == a + b
    assert any(local(e.tag) == "rect" and "frame" in e.attrib.get("class", "") for e in gb)


@pytest.mark.parametrize(
    "lo_hi_marks", [(0, 10, [3]), (0, 20, [0, 20]), (30, 100, [31, 50, 99]), (0, 100, [])]
)
def test_number_line_ticks_and_marks(lo_hi_marks: tuple[int, int, list[int]]) -> None:
    lo, hi, marks = lo_hi_marks
    s = L.number_line(lo, hi, marks, PAL)
    root = parse(s.svg)
    ticks = sum(e.attrib["d"].count("M") for e in with_class(root, "tick"))
    assert ticks == hi - lo + 1 == s.report["ticks"]
    assert len(units(root)) == len(marks) == s.report["count_drawn"]


def test_bar_model_draws_one_rect_per_part_in_proportion() -> None:
    s = L.bar_model([3, 5, 2], PAL)
    root = parse(s.svg)
    rects = [e for e in units(root) if local(e.tag) == "rect"]
    widths = [int(e.attrib["width"]) for e in rects]
    assert len(rects) == 3 == s.report["count_drawn"] and s.report["total"] == 10
    assert widths[1] > widths[0] > widths[2]  # 5 > 3 > 2


@pytest.mark.parametrize("item_id", item_ids())
@pytest.mark.parametrize("n", [1, 5, 10, 23, 45, 100])
def test_every_item_in_every_counting_layout(item_id: str, n: int) -> None:
    spec = load_item(item_id)
    for scene in (L.row(spec, n, PAL), L.scatter(spec, n, PAL, 1), L.bundle_group(spec, n, PAL),
                  L.cross_out(spec, n, n // 2, PAL)):  # fmt: skip
        assert scene.report["count_drawn"] == n == drawn(scene), (
            item_id,
            n,
            scene.report["layout"],
        )
    if n <= 20:
        assert drawn(L.ten_frame(spec, n, PAL)) == n
    if n <= 99:
        assert drawn(L.place_value_mat(spec, n, PAL)) == n


# ---------------------------------------------------------------------------- non-overlap
def boxes(scene: L.Scene) -> list[tuple[int, int, int]]:
    return [
        (int(u.attrib["x"]), int(u.attrib["y"]), int(u.attrib["width"]))
        for u in units(parse(scene.svg))
    ]


@pytest.mark.parametrize("n", [1, 7, 23, 45, 100])
@pytest.mark.parametrize("seed", range(5))
def test_scatter_never_overlaps_and_stays_inside(n: int, seed: int) -> None:
    b = boxes(L.scatter(BALL, n, PAL, seed))
    assert len(b) == n
    for i, (x, y, s) in enumerate(b):
        assert 0 <= x and 0 <= y and x + s <= L.W and y + s <= L.H
        for x2, y2, s2 in b[i + 1 :]:
            assert x + s <= x2 or x2 + s2 <= x or y + s <= y2 or y2 + s2 <= y


def test_scatter_is_deterministic_in_its_seed_and_varies_with_it() -> None:
    assert L.scatter(BALL, 30, PAL, 5).svg == L.scatter(BALL, 30, PAL, 5).svg
    assert L.scatter(BALL, 30, PAL, 5).svg != L.scatter(BALL, 30, PAL, 6).svg


# ---------------------------------------------------------------------------- bad input
@pytest.mark.parametrize("n", [-1, 101, 2.5, True, "7"])
def test_a_bad_count_is_refused(n: object) -> None:
    with pytest.raises(L.LayoutError):
        L.row(BALL, n, PAL)  # type: ignore[arg-type]


def test_other_bad_inputs_are_refused() -> None:
    for call in (
        lambda: L.place_value_mat(STICK, 100, PAL),
        lambda: L.ten_frame(BALL, 21, PAL),
        lambda: L.cross_out(BALL, 5, 6, PAL),
        lambda: L.cross_out(BALL, 0, 0, PAL),
        lambda: L.number_line(5, 5, [], PAL),
        lambda: L.number_line(0, 10, [11], PAL),
        lambda: L.bar_model([], PAL),
        lambda: L.bar_model([3, 0], PAL),
        lambda: L.grid_array(BALL, 0, 3, PAL),
    ):
        with pytest.raises(L.LayoutError):
            call()
