"""tsptw — shared helpers for the TSPTW Arena.

The server runs your ``algorithm.py`` next to an identical copy of this
package, so anything you import from here behaves exactly the same locally
and on the leaderboard. Do not modify it.
"""

from .evaluate import EPS, InvalidTour, TourCheck, check_tour, gap, normalize_tour, schedule, tour_length
from .generator import generate_instance
from .instance import Benchmark, Instance, dump_set, load_instance, load_set
from .scoring import Run, Stats, beats_floor, rank_key, summarize
from .submission import check_source
from .timer import Deadline

__version__ = "1.0.0"

# Leaderboard tracks: key -> (n, hardness)
TRACKS: dict[str, tuple[int, str]] = {
    "50_medium": (50, "medium"),
    "50_hard": (50, "hard"),
    "100_medium": (100, "medium"),
    "100_hard": (100, "hard"),
}

# Per-instance time limit (seconds) used by the leaderboard, by node count.
TIME_LIMITS: dict[int, float] = {50: 5.0, 100: 10.0}

__all__ = [
    "EPS",
    "TIME_LIMITS",
    "TRACKS",
    "Benchmark",
    "Deadline",
    "Instance",
    "InvalidTour",
    "Run",
    "Stats",
    "TourCheck",
    "beats_floor",
    "check_source",
    "check_tour",
    "dump_set",
    "gap",
    "generate_instance",
    "load_instance",
    "load_set",
    "normalize_tour",
    "rank_key",
    "schedule",
    "summarize",
    "tour_length",
    "__version__",
]
