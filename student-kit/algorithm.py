"""
TSPTW Arena — team submission
=============================

This is the ONLY file you upload to the website. Keep everything you need in
this single file (helper functions and classes are fine).
New to the kit? Read GUIDE.md first: what to write, how you are scored, do's and don'ts.

Contract
--------
    solve(instance, time_limit, seed) -> list[int]

* ``instance``   a ``tsptw.Instance`` (see tsptw/instance.py): ``n``, ``coords``,
                 ``tw_start``, ``tw_end``, ``dist`` (numpy) and the fast plain-list
                 mirrors ``dist_list``, ``tw_start_list``, ``tw_end_list``.
* ``time_limit`` seconds you may spend on this instance (5 s for n=50, 10 s for
                 n=100). The server kills the run at time_limit + 1 s and counts it
                 as a failure, so always return in time (use ``Deadline``).
* ``seed``       use it for ALL randomness so a run can be reproduced.
* return         the visit order of all n nodes, starting with the depot 0,
                 e.g. [0, 17, 3, ...]. The return to the depot is implicit.

Rules
-----
* Allowed imports: the Python standard library, ``numpy`` and ``tsptw``.
  No network, subprocesses, threads or multiprocessing (blocked on the server).
* Ready-made solvers (OR-Tools, LKH, SAT/CP solvers, ...) are not allowed.
* Run ``python check_submission.py`` before uploading.

What the starter code does
--------------------------
Out of the box this file visits customers in increasing order of their window
end. That is exactly the C-Greedy FLOOR baseline: uploading it unchanged gets
you REJECTED. Fill in the TODOs below to beat it. The suggested plan follows
the project description:

  Phase 1 (CSP view)          find ANY feasible tour:
                              backtracking + forward checking + MRV/LCV ordering
  Phase 2 (optimisation view) make it SHORT while staying feasible:
                              hill climbing / simulated annealing with 2-opt,
                              or-opt, swap moves

You are free to change the structure completely — only ``solve`` is required.
"""

from __future__ import annotations

import math  # noqa: F401  (you will probably need it for simulated annealing)
import random

from tsptw import EPS, Deadline, Instance, check_tour, tour_length

# =============================================================================
# Small helpers (provided)
# =============================================================================


def arrival(instance: Instance, t: float, i: int, j: int) -> float:
    """Service start time at node j when leaving node i at time t (waits if early)."""
    a = t + instance.dist_list[i][j]
    start = instance.tw_start_list[j]
    return a if a > start else start


def reachable(instance: Instance, t: float, i: int, j: int) -> bool:
    """Can we go from i (at time t) to j and still start service before u_j?"""
    return t + instance.dist_list[i][j] <= instance.tw_end_list[j] + EPS


def is_feasible(instance: Instance, tour: list[int]) -> bool:
    """O(n) full check using the official evaluator.

    TODO(speed): local search calls this a lot. Once everything works, write
    an incremental check that only re-simulates the part of the tour that a
    move changed (positions before the first changed index keep their times).
    """
    return check_tour(instance, tour).feasible


def tour_cost(instance: Instance, tour: list[int]) -> float:
    """Total length of the closed tour (official definition)."""
    return tour_length(instance, tour)


# =============================================================================
# Phase 1 — find a FEASIBLE tour (constraint satisfaction view)
# =============================================================================


def order_candidates(instance: Instance, current: int, t: float, unvisited: set[int]) -> list[int]:
    """Return the unvisited nodes to try next, best first (value ordering).

    Starter: earliest window end first (this is the C-Greedy rule).

    TODO(MRV): prefer the most constrained node, e.g. the one with the least
    slack ``tw_end[j] - arrival(t, current, j)``. Nodes that are not
    ``reachable`` any more should not be tried at all.
    TODO(LCV, optional): among similar candidates, prefer the one that leaves
    the remaining nodes the most room (e.g. arrives earliest / shortest edge).
    """
    return sorted(unvisited, key=lambda j: instance.tw_end_list[j])


def forward_check(instance: Instance, current: int, t: float, unvisited: set[int]) -> bool:
    """Return False if the partial tour ending at ``current`` (time ``t``) can
    already be proven to be a dead end.

    Starter: never prunes.

    TODO(forward checking): after placing ``current`` at time ``t``, every
    unvisited node must still be reachable before its window closes. If some
    node j has ``t + dist[current][j] > tw_end[j]`` (+EPS), no completion can
    be feasible (triangle inequality holds for Euclidean distances), so prune.
    Ideas for stronger pruning: a node whose window closes before the window
    of another node opens must be visited first, ...
    """
    return True


def construct_feasible_tour(instance: Instance, deadline: Deadline, rng: random.Random) -> list[int] | None:
    """Return a feasible tour, or None if none was found in the budget.

    Starter: no search at all — follows ``order_candidates`` greedily from the
    depot and returns the result even if it is infeasible.

    TODO(backtracking): turn this into a depth-first search.
      * state = (partial tour, current time, set of unvisited nodes)
      * expand children in the order given by ``order_candidates``
      * skip children that are not ``reachable`` and prune with ``forward_check``
      * undo the choice when a subtree fails (that's the backtracking)
      * stop at ``deadline`` and also give the search a node/backtrack budget
        (or restart with randomised tie-breaking using ``rng``) so a single
        unlucky branch cannot eat the whole time limit
      * prefer an explicit stack over recursion if you hit recursion limits
    """
    tour, t, current = [0], 0.0, 0
    unvisited = set(range(1, instance.n))
    while unvisited:
        nxt = order_candidates(instance, current, t, unvisited)[0]
        t = arrival(instance, t, current, nxt)
        tour.append(nxt)
        unvisited.remove(nxt)
        current = nxt
    return tour


# =============================================================================
# Phase 2 — make it SHORT (optimisation view)
# =============================================================================


def random_neighbor(tour: list[int], rng: random.Random) -> list[int]:
    """Return a NEW tour obtained by a small random change. Never move index 0.

    Starter: no move.

    TODO(moves): implement a few neighbourhoods and pick one at random:
      * 2-opt: reverse a segment tour[i:j+1]
      * or-opt / relocate: move a node (or a short segment) to another position
      * swap: exchange two nodes
    In TSPTW short moves (relocate, or-opt) keep feasibility far more often
    than long 2-opt reversals — measure it!
    """
    return tour[:]


def local_search(instance: Instance, tour: list[int], deadline: Deadline, rng: random.Random) -> list[int]:
    """Improve ``tour`` until the deadline and return the best feasible tour found.

    Starter: returns the input unchanged.

    TODO(hill climbing): repeatedly take ``random_neighbor``; keep it if it is
    feasible and shorter.
    TODO(simulated annealing): also accept worse feasible tours with
    probability exp(-delta / T) and cool T over time (e.g. geometric cooling
    tied to ``deadline.elapsed()``). Always remember the best tour seen.
    Ideas: allow infeasible tours with a penalty on lateness, restarts,
    computing the length change of a move in O(1) instead of O(n).
    """
    return tour


# =============================================================================
# Entry point — DO NOT RENAME
# =============================================================================


def solve(instance: Instance, time_limit: float, seed: int) -> list[int]:
    rng = random.Random(seed)  # for numpy randomness use np.random.default_rng(seed)
    deadline = Deadline(time_limit)  # stops at 95% of the budget

    tour = construct_feasible_tour(instance, deadline, rng)
    if tour is None:  # always return *something*: an infeasible tour is a failure, a crash too
        tour = [0] + sorted(range(1, instance.n), key=lambda j: instance.tw_end_list[j])

    if is_feasible(instance, tour):
        tour = local_search(instance, tour, deadline, rng)
    return tour
