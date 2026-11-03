"""C-Greedy — the FLOOR of the leaderboard.

PIP baseline ``greedy_parallel.py --heuristics constraint``: always go to the
unvisited customer whose time window closes first. Because the choice does not
depend on the current position, this is simply the customers sorted by
``tw_end``. Your submission must be strictly better than this (lower failure
rate, or the same failure rate and a lower gap) to be ACCEPTED.
"""

from tsptw import Instance


def solve(instance: Instance, time_limit: float, seed: int) -> list[int]:
    return [0] + sorted(range(1, instance.n), key=lambda j: instance.tw_end_list[j])
