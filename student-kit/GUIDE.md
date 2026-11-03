# Student kit guide: what is going on and what you should do

Read this before anything else in the kit. It covers:
- what each file is for
- what you write
- how the website judges your code
- the mistakes that cost you points

`README.md` is the short reference. This guide is the long walkthrough.

---

## 1. The short version

1. You write **one file: `algorithm.py`**. Inside it, **one function** is required:
   `solve(instance, time_limit, seed)`.
2. `solve` receives one TSPTW instance. It must return **the order in which to visit all nodes**,
   starting with the depot `0`.
3. You test on your own machine with the kit's scripts. They score your code **exactly** like the
   website does.
4. You upload **only `algorithm.py`**. Don't upload a zip, the `tsptw/` folder, or any data files.
5. To be accepted you must beat **C-Greedy**, a very simple baseline. The `algorithm.py` you
   received *is* C-Greedy, so uploading it unchanged gets you **REJECTED**. That's on purpose: your
   job is to improve it.

---

## 2. What is in the kit and what you touch

| file / folder | what it is | what you do with it |
|---|---|---|
| `algorithm.py` | your solver. Starts as C-Greedy plus TODO comments | **edit it.** This is the only file you upload |
| `tsptw/` | helper library: instance object, official tour checker, timer | **import it, read it, never edit it.** The server has its own copy, so your edits wouldn't exist there |
| `instances/public/` | 10 public instances per track, each with a reference tour length | use them for testing. Don't hard-code anything about them (see section 10) |
| `baselines/greedy.py` | the C-Greedy floor, 3 lines long | read it. It's the bar you have to beat |
| `run_local.py` | runs any `solve()` on the public instances and prints the same table as the website | **run it** after every change |
| `check_submission.py` | the website's upload checks plus a quick test run | **run it** before every upload |
| `tests/` | `pytest` tests that check your file follows the rules | **run them** (`pytest -q`). You may add your own tests |
| `requirements.txt` | numpy + pytest | `pip install -r requirements.txt` once |
| `README.md` | short reference | look things up there |

You can add your own files next to these: notes, experiment scripts, variants of your algorithm
for the ablation study. The website only ever sees the single file you upload.

---

## 3. The problem, with a tiny example

There are `n` nodes. Node `0` is the depot, and the others are customers. Every node has a position and a
**time window** `[open, close]`. The rules:

- You leave the depot at time **0**. Travel time equals the straight-line distance.
- If you **arrive early**, you **wait** until the window opens. Waiting is free: it costs time, not distance.
- If you **arrive after the window closes**, the whole tour is **infeasible**, and an infeasible tour
  counts as a failure.
- After the last customer you go back to the depot.
- Among feasible tours, the **shortest total distance** wins. The return leg counts.

A 4-node example (you can run it yourself, see below):

```
node   position   window        distances:  0-A = 3   A-B = 4   B-C = 3
0      (0, 0)     [0, 100]                  C-0 = 4   0-B = 5   A-C = 5
A=1    (0, 3)     [5, 6]
B=2    (4, 3)     [6, 10]
C=3    (4, 0)     [0, 13]
```

Tour `[0, 1, 2, 3]`, i.e. depot, then A, then B, then C:

```
leave depot   t = 0
arrive A      t = 3   window opens at 5, so wait     start A at t = 5   (<= 6 ok)
arrive B      t = 5 + 4 = 9                           start B at t = 9   (<= 10 ok)
arrive C      t = 9 + 3 = 12                          start C at t = 12  (<= 13 ok)
back at 0     t = 12 + 4 = 16                                            (<= 100 ok)
length = 3 + 4 + 3 + 4 = 14     feasible
```

Tour `[0, 3, 2, 1]` (the same rectangle walked the other way) also has length **14**, but it reaches
A at t = 11, after A's window closed at 6. It is **infeasible**, so it is worth nothing. In fact this
is the only feasible order of the six possible ones. That is the whole difficulty of the TSPTW: a
short tour is useless if it is late. **First find a feasible tour, then make it short.**

```python
from tsptw import Instance, check_tour, schedule
inst = Instance("example", [[0, 0], [0, 3], [4, 3], [4, 0]], [0, 5, 6, 0], [100, 6, 10, 13])
print(schedule(inst, [0, 1, 2, 3]))    # [0.0, 5.0, 9.0, 12.0, 16.0]
print(check_tour(inst, [0, 3, 2, 1]))  # feasible=False, first_late=1
```

The real instances have 50 or 100 nodes in the unit square, and their windows are generated like those
in the PIP paper. On **Hard** instances the windows are built around a hidden random tour, so a feasible
tour always exists, but most orders are infeasible. **Medium** instances have looser windows, but
length matters more there.

---

## 4. What `solve` receives and what it must return

```python
def solve(instance, time_limit, seed):
    ...
    return [0, 17, 3, 42, ...]   # every node exactly once, starting with 0
```

**`instance`** (a `tsptw.Instance`):

| attribute | meaning |
|---|---|
| `instance.n` | number of nodes including the depot (50 or 100) |
| `instance.dist_list[i][j]` | distance = travel time from i to j (plain Python list, **fast**) |
| `instance.tw_start_list[j]`, `instance.tw_end_list[j]` | window of node j (plain lists, **fast**) |
| `instance.dist`, `instance.tw_start`, `instance.tw_end`, `instance.coords` | the same data as read-only numpy arrays (good for vectorised numpy code, slow in Python loops) |

**`time_limit`** is how many seconds you get for this one instance: **5 s** for n=50 and **10 s** for n=100.
The server kills your run at `time_limit + 1 s`, and a killed run is a failure. Use the provided timer:

```python
from tsptw import Deadline
deadline = Deadline(time_limit)     # stops at 95% of the budget, leaving you a safety margin
while not deadline.expired():
    ...                             # improve your tour
```

**`seed`** is an integer. Create your random generator from it (`random.Random(seed)`), so that you
can reproduce a run.

**What you return** must be a list with every node index exactly once, starting with `0`.

| you return | result |
|---|---|
| `[0, 4, 1, 3, 2]` | valid |
| `[0, 4, 1, 3, 2, 0]` | valid (a trailing 0 is accepted) |
| numpy array of ints, e.g. `np.array([0, 4, 1, 3, 2])` | valid |
| `[4, 1, 3, 2]` (missing the depot) | **invalid**: must start with 0 |
| `[0, 4, 1, 1, 2]` (duplicate / missing node) | **invalid** |
| `[1, 5, 2, 4, 3]` (1-based numbering) | **invalid**: nodes are numbered 0 .. n-1 |
| `[0.0, 4.0, ...]` (floats) | **invalid**: integers only |
| `None` | **invalid** |
| your code raises an exception | counts as a **crash** |

A valid tour that is late somewhere is accepted as an answer, but it counts as a **failure**. So
always return the best thing you have. Even an infeasible tour is better than a crash, because
you'll at least see the breakdown in your results.

---

## 5. What happens when you upload

```
upload algorithm.py
 |
 |-- 1. static checks (instant)   imports, solve() signature, size <= 256 KB
 |       fails -> rejected immediately, does NOT count as a try
 |
 |-- 2. smoke test                your solve() on ONE public instance
 |       crash / timeout / garbage -> error with the full traceback,
 |       does NOT count as a try
 |
 |-- 3. hidden runs               every hidden instance x 2 seeds, each in a fresh,
 |                                locked-down process on the server
 |
 |-- 4. scoring                   with the same code as tsptw/evaluate.py
 |
 `-- 5. the result REPLACES your leaderboard entry, even if it is worse than before
```

- **Hidden instances** are different from the public ones, so you can't tune against them. Crashes in the
  hidden runs show only the exception name (for example `IndexError x3`), never the message, so that
  nobody can print hidden data. Debug crashes locally on the public instances.
- **Limits:** you can have one evaluation running at a time, and a limited number of tries per day
  (the site shows how many you have left).

---

## 6. How you are scored

Every (instance, seed) pair is one **run**. For each track (`50_medium`, `50_hard`, `100_medium`,
`100_hard`):

- **Failure rate** is the % of runs with no feasible tour. Infeasible, timeout, crash and invalid
  output all count as failures.
- **Gap** is how much longer your tour is than the best known tour for that instance (the reference),
  averaged over your **feasible runs only**: `(your length - reference) / reference x 100`.

Example: one track, 2 instances x 2 seeds = 4 runs:

| run | result | length | reference | gap |
|---|---|---|---|---|
| 1 | feasible | 10.5 | 10.0 | 5 % |
| 2 | feasible | 10.2 | 10.0 | 2 % |
| 3 | timeout | | | |
| 4 | infeasible | | | |

So this track scores a failure rate of 2/4 = **50 %** and a gap of (5 + 2) / 2 = **3.5 %**.

- **Overall** is the average of the four tracks' failure rates, and separately of the four gaps.
- **Ranking:** a lower failure rate always wins. Gap only decides between equal failure rates
  (then time). So **feasibility is worth far more than length**.
- **Floor:** you are ACCEPTED only if you are strictly better than C-Greedy, which means a lower failure
  rate, or the same failure rate and a lower gap. A copy of C-Greedy ties, and a tie is REJECTED.
- **Last try matters:** your newest evaluated try is your entry. Don't upload an experiment you
  aren't confident in right before the deadline.
- **Final ranking:** after the deadline, every team's last try is re-run on a **separate, larger
  hidden set** with more seeds. Good leaderboard numbers that come from luck or overfitting won't
  survive that.

A small gap (even slightly negative, if you beat the reference) is possible on easy runs. Don't chase it
before your failure rate is near zero.

---

## 7. Your day-to-day workflow

```bash
pip install -r requirements.txt                       # once

pytest -q                                             # 1. does my file follow the rules?
python run_local.py --time-scale 0.2 --workers 4      # 2. quick check while developing (~1 min)
python run_local.py                                   # 3. official timing on all public instances
python check_submission.py                            # 4. the website's exact upload checks
#    then upload algorithm.py on the website           # 5. watch the live log
```

`run_local.py` prints a table per track for your algorithm and for the C-Greedy floor, and a
verdict (ACCEPTED / REJECTED) on the public instances when you run all tracks. Useful flags:

| flag | what it does |
|---|---|
| `--track 50_hard` | only one track |
| `--seeds 3` | seeds per instance (the live board uses 2) |
| `--instances 3` | only the first 3 instances per track (faster) |
| `--time-scale 0.2` | 20% of the official time limits. Fast, but **not** comparable to the website |
| `--workers 4` | 4 runs in parallel. Fast, but timing is less faithful. Use 1 for official numbers |
| `--algo other.py` | evaluate a different file (e.g. a variant for your ablation study) |
| `--csv results.csv --label name` | append every run to a CSV, tagged with `name` |
| `-v` | print every single run |

---

## 8. Where to write code in `algorithm.py`

The file is split into helpers you get for free, the TODOs you fill in, and the entry point.

| function | status | what it should do |
|---|---|---|
| `arrival(inst, t, i, j)` | **given** | service start time at j if you leave i at time t (includes waiting) |
| `reachable(inst, t, i, j)` | **given** | can j still be reached from i at time t before its window closes? |
| `is_feasible(inst, tour)` | given (slow) | full O(n) check. Replace it with a faster incremental check later |
| `tour_cost(inst, tour)` | **given** | total length of a tour |
| `order_candidates(...)` | TODO | which customer to try next, best first (MRV: most urgent first) |
| `forward_check(...)` | TODO | return False when the current partial tour can't possibly be completed |
| `construct_feasible_tour(...)` | TODO | backtracking search that finds a feasible tour |
| `random_neighbor(tour, rng)` | TODO | a small random change: move a node, swap two, reverse a segment |
| `local_search(...)` | TODO | hill climbing, then simulated annealing, keeping the best feasible tour |
| `solve(...)` | entry point | glues it together. **Keep its name and its three parameters** |

Suggested order of work. Measure with `run_local.py` after each step:

1. **`forward_check`:** prune as soon as some unvisited node can't be reached in time. This is
   only a few lines, but it is what makes the next step work.
2. **`construct_feasible_tour`:** turn the greedy loop into a real backtracking search (try the
   candidates in order, go deeper, undo on failure). Give it a budget or restarts so it can't get
   stuck in one branch until the time limit. **This step alone should push your failure rate well
   below C-Greedy's**, which is enough to get accepted.
3. **`order_candidates`:** better ordering (least slack first, tie-breaks) means less backtracking.
4. **`random_neighbor` + `local_search`:** now shorten the feasible tour. Only accept moves that keep it
   feasible (or penalise lateness). This lowers your gap.
5. **Speed:** faster checks mean more iterations in the same time, which means better tours.

You don't have to keep this structure. You can delete everything and write your own algorithm, as
long as `def solve(instance, time_limit, seed)` exists and returns a tour. The structure is only a
suggested starting point, taken from the project description.

---

## 9. Do

- **Do** keep everything in `algorithm.py`. Helper functions and classes are fine. Extra files are
  not uploaded.
- **Do** use `Deadline(time_limit)` and check it inside every loop that can run long, including your
  backtracking search.
- **Do** always return something. Keep a "best tour so far" and return it when time runs out.
- **Do** use `instance.dist_list[i][j]` in Python loops. It is many times faster than `instance.dist[i, j]`.
- **Do** create all randomness from `seed` (`rng = random.Random(seed)`) and pass `rng` around.
- **Do** run `pytest -q` and `python check_submission.py` before every upload.
- **Do** compare against the floor and your previous version with `run_local.py`, and keep the CSV
  rows. They are your experiments for the report.
- **Do** make extra test instances if you want: `inst, _ = tsptw.generate_instance(50, "hard", numpy.random.default_rng(k))`.
  It is the same generator the hidden sets come from.

## 10. Don't (and why)

| don't | why |
|---|---|
| edit anything in `tsptw/` | the server uses its own copy. Your local results would no longer match the website |
| import anything besides the standard library, `numpy` and `tsptw` | the upload is rejected. Other packages (scipy, numba, ortools, ...) aren't installed on the server |
| use ready-made solvers (OR-Tools, LKH, SAT/CP solvers) or copy their code | against the course rules: the algorithm must be your own design |
| use threads, `multiprocessing`, `subprocess`, sockets, `exec`/`eval` | rejected on upload and blocked on the server. You get one CPU core anyway |
| use the full time limit, or ignore it | the server may be slower than your laptop, and the run is killed at `time_limit + 1 s` |
| do heavy work when the module is imported (at top level) | imports have their own short limit. Do the work inside `solve` |
| read files, or hard-code tours or values from `instances/public` | the hidden instances are different. Hard-coded answers score nothing and break the rules |
| rely on `print` for debugging on the server | output is discarded there. Debug locally |
| change the signature of `solve`, or rename it | the website calls exactly `solve(instance, time_limit, seed)` |
| keep state between calls (global caches) | every run is a fresh process on the server |
| upload a zip or several files | only one `.py` file is accepted |
| upload an untested experiment near the deadline | your last evaluated try is your entry, even if it is worse |

---

## 11. Error messages and what they mean

| you see | meaning | fix |
|---|---|---|
| `import of 'X' is not allowed` | X isn't on the allowed list | remove the import and write that part yourself |
| `missing top-level function: def solve(...)` | no `solve` at module level | keep `def solve(instance, time_limit, seed)` |
| `solve must accept three arguments` | wrong signature | exactly `(instance, time_limit, seed)` |
| `syntax error on line N` | your file doesn't parse | run `python -m py_compile algorithm.py` locally |
| `file is larger than 256 KB` | file too big | you probably embedded data; don't |
| `did not return within Xs + 1s grace` | smoke test timed out | use `Deadline` everywhere, including in the search |
| `solve() crashed on a public instance (...)` + traceback | your bug, shown in full | reproduce it with `run_local.py -v` |
| `invalid tour` | wrong output format | see the table in section 4 |
| hidden runs: `IndexError x3` (no message) | crashes on hidden instances | test on more instances: `--seeds 5`, generated instances |
| status `infeasible` | valid tour, but some window was missed | that's the algorithm to improve, not a bug |
| `already have an evaluation in progress` | one evaluation at a time | wait for it to finish |
| `daily limit reached` | out of tries for today | evaluate locally until tomorrow |

---

## 12. Using the kit for your report

The project asks for runnable code, a short paper-style report and an **ablation study**
(remove one part of your algorithm at a time and show what it was worth). The kit covers the
measuring:

```bash
python run_local.py --label full          --csv results.csv
python run_local.py --label no-forward-chk --csv results.csv --algo variants/no_fc.py
python run_local.py --label no-annealing  --csv results.csv --algo variants/hill_climb_only.py
```

Every run becomes one CSV row: label, track, instance, seed, status, length, gap and time. Group by label
and track to get your tables. Use `--workers 1 --time-scale 1` for the numbers you report.

---

## 13. FAQ

**Can I use numpy?** Yes. For tight per-node loops, plain Python lists (`dist_list`) are usually faster
than numpy indexing. Numpy pays off for whole-array operations.

**Is my local time the same as the server's?** Roughly, but the server may be slower. If you
need almost all of the time limit locally, you'll be too close to the limit on the server.
`Deadline` already stops you at 95%, so don't push it further.

**Why does the unchanged starter get REJECTED?** It *is* C-Greedy, and you have to be strictly
better than C-Greedy.

**My gap is great but I'm ranked low.** Your failure rate is higher than the teams above you.
Failure rate always comes first.

**Does a crash in the smoke test cost me a try?** No. Static-check failures and smoke-test failures
are free. Only completed evaluations count.

**Can a team member change?** Members can be added (up to 3) on your team page. Removals go
through the TAs.

**Where is the exact definition of "feasible"?** In `tsptw/evaluate.py` (`check_tour`). That is
the very function the website uses. A start time up to `EPS = 1e-5` past the window still counts
as on time, to absorb rounding.
