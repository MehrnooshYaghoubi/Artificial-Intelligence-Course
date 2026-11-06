"""Local Search Baseline (C-Greedy + 2-Opt Search).

Starts from the C-Greedy tour and applies local 2-opt moves to
reduce tour distance while verifying time window constraints.
"""

import math
import random
import time
from tsptw import Instance


def get_distance(instance: Instance, i: int, j: int) -> float:
    """Helper to safely calculate Euclidean distance between two nodes."""
    if hasattr(instance, "dist_matrix"):
        return instance.dist_matrix[i][j]
    if hasattr(instance, "distance_matrix"):
        return instance.distance_matrix[i][j]
    if hasattr(instance, "dist"):
        return instance.dist[i][j]
    if hasattr(instance, "coords"):
        c1, c2 = instance.coords[i], instance.coords[j]
        return math.hypot(c1[0] - c2[0], c1[1] - c2[1])
    if hasattr(instance, "x") and hasattr(instance, "y"):
        return math.hypot(instance.x[i] - instance.x[j], instance.y[i] - instance.y[j])
    return 0.0


def evaluate_tour(tour: list[int], instance: Instance) -> tuple[bool, float]:
    """Calculates feasibility and total length of a tour."""
    curr_time = 0.0
    total_dist = 0.0

    tw_start = getattr(instance, "tw_start_list", None)
    tw_end = instance.tw_end_list

    for idx in range(len(tour)):
        curr_node = tour[idx]
        next_node = tour[(idx + 1) % len(tour)]
        d = get_distance(instance, curr_node, next_node)
        total_dist += d

        if idx + 1 < len(tour):
            arr_time = curr_time + d
            if tw_start is not None and arr_time < tw_start[next_node]:
                curr_time = float(tw_start[next_node])
            else:
                curr_time = arr_time

            if curr_time > tw_end[next_node]:
                return False, total_dist

    return True, total_dist


def solve(instance: Instance, time_limit: float, seed: int) -> list[int]:
    """Solves TSPTW by improving greedy order with 2-Opt local search."""
    start_time = time.time()
    rng = random.Random(seed)

    # 1. Initial order using C-Greedy
    best_tour = [0] + sorted(range(1, instance.n), key=lambda j: instance.tw_end_list[j])
    best_feasible, best_cost = evaluate_tour(best_tour, instance)

    current_tour = list(best_tour)
    n = instance.n

    # 2. Local search exploration within allocated time
    deadline = min(time_limit * 0.75, 5.0)
    while (time.time() - start_time) < deadline:
        i = rng.randint(1, n - 2)
        j = rng.randint(i + 1, n - 1)

        # 2-Opt: reverse segment between i and j
        candidate = current_tour[:i] + list(reversed(current_tour[i : j + 1])) + current_tour[j + 1 :]
        is_feasible, cost = evaluate_tour(candidate, instance)

        if is_feasible:
            if (not best_feasible) or (cost < best_cost):
                best_tour = candidate
                best_cost = cost
                best_feasible = True
                current_tour = candidate
        else:
            if (not best_feasible) and (cost < best_cost):
                best_tour = candidate
                best_cost = cost
                current_tour = candidate

    return best_tour
