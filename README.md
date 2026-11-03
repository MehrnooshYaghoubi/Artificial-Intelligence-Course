# Artificial Intelligence Course — Fall 1405

Course project repository for the **Artificial Intelligence** course, **Fall semester 2026**

This repository holds the course project: a competitive solver-design assignment built around the
**Travelling Salesman Problem with Time Windows (TSPTW)**. Student teams design their own search
algorithm, evaluate it locally with the provided kit, and upload it to a leaderboard website where
it is scored on hidden instances and ranked against other teams and a reference baseline.

---

## Overview

| | |
|---|---|
| **Course** | Artificial Intelligence |
| **Semester** | Fall 2026 |
| **Instructor** | Dr. Eskandari |
| **Project topic** | TSPTW Arena — constraint satisfaction + local search |
| **Deliverable** | `algorithm.py` (single file), a short paper-style report, and an ablation study |
| **Teams** | 1–3 members, registered on the leaderboard site |

The project is deliberately open-ended: the course gives you the problem, the evaluation rules and
a baseline to beat, and leaves the algorithm design to you. It exercises the classic AI toolbox
taught in the course — constraint propagation, heuristic search, and stochastic local search —
on a problem where a naive approach fails loudly and visibly.

---

## The problem in one paragraph

There are `n` nodes (50 or 100) placed in the unit square; node `0` is the depot. Each node `i` has
a time window `[l_i, u_i]`, and travel time between two nodes equals their Euclidean distance. You
leave the depot at time 0. Arriving early at a node means waiting until its window opens (free, but
it costs time); arriving after the window **closes** makes the whole tour infeasible. The goal is a
tour that visits every node exactly once, respects every window, returns to the depot, and has
**minimum total distance**. Instances come from the PIP benchmark generator (NeurIPS 2024). On
*Hard* instances the windows are built around a hidden random tour, so a feasible tour is guaranteed
to exist — finding it is the hard part.

The key asymmetry: **a short tour that is late is worth nothing.** Feasibility first, length second.

---

## Repository layout

```
Artificial-Intelligence-Course/
└── student-kit/              the kit handed out to students
    ├── GUIDE.md              long walkthrough: read this first
    ├── README.md             short reference for the kit
    ├── algorithm.py          YOUR solver — the only file you upload
    ├── tsptw/                helper package (identical copy on the server; do not edit)
    │   ├── instance.py       the Instance object
    │   ├── evaluate.py       the official feasibility checker and scorer
    │   ├── generator.py      PIP-style instance generator
    │   ├── scoring.py        failure rate / gap computation
    │   ├── submission.py     the static upload checks
    │   └── timer.py          Deadline helper
    ├── baselines/greedy.py   C-Greedy — the floor you must beat
    ├── instances/public/     public instances with reference lengths
    ├── run_local.py          local evaluation, same metrics as the website
    ├── check_submission.py   pre-flight upload checks + smoke run
    ├── tests/                pytest contract tests
    └── requirements.txt      numpy + pytest
```

> Full details for every file, the API, the do's and don'ts, and the FAQ live in
> [`student-kit/GUIDE.md`](student-kit/GUIDE.md).

---

## Quick start

```bash
cd student-kit
pip install -r requirements.txt

pytest -q                                          # contract tests: can the website run your file?
python run_local.py --time-scale 0.2 --workers 4   # fast iteration while developing
python run_local.py                                # official timing on all public instances
python check_submission.py                         # the exact upload checks the website runs
```

Then upload `algorithm.py` on the leaderboard site and follow the evaluation live.

---

## The contract

```python
def solve(instance: tsptw.Instance, time_limit: float, seed: int) -> list[int]:
    ...  # visit order of all n nodes, starting with the depot, e.g. [0, 17, 3, 42, ...]
```

- `instance` exposes `n`, `coords`, `tw_start`, `tw_end`, `dist` as read-only numpy arrays, plus the
  much faster plain-list mirrors `dist_list`, `tw_start_list`, `tw_end_list` for Python loops.
- `time_limit` is the per-instance budget. Use `tsptw.Deadline(time_limit)`; the server kills a run
  at `time_limit + 1 s` and a killed run counts as a failure.
- `seed` must drive all randomness, so runs are reproducible.
- Allowed imports: the Python standard library, `numpy` and `tsptw` — nothing else. Ready-made
  solvers (OR-Tools, LKH, SAT/CP solvers) are not allowed; the algorithm must be your own design.
- One `.py` file, at most 256 KB. No threads, subprocesses, network, `exec`/`eval`.

---

## Tracks and scoring

| track | nodes | difficulty | time limit / instance |
|---|---|---|---|
| `50_medium` | 50 | Medium | 5 s |
| `50_hard` | 50 | Hard | 5 s |
| `100_medium` | 100 | Medium | 10 s |
| `100_hard` | 100 | Hard | 10 s |

Each (instance, seed) pair is one **run**.

- **Failure rate** — the % of runs with no feasible tour. Crashes, timeouts, invalid output and
  window violations all count as failures.
- **Gap** — mean over *feasible runs only* of `(L − L_ref) / L_ref × 100`, where `L_ref` is a
  reference length from long LKH-3 runs.
- **Overall** — the mean of the four per-track failure rates, and separately of the four gaps.
- **Ranking** — failure rate first, then gap, then average time.
- **Floor** — a submission is ACCEPTED only if it is *strictly* better than C-Greedy on
  (failure rate, gap). The starter file *is* C-Greedy, so uploading it unchanged is REJECTED by
  design.
- **Final ranking** — after the deadline every team's last submission is re-run on a separate,
  larger hidden set with more seeds, so overfitting the public instances does not pay off.

---

## Suggested path through the project

The TODOs in `algorithm.py` follow the order the project description suggests:

1. **Forward checking** — prune a partial tour as soon as any unvisited node can no longer be
   reached before its window closes. A few lines, and the foundation for everything after it.
2. **Backtracking construction** — turn the greedy loop into a real backtracking search with a
   budget or restarts, so one bad branch cannot eat the time limit. This step alone should push the
   failure rate well below C-Greedy's and get you accepted.
3. **Candidate ordering** — MRV-style ordering (least slack / most urgent first) with sensible
   tie-breaks, to cut the amount of backtracking.
4. **Local search** — hill climbing, then simulated annealing over relocate / or-opt / 2-opt / swap
   moves, keeping the best feasible tour. This is what lowers the gap.
5. **Speed** — incremental feasibility checks, O(1) length deltas, and the `*_list` mirrors. More
   iterations in the same budget means better tours.

You are free to discard this structure entirely and write your own algorithm, as long as
`solve(instance, time_limit, seed)` exists and returns a tour.

---

## Reporting and the ablation study

`run_local.py` appends one CSV row per run (label, track, instance, seed, status, length, gap, time),
so the report's tables are reproducible with a handful of commands:

```bash
python run_local.py --label full            --csv results.csv
python run_local.py --label no-forward-chk  --csv results.csv --algo variants/no_fc.py
python run_local.py --label no-annealing    --csv results.csv --algo variants/hill_climb_only.py
```

Group by `label` and `track` to build the tables. Use `--workers 1 --time-scale 1` for any number
you report — parallel workers and scaled time limits are for fast iteration only, not for official
figures.
