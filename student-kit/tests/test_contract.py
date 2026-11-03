"""Contract tests: if these pass, the website can run your algorithm.py.

    pytest -q                                   # tests algorithm.py
    TSPTW_ALGO=baselines/greedy.py pytest -q    # tests another file
"""

import time

import numpy as np
import pytest
from conftest import ALGO, ROOT

from run_local import load_module
from tsptw import TRACKS, Instance, check_source, check_tour, generate_instance, load_set, normalize_tour


@pytest.fixture(scope="module")
def algo():
    return load_module(ALGO)


@pytest.fixture(scope="module", params=list(TRACKS))
def instance(request):
    return load_set(ROOT / "instances" / "public" / f"{request.param}.json").instances[0]


def test_static_check_passes():
    assert check_source(ALGO.read_bytes()) == []


def test_returns_a_valid_tour(algo, instance):
    tour = algo.solve(instance, 1.0, 0)
    order = normalize_tour(tour, instance.n)  # raises if not a permutation starting at 0
    assert order[0] == 0 and len(order) == instance.n


def test_respects_the_time_limit(algo, instance):
    limit = 0.5
    start = time.perf_counter()
    algo.solve(instance, limit, 1)
    elapsed = time.perf_counter() - start
    assert elapsed <= limit + 1.0, f"took {elapsed:.2f}s with time_limit={limit}s (server kills at +1s)"


def test_solves_an_easy_instance():
    inst, _ = generate_instance(20, "easy", np.random.default_rng(42))
    wide = Instance("wide", inst.coords, [0.0] * inst.n, [1e6] * inst.n)  # no binding windows
    tour = load_module(ALGO).solve(wide, 1.0, 0)
    assert check_tour(wide, tour).feasible


def test_handles_tiny_instances(algo):
    tiny = Instance("tiny", [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]], [0.0, 0.0, 0.0], [100.0, 100.0, 100.0])
    assert check_tour(tiny, algo.solve(tiny, 0.5, 0)).feasible
