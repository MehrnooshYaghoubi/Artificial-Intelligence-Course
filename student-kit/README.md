# TSPTW Arena — student kit

> **New here? Read [`GUIDE.md`](GUIDE.md) first.** It explains what every file is for, what you
> write, how the website scores you, and the do's and don'ts. This README is the short reference.

Design your own solver for the **Travelling Salesman Problem with Time Windows**
and climb the leaderboard. You upload **one file, `algorithm.py`**. The server
runs it on hidden instances and ranks it against the other teams and the
baselines.

```bash
pip install -r requirements.txt
pytest -q                      # contract tests: can the website run your file?
python check_submission.py     # the exact upload checks + a smoke run
python run_local.py            # full local evaluation, same metrics as the website
```

## Files

| file | what it is |
|---|---|
| `algorithm.py` | **your solver, the only file you upload.** Starts as the C-Greedy floor, with TODOs |
| `tsptw/` | helper package installed identically on the server. Import from it, don't modify it |
| `instances/public/` | 10 public instances per track, with reference lengths so you can compute gaps |
| `baselines/greedy.py` | the C-Greedy **floor** you must beat |
| `run_local.py` | evaluates any `solve()` file like the leaderboard and appends rows to a CSV |
| `check_submission.py` | pre-flight check before uploading |
| `tests/` | `pytest` contract tests |

## The problem

There are `n` nodes (50 or 100) with coordinates in the unit square, and node `0` is the depot.
Every node `i` has a time window `[l_i, u_i]`, and travel time equals Euclidean distance.
Starting at the depot at time 0, if `j` is visited right after `i`, then

```
t_j = max(l_j, t_i + d_ij)      # waiting is allowed
t_j <= u_j                      # arriving after the window closes is NOT allowed
```

Find a tour that visits every node once, respects all windows and returns to the
depot, with **minimum total distance**. Instances come from the PIP benchmark
(NeurIPS 2024) generator. In **Hard** instances the windows are built around
a hidden random tour, so a feasible tour always exists, but finding it is the hard
part. Read `tsptw/evaluate.py` to see the exact rules the website uses.

## Contract

```python
def solve(instance: tsptw.Instance, time_limit: float, seed: int) -> list[int]:
    ...  # visit order of all n nodes, starting with 0, e.g. [0, 17, 3, ...]
```

* `instance` provides `n`, `coords`, `tw_start`, `tw_end` and `dist` as read-only numpy
  arrays, plus the plain-list mirrors `dist_list`, `tw_start_list` and `tw_end_list`.
  In Python loops, `inst.dist_list[i][j]` is much faster than `inst.dist[i, j]`.
* `time_limit` is the per-instance budget. Use `tsptw.Deadline(time_limit)` and return in
  time: the server **kills the run at `time_limit + 1 s`**, and a killed run counts as a failure.
* `seed`: use it for all randomness.

### Rules

* Allowed imports: the Python standard library, `numpy` and `tsptw`. Network,
  subprocesses, threads, multiprocessing, `ctypes`, `importlib`, `exec`/`eval` are rejected on upload
  and blocked on the server. The server runs Python 3.12 with numpy 2.5.
* Ready-made solvers (OR-Tools, LKH, SAT/CP solvers, …) are not allowed in your algorithm.
* The file must be a single `.py` of at most 256 KB.

## Scoring

| track | nodes | difficulty | time limit / instance |
|---|---|---|---|
| `50_medium` | 50 | Medium | 5 s |
| `50_hard` | 50 | Hard | 5 s |
| `100_medium` | 100 | Medium | 10 s |
| `100_hard` | 100 | Hard | 10 s |

Each instance is run with several seeds. Each (instance, seed) pair is one *run*.

* **Failure rate** is the % of runs without a feasible tour. Crashes, timeouts, invalid tours
  and tours that break a window all count as failures.
* **Gap** is the mean over **feasible runs only** of `(L − L_ref) / L_ref × 100`, where `L_ref`
  is the reference length from long LKH-3 runs.
* **Overall** is the mean of the four per-track failure rates, and separately of the four gaps.
* **Ranking** sorts by failure rate first, then gap, then average time (as in the project description:
  reduce failures first, then improve quality).
* **Floor:** a submission is ACCEPTED only if it is strictly better than C-Greedy on
  (failure rate, gap). Anything else is REJECTED and shown below the red line.
* **Your last evaluated submission is your entry**, even if it is worse than an earlier one.
  Uploads that fail the static checks, or crash in the smoke test, don't count as a try.

The live leaderboard uses a hidden *dev* set. The final ranking re-runs every team's
last submission on a separate hidden *final* set with more seeds, so don't overfit
the public instances.

## Using `run_local.py` for your report

```bash
python run_local.py --track 50_hard --seeds 3                  # one track
python run_local.py --workers 4 --time-scale 0.2               # fast iteration (not official timing)
python run_local.py --label full        --csv results.csv      # baseline row of your ablation
python run_local.py --label no-fc       --csv results.csv --algo variants/no_fc.py
```

Every run is appended to the CSV (label, track, instance, seed, status, length, gap, time),
so one command reproduces your tables, which is deliverable #1 of the project. For official
numbers use `--workers 1` and `--time-scale 1`.

## Suggested path (see the TODOs in `algorithm.py`)

1. **Feasibility first.** Use backtracking with forward checking (prune as soon as some unvisited node
   can't be reached before its window closes), plus MRV-style ordering (least slack first).
   Give the search a budget or restarts so one bad branch can't eat the time limit.
2. **Then length.** Hill climbing, then simulated annealing with relocate / or-opt / 2-opt / swap moves,
   keeping only feasible tours or penalising lateness.
3. **Make it fast.** Use incremental feasibility checks, O(1) length deltas and the `*_list` mirrors.
4. **Measure every change** with `run_local.py --label ... --csv ...`. That's your ablation study.

## Submitting

Go to the leaderboard website, register your team (1–3 members, student codes, a team
password) and upload `algorithm.py`. You can follow the evaluation live. Each team has one
active evaluation at a time and a daily upload cap.
