"""Tour validation and scoring — the exact rules the leaderboard uses.

A tour is the visit order of all n nodes starting at the depot (node 0); the
return to the depot is implicit (a trailing 0 is accepted and ignored).

Schedule (PIP benchmark semantics): start at the depot at time 0 and for each
consecutive pair (i, j)

    t_j = max(l_j, t_i + d_ij)        # wait if early
    t_j <= u_j + EPS                  # otherwise the tour is infeasible

The tour length is the sum of Euclidean distances including the return leg.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Integral
from typing import Sequence

from .instance import Instance

EPS = 1e-5


class InvalidTour(ValueError):
    pass


@dataclass(frozen=True)
class TourCheck:
    valid: bool  # a permutation of 0..n-1 starting with 0
    feasible: bool  # valid and every time window respected
    length: float  # closed tour length (inf when not valid)
    late_nodes: int  # number of nodes served after their window closed
    first_late: int | None  # first node that was late, if any
    message: str = ""


def normalize_tour(tour: Sequence[int], n: int) -> list[int]:
    """Return ``tour`` as a list of Python ints, or raise InvalidTour."""
    try:
        items = list(tour)
    except TypeError:
        raise InvalidTour("tour must be a sequence of node indices") from None
    if len(items) == n + 1 and items[-1] == 0:
        items = items[:-1]
    if len(items) != n:
        raise InvalidTour(f"tour has {len(items)} nodes, expected {n}")
    out = []
    for v in items:
        if isinstance(v, bool) or not isinstance(v, Integral):
            raise InvalidTour(f"tour entries must be integers, got {type(v).__name__}")
        out.append(int(v))
    if out[0] != 0:
        raise InvalidTour("tour must start at the depot (node 0)")
    if sorted(out) != list(range(n)):
        raise InvalidTour("tour must visit every node exactly once")
    return out


def schedule(instance: Instance, tour: Sequence[int]) -> list[float]:
    """Service start time at every position of ``tour`` (position 0 = depot at
    t=0). The last element is the arrival time back at the depot."""
    order = normalize_tour(tour, instance.n)
    d, l = instance.dist_list, instance.tw_start_list
    times = [0.0]
    t, prev = 0.0, 0
    for j in order[1:]:
        t = max(l[j], t + d[prev][j])
        times.append(t)
        prev = j
    times.append(t + d[prev][0])
    return times


def tour_length(instance: Instance, tour: Sequence[int]) -> float:
    order = normalize_tour(tour, instance.n)
    d = instance.dist_list
    total = 0.0
    for a, b in zip(order, order[1:] + [0]):
        total += d[a][b]
    return total


def check_tour(instance: Instance, tour: Sequence[int]) -> TourCheck:
    """Validate ``tour`` and compute its length and feasibility."""
    try:
        order = normalize_tour(tour, instance.n)
    except InvalidTour as e:
        return TourCheck(False, False, math.inf, 0, None, str(e))

    d, l, u = instance.dist_list, instance.tw_start_list, instance.tw_end_list
    t, prev, length = 0.0, 0, 0.0
    late, first_late = 0, None
    for j in order[1:]:
        length += d[prev][j]
        t = max(l[j], t + d[prev][j])
        if t > u[j] + EPS:
            late += 1
            if first_late is None:
                first_late = j
        prev = j
    length += d[prev][0]
    if t + d[prev][0] > u[0] + EPS:
        late += 1
        if first_late is None:
            first_late = 0

    msg = "" if late == 0 else f"{late} node(s) served after their time window"
    return TourCheck(True, late == 0, length, late, first_late, msg)


def gap(length: float, ref_length: float) -> float:
    """Percentage gap of ``length`` w.r.t. the reference length."""
    return (length - ref_length) / ref_length * 100.0
