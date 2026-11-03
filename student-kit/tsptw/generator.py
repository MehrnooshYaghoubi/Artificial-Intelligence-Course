"""Random TSPTW instances, a numpy port of the PIP benchmark generator.

Source: github.com/jieyibi/PIP-constraint, ``POMO+PIP/envs/TSPTWEnv.py``
(``get_random_problems`` + the normalisation in ``load_problems``).

* easy / medium: JAMPR-style windows (Falkner & Schmidt-Thieme), window
  length = time_factor * U(.5, .75) (easy) or U(.1, .2) (medium).
* hard: Da Silva & Urrutia style. A random tour is drawn first and every
  window is placed around its arrival time on that tour, so at least one
  feasible tour is guaranteed (returned as ``witness``).

Values are rounded to 6 decimals so a JSON round-trip is exact.
"""

from __future__ import annotations

import math

import numpy as np

from .instance import Instance, distance_matrix

HARDNESS = ("easy", "medium", "hard")
DECIMALS = 6


def _round_up(x: float) -> float:
    q = 10**DECIMALS
    return math.ceil(x * q) / q


def generate_instance(
    n: int, hardness: str, rng: np.random.Generator, name: str = "", track: str = ""
) -> tuple[Instance, list[int] | None]:
    """Return ``(instance, witness)``; ``witness`` is a feasible tour for hard
    instances and ``None`` otherwise."""
    if hardness not in HARDNESS:
        raise ValueError(f"hardness must be one of {HARDNESS}")
    coord_factor, loc_factor = 100.0, 100.0
    witness = None

    if hardness == "hard":
        max_tw_size = 100.0
        xy = rng.random((n, 2)) * coord_factor
        travel = distance_matrix(xy)
        perm = [0] + (rng.permutation(n - 1) + 1).tolist()
        tw = np.zeros((n, 2))
        tw[0] = [0.0, 1000.0 * coord_factor]
        total = 0.0
        for prev, cur in zip(perm, perm[1:]):
            total += travel[prev, cur]
            lb = rng.random() * (max_tw_size / 2) + (total - max_tw_size / 2)
            ub = rng.random() * (max_tw_size / 2) + total
            tw[cur] = [lb, ub]
        witness = perm
    else:
        time_factor = n * 55.0
        service_window = int(time_factor * 2)
        dura = (0.5, 0.75) if hardness == "easy" else (0.1, 0.2)
        xy = rng.uniform(size=(n, 2)) * loc_factor
        tw_start = rng.integers(0, service_window // 2, size=n).astype(np.float64)
        tw_start[0] = 0.0
        duration = np.around(time_factor * rng.uniform(dura[0], dura[1], size=n))
        duration[0] = service_window
        tw_end = np.minimum(tw_start + duration, service_window).astype(int).astype(np.float64)
        tw = np.stack([tw_start, tw_end], axis=1)

    # PIP normalisation: same unit for space and time.
    xy = np.round(xy / loc_factor, DECIMALS)
    tw_start = np.round(tw[:, 0] / loc_factor, DECIMALS)
    tw_end = np.round(tw[:, 1] / loc_factor, DECIMALS)
    # Depot upper bound = max(node ub + dist to depot), as in PIP.
    d0 = distance_matrix(xy)[0]
    tw_end[0] = _round_up(float((d0[1:] + tw_end[1:]).max()))

    inst = Instance(name=name, coords=xy, tw_start=tw_start, tw_end=tw_end, track=track)
    return inst, witness
