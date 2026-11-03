"""Leaderboard metrics (identical on the server and in ``run_local.py``).

* failure rate: % of (instance, seed) runs without a feasible tour — crashes,
  timeouts, invalid output and infeasible tours all count as failures.
* gap: mean of ``(L - L_ref) / L_ref * 100`` over the feasible runs only.
* overall: the mean of the per-track failure rates and of the per-track gaps.
* ranking: failure rate first, then gap, then average time.
* floor: a submission is ACCEPTED only if it is strictly better than the
  C-Greedy floor on (failure rate, gap); time never helps you pass the floor.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Iterable

STATUSES = ("ok", "infeasible", "invalid", "timeout", "crash")
_FAIL_TOL = 1e-9
_GAP_TOL = 1e-6


@dataclass(frozen=True)
class Run:
    track: str
    instance: str
    seed: int
    status: str  # one of STATUSES; only "ok" is a success
    length: float | None = None
    ref_length: float | None = None
    wall_time: float = 0.0

    @property
    def gap(self) -> float | None:
        if self.status != "ok" or self.length is None or not self.ref_length:
            return None
        return (self.length - self.ref_length) / self.ref_length * 100.0


@dataclass(frozen=True)
class Stats:
    track: str
    runs: int
    feasible: int
    failure_rate: float  # percent
    gap: float | None  # percent, None when nothing was feasible
    avg_time: float  # seconds

    def to_dict(self) -> dict:
        return asdict(self)


def track_stats(track: str, runs: Iterable[Run]) -> Stats:
    runs = list(runs)
    if not runs:
        return Stats(track, 0, 0, 100.0, None, 0.0)
    gaps = [g for g in (r.gap for r in runs) if g is not None]
    feasible = sum(1 for r in runs if r.status == "ok")
    return Stats(
        track=track,
        runs=len(runs),
        feasible=feasible,
        failure_rate=100.0 * (len(runs) - feasible) / len(runs),
        gap=sum(gaps) / len(gaps) if gaps else None,
        avg_time=sum(r.wall_time for r in runs) / len(runs),
    )


def summarize(runs: Iterable[Run], tracks: Iterable[str]) -> dict[str, Stats]:
    """Per-track stats for ``tracks`` plus an ``"overall"`` entry."""
    runs = list(runs)
    per = {t: track_stats(t, [r for r in runs if r.track == t]) for t in tracks}
    per["overall"] = overall_stats(per.values())
    return per


def overall_stats(stats: Iterable[Stats]) -> Stats:
    stats = [s for s in stats if s.track != "overall"]
    if not stats:
        return Stats("overall", 0, 0, 100.0, None, 0.0)
    gaps = [s.gap for s in stats if s.gap is not None]
    return Stats(
        track="overall",
        runs=sum(s.runs for s in stats),
        feasible=sum(s.feasible for s in stats),
        failure_rate=sum(s.failure_rate for s in stats) / len(stats),
        gap=sum(gaps) / len(gaps) if gaps else None,
        avg_time=sum(s.avg_time for s in stats) / len(stats),
    )


def rank_key(s: Stats) -> tuple[float, float, float]:
    """Sort key: smaller is better."""
    return (
        round(s.failure_rate, 9),
        s.gap if s.gap is not None else math.inf,
        s.avg_time,
    )


def beats_floor(s: Stats, floor: Stats) -> bool:
    """Strictly better than the floor on failure rate, then gap."""
    if s.failure_rate < floor.failure_rate - _FAIL_TOL:
        return True
    if s.failure_rate > floor.failure_rate + _FAIL_TOL:
        return False
    if s.gap is None:
        return False
    if floor.gap is None:
        return True
    return s.gap < floor.gap - _GAP_TOL
