"""The 32 hidden states of an erring child, declared once.

Axis order (place_value, exchange, written_step, habit) and habit value order (none, target,
sibling, no_method) live here and nowhere else. A belief is an array of shape (2, 2, 2, 4) with one
named axis per variable; the flat list of 32 is its row-major flattening, so a state's flat index
is ((P*2 + E)*2 + W)*4 + H. Every conversion between a state map and array coordinates goes
through this module.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

import numpy as np
import numpy.typing as npt

Habit = Literal["none", "target", "sibling", "no_method"]
AXES: tuple[str, ...] = ("place_value", "exchange", "written_step", "habit")
HABITS: tuple[Habit, ...] = ("none", "target", "sibling", "no_method")
SIZES: dict[str, int] = {"place_value": 2, "exchange": 2, "written_step": 2, "habit": len(HABITS)}
SHAPE: tuple[int, ...] = tuple(SIZES[a] for a in AXES)
N_STATES = int(np.prod(SHAPE))  # 32

StateMap = dict[str, int | str]
Vector = npt.NDArray[np.float64]


def value_index(axis: str, value: int | str) -> int:
    """The coordinate of `value` on `axis`."""
    if axis == "habit":
        if value not in HABITS:
            raise ValueError(f"unknown habit {value!r}")
        return HABITS.index(value)
    if value not in (0, 1) or isinstance(value, bool):
        raise ValueError(f"{axis} must be 0 or 1, not {value!r}")
    return int(value)


def coords(state: Mapping[str, int | str]) -> tuple[int, ...]:
    """Array coordinates of a state map, in AXES order."""
    if set(state) != set(AXES):
        raise ValueError(f"a state needs exactly {AXES}, got {sorted(state)}")
    return tuple(value_index(a, state[a]) for a in AXES)


def index(state: Mapping[str, int | str]) -> int:
    """The flat (row-major) index of a state map."""
    return int(np.ravel_multi_index(coords(state), SHAPE))


def from_coords(c: tuple[int, ...]) -> StateMap:
    out: StateMap = {}
    for axis, i in zip(AXES, c, strict=True):
        out[axis] = HABITS[i] if axis == "habit" else int(i)
    return out


def from_index(i: int) -> StateMap:
    return from_coords(tuple(int(x) for x in np.unravel_index(i, SHAPE)))


ALL_STATES: tuple[StateMap, ...] = tuple(from_index(i) for i in range(N_STATES))

# Per-state value of each variable, by flat index (derived from the declaration above).
_GRID = np.array([coords(s) for s in ALL_STATES], dtype=np.int64)
P_OF: npt.NDArray[np.int64] = _GRID[:, AXES.index("place_value")]
E_OF: npt.NDArray[np.int64] = _GRID[:, AXES.index("exchange")]
W_OF: npt.NDArray[np.int64] = _GRID[:, AXES.index("written_step")]
H_OF: npt.NDArray[np.int64] = _GRID[:, AXES.index("habit")]


def habit_of(i: int) -> Habit:
    return HABITS[int(H_OF[i])]


def to_array(flat: Vector) -> Vector:
    """A flat belief of 32 as the named-axis array of shape SHAPE."""
    return np.asarray(flat, dtype=np.float64).reshape(SHAPE)


def to_flat(arr: Vector) -> Vector:
    return np.asarray(arr, dtype=np.float64).reshape(N_STATES)


def mask(**fixed: int | str) -> npt.NDArray[np.bool_]:
    """A flat boolean mask of the states whose named variables take the given values."""
    keep = np.ones(N_STATES, dtype=np.bool_)
    for axis, value in fixed.items():
        if axis not in SIZES:
            raise ValueError(f"unknown variable {axis!r}")
        keep &= _GRID[:, AXES.index(axis)] == value_index(axis, value)
    return keep


def assemble(parts: list[tuple[tuple[str, ...], Vector]]) -> Vector:
    """A 32 x 32 matrix from independent factors. Each part is (axes, array) where the array has
    shape (32, *sizes of those axes): for every start state, a distribution over the next values of
    those axes. The factors are multiplied in AXES order, so the columns are flat next-state
    indices. Every axis must appear in exactly one part."""
    seen = [a for axes, _ in parts for a in axes]
    if sorted(seen) != sorted(AXES):
        raise ValueError(f"each of {AXES} must appear in exactly one part, got {seen}")
    out = np.ones((N_STATES, *SHAPE), dtype=np.float64)
    for axes, arr in parts:
        order = sorted(range(len(axes)), key=lambda k: AXES.index(axes[k]))
        moved = np.transpose(arr, (0, *[k + 1 for k in order]))
        shape = [N_STATES] + [SIZES[a] if a in axes else 1 for a in AXES]
        out = out * moved.reshape(shape)
    return out.reshape(N_STATES, N_STATES)


def pe_cells() -> tuple[tuple[int, int], ...]:
    """The four (place_value, exchange) cells in row-major order, for the one-uniform joint draw."""
    return ((0, 0), (0, 1), (1, 0), (1, 1))


def declaration() -> dict[str, object]:
    """What a serialised belief needs to be read back: the axes and the habit order."""
    return {"axes": list(AXES), "habits": list(HABITS), "shape": list(SHAPE)}
