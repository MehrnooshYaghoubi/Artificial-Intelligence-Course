"""Simulated Annealing Baseline for TSPTW.

A two-phase metaheuristic approach:
1. CSP/Feasibility Phase: Starts with C-Greedy and guides search toward valid time windows.
2. Optimization Phase: Minimizes tour length using 2-Opt, Swap, and Insertion moves
   with dynamic temperature decay.
"""

from __future__ import annotations

import math
import random
import time
from tsptw import Instance


def _get_distance(instance: Instance, u: int, v: int) -> float:
    """Calculates Euclidean distance safely across different instance schemas."""
    if hasattr(instance, "dist_matrix") and instance.dist_matrix is not None:
        return float(instance.dist_matrix[u][v])
    if hasattr(instance, "distance_matrix") and instance.distance_matrix is not None:
        return float(instance.distance_matrix[u][v])
    if hasattr(instance, "dist") and instance.dist is not None:
        return float(instance.dist[u][v])
    if hasattr(instance, "coords") and instance.coords is not None:
        p1, p2 = instance.coords[u], instance.coords[v]
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])
    if hasattr(instance, "x") and hasattr(instance, "y"):
        return math.hypot(instance.x[u] - instance.x[v], instance.y[u] - instance.y[v])
    return 0.0


def _evaluate(tour: list[int], instance: Instance) -> tuple[bool, float, float]:
    """Evaluates tour feasibility, total distance, and tardiness penalty.

    Returns:
        (is_feasible, total_distance, total_tardiness)
    """
    n = len(tour)
    curr_time = 0.0
    total_dist = 0.0
    total_tardiness = 0.0

    tw_start = getattr(instance, "tw_start_list", None) or getattr(instance, "tw_low_list", None)
    tw_end = instance.tw_end_list

    for idx in range(n):
        curr_node = tour[idx]
        next_node = tour[(idx + 1) % n]
        dist = _get_distance(instance, curr_node, next_node)
        total_dist += dist

        if idx + 1 < n:
            arr_time = curr_time + dist
            earliest = float(tw_start[next_node]) if tw_start is not None else 0.0
            curr_time = max(arr_time, earliest)
            latest = float(tw_end[next_node])
            if curr_time > latest:
                total_tardiness += (curr_time - latest)
        else:
            # Return to depot
            arr_time = curr_time + dist
            depot_latest = float(tw_end[0]) if len(tw_end) > 0 else float("inf")
            if arr_time > depot_latest:
                total_tardiness += (arr_time - depot_latest)

    is_feasible = (total_tardiness <= 1e-6)
    return is_feasible, total_dist, total_tardiness


def _energy(is_feasible: bool, dist: float, tardiness: float) -> float:
    """Energy function: heavily penalizes time violations to enforce feasibility first."""
    penalty_weight = 10000.0
    return dist + (penalty_weight * tardiness)


def solve(instance: Instance, time_limit: float, seed: int) -> list[int]:
    """Solves TSPTW instance using adaptive Simulated Annealing."""
    start_time = time.time()
    rng = random.Random(seed)
    n = instance.n

    # Phase 1: Initial solution from C-Greedy (Depot 0 + sorted by deadline)
    initial_tour = [0] + sorted(range(1, n), key=lambda j: instance.tw_end_list[j])
    is_feas, dist, tard = _evaluate(initial_tour, instance)

    best_feasible_tour: list[int] | None = initial_tour if is_feas else None
    best_feasible_cost: float = dist if is_feas else float("inf")

    current_tour = list(initial_tour)
    current_energy = _energy(is_feas, dist, tard)
    best_overall_tour = list(initial_tour)
    best_overall_energy = current_energy

    # Time budget allocation: use up to 85% of time_limit to guarantee safe exit
    time_budget = max(0.5, time_limit * 0.85)

    initial_temp = 150.0
    min_temp = 0.05

    while True:
        elapsed = time.time() - start_time
        if elapsed >= time_budget:
            break

        # Dynamic temperature cooling based on time progress
        progress = elapsed / time_budget
        temp = initial_temp * ((min_temp / initial_temp) ** progress)

        # Phase 2: Neighborhood Exploration (Swap, 2-Opt, Insertion)
        move_type = rng.choice(["2opt", "swap", "insert"])
        i = rng.randint(1, n - 1)
        j = rng.randint(1, n - 1)
        if i == j:
            continue

        cand_tour = list(current_tour)
        if move_type == "2opt":
            low, high = min(i, j), max(i, j)
            cand_tour[low : high + 1] = reversed(cand_tour[low : high + 1])
        elif move_type == "swap":
            cand_tour[i], cand_tour[j] = cand_tour[j], cand_tour[i]
        elif move_type == "insert":
            node = cand_tour.pop(i)
            cand_tour.insert(j, node)

        cand_feas, cand_dist, cand_tard = _evaluate(cand_tour, instance)
        cand_energy = _energy(cand_feas, cand_dist, cand_tard)

        # Track global best feasible solution
        if cand_feas and cand_dist < best_feasible_cost:
            best_feasible_cost = cand_dist
            best_feasible_tour = list(cand_tour)

        # Metropolis Acceptance Criterion
        delta = cand_energy - current_energy
        if delta < 0 or rng.random() < math.exp(-delta / max(temp, 1e-8)):
            current_tour = cand_tour
            current_energy = cand_energy

            if cand_energy < best_overall_energy:
                best_overall_energy = cand_energy
                best_overall_tour = list(cand_tour)

    # Always return best feasible if discovered; otherwise best energy tour
    if best_feasible_tour is not None:
        return best_feasible_tour
    return best_overall_tour
