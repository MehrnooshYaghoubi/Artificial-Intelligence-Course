"""Evaluate an algorithm on the public instances exactly like the leaderboard.

    python run_local.py                              # algorithm.py, all tracks, 2 seeds
    python run_local.py --track 50_hard --seeds 3    # one track
    python run_local.py --algo baselines/greedy.py   # any file with solve()
    python run_local.py --time-scale 0.2 --workers 4 # quick iteration (NOT official timing)
    python run_local.py --label no-forward-check --csv results.csv   # ablation rows

Each (instance, seed) run happens in a fresh process: the clock starts when
``solve`` is called (imports are not timed) and the run is killed at
``time_limit + 1 s``, like on the server. Every run is appended to the CSV so
you can build tables for your report and ablation study.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import multiprocessing as mp
import os
import sys
import time
import traceback
from dataclasses import dataclass
from multiprocessing.connection import wait
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from tsptw import (  # noqa: E402
    TIME_LIMITS,
    TRACKS,
    Instance,
    Run,
    beats_floor,
    check_tour,
    load_set,
    normalize_tour,
    summarize,
)

GRACE = 1.0  # seconds after time_limit before a run is killed
IMPORT_TIMEOUT = 10.0
INSTANCE_DIR = ROOT / "instances" / "public"


@dataclass
class Job:
    track: str
    instance: Instance
    ref_length: float | None
    seed: int
    time_limit: float


@dataclass
class Result:
    job: Job
    status: str  # ok | infeasible | invalid | timeout | crash
    length: float | None
    wall_time: float
    detail: str = ""

    def as_run(self) -> Run:
        return Run(
            self.job.track, self.job.instance.name, self.job.seed, self.status,
            self.length, self.job.ref_length, self.wall_time,
        )  # fmt: skip


def load_module(path: str | Path):
    spec = importlib.util.spec_from_file_location("submission_algorithm", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _child(conn, algo_path: str, inst_dict: dict, time_limit: float, seed: int) -> None:
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    try:
        sys.path.insert(0, str(ROOT))
        module = load_module(algo_path)
        instance = Instance.from_dict(inst_dict)
    except BaseException:
        conn.send(("crash", "import failed:\n" + traceback.format_exc(limit=5)))
        return
    conn.send(("ready", None))
    conn.recv()  # "go": the clock starts now (measured by the parent)
    try:
        tour = module.solve(instance, time_limit, seed)
    except BaseException:
        conn.send(("crash", traceback.format_exc(limit=8)))
        return
    try:
        conn.send(("tour", normalize_tour(tour, instance.n)))
    except Exception as e:
        conn.send(("invalid", str(e)))


def run_jobs(algo_path: str | Path, jobs: list[Job], workers: int = 1, progress=None) -> list[Result]:
    """Run every job in its own process, at most ``workers`` at a time."""
    ctx = mp.get_context("spawn")
    pending = list(enumerate(jobs))
    results: list[Result | None] = [None] * len(jobs)
    active: dict = {}  # conn -> dict(state, proc, idx, deadline, t_go)

    def finish(conn, status, length=None, wall=0.0, detail=""):
        a = active.pop(conn)
        if a["proc"].is_alive():
            a["proc"].kill()
        a["proc"].join()
        conn.close()
        results[a["idx"]] = Result(jobs[a["idx"]], status, length, wall, detail)
        if progress:
            progress(results[a["idx"]])

    while pending or active:
        while pending and len(active) < workers:
            idx, job = pending.pop(0)
            parent, child = ctx.Pipe()
            proc = ctx.Process(
                target=_child,
                args=(child, str(algo_path), job.instance.to_dict(), job.time_limit, job.seed),
                daemon=True,
            )
            proc.start()
            child.close()
            active[parent] = {"state": "import", "proc": proc, "idx": idx,
                              "deadline": time.perf_counter() + IMPORT_TIMEOUT, "t_go": 0.0}  # fmt: skip

        now = time.perf_counter()
        timeout = max(0.0, min(a["deadline"] for a in active.values()) - now)
        ready = wait(list(active), timeout=timeout)
        now = time.perf_counter()
        for conn in ready:
            a = active[conn]
            try:
                kind, payload = conn.recv()
            except (EOFError, OSError):
                finish(conn, "crash", wall=now - a["t_go"] if a["t_go"] else 0.0, detail="process died")
                continue
            if kind == "ready":
                job = jobs[a["idx"]]
                a.update(state="run", t_go=time.perf_counter())
                a["deadline"] = a["t_go"] + job.time_limit + GRACE
                conn.send("go")
                continue
            wall = now - a["t_go"] if a["t_go"] else 0.0
            if kind == "tour":
                job = jobs[a["idx"]]
                r = check_tour(job.instance, payload)
                finish(conn, "ok" if r.feasible else "infeasible", r.length, wall, r.message)
            else:
                finish(conn, kind, None, wall, payload or "")
        for conn, a in list(active.items()):
            if now >= a["deadline"]:
                if a["state"] == "import":
                    finish(conn, "crash", detail=f"import took longer than {IMPORT_TIMEOUT:.0f}s")
                else:
                    finish(conn, "timeout", wall=now - a["t_go"], detail="killed at time_limit + 1s")
    return results  # type: ignore[return-value]


def build_jobs(tracks, seeds: int, time_scale: float, limit: int | None) -> list[Job]:
    jobs = []
    for track in tracks:
        bench = load_set(INSTANCE_DIR / f"{track}.json")
        n = TRACKS[track][0]
        tl = TIME_LIMITS[n] * time_scale
        for inst in bench.instances[:limit]:
            for seed in range(seeds):
                jobs.append(Job(track, inst, bench.refs.get(inst.name), seed, tl))
    return jobs


def floor_stats(jobs: list[Job]):
    """C-Greedy is deterministic and instant, so evaluate it inline."""
    sys.path.insert(0, str(ROOT / "baselines"))
    greedy = load_module(ROOT / "baselines" / "greedy.py")
    runs = []
    for j in jobs:
        r = check_tour(j.instance, greedy.solve(j.instance, j.time_limit, j.seed))
        runs.append(Run(j.track, j.instance.name, j.seed, "ok" if r.feasible else "infeasible",
                        r.length, j.ref_length, 0.0))  # fmt: skip
    return runs


def fmt(x, unit="", nd=2):
    if x is None:
        return "—"
    if abs(x) < 0.5 * 10**-nd:
        x = 0.0  # avoid "-0.00"
    return f"{x:.{nd}f}{unit}"


def print_table(title: str, stats: dict) -> None:
    print(f"\n{title}")
    print(f"  {'track':<12}{'runs':>6}{'fail %':>9}{'gap %':>9}{'avg time':>10}")
    for key, s in stats.items():
        print(f"  {key:<12}{s.runs:>6}{fmt(s.failure_rate):>9}{fmt(s.gap):>9}{fmt(s.avg_time, 's'):>10}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--algo", default=str(ROOT / "algorithm.py"))
    p.add_argument("--track", default="all", choices=["all", *TRACKS])
    p.add_argument("--seeds", type=int, default=2, help="seeds per instance (server: 2 live, 3 final)")
    p.add_argument("--instances", type=int, default=None, help="max instances per track")
    p.add_argument("--time-scale", type=float, default=1.0, help="multiply official time limits")
    p.add_argument("--workers", type=int, default=1,
                   help="parallel runs; >1 is faster but timing is less faithful on busy machines")
    p.add_argument("--csv", default=None, help="append per-run rows to this CSV file")
    p.add_argument("--label", default="", help="free text stored in the CSV (e.g. ablation name)")
    p.add_argument("--verbose", "-v", action="store_true", help="print every run")
    args = p.parse_args()

    tracks = list(TRACKS) if args.track == "all" else [args.track]
    jobs = build_jobs(tracks, args.seeds, args.time_scale, args.instances)
    est = sum(j.time_limit for j in jobs) / max(1, args.workers)
    print(f"{len(jobs)} runs of {Path(args.algo).name} on {', '.join(tracks)}  (≤ {est / 60:.1f} min)")
    if args.time_scale != 1.0:
        print(f"note: time limits scaled by {args.time_scale} — results are not comparable to the leaderboard")

    done = 0

    def progress(r: Result):
        nonlocal done
        done += 1
        if args.verbose or r.status in ("crash", "invalid"):
            print(f"  [{done:>4}/{len(jobs)}] {r.job.instance.name} seed={r.job.seed} "
                  f"{r.status:<10} len={fmt(r.length, nd=4)} t={r.wall_time:.2f}s"
                  + (f"\n{r.detail}" if r.status in ("crash", "invalid") else ""))  # fmt: skip
        else:
            print(f"\r  {done}/{len(jobs)} runs done", end="", flush=True)

    results = run_jobs(args.algo, jobs, args.workers, progress)
    print()
    stats = summarize([r.as_run() for r in results], tracks)
    floor = summarize(floor_stats(jobs), tracks)
    print_table(f"{Path(args.algo).name}", stats)
    print_table("C-Greedy floor", floor)

    if len(tracks) == len(TRACKS):
        ok = beats_floor(stats["overall"], floor["overall"])
        verdict = "ACCEPTED (beats the floor)" if ok else "REJECTED (not better than the C-Greedy floor)"
        print(f"\nverdict on public instances: {verdict}")
    else:
        print("\n(run all tracks to see the overall verdict)")

    if args.csv:
        new = not Path(args.csv).exists()
        with open(args.csv, "a", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["label", "algo", "track", "instance", "seed", "status", "length",
                            "ref_length", "gap_pct", "wall_time", "time_limit"])  # fmt: skip
            for r in results:
                run = r.as_run()
                w.writerow([args.label, Path(args.algo).name, run.track, run.instance, run.seed, run.status,
                            "" if run.length is None else f"{run.length:.6f}",
                            "" if run.ref_length is None else f"{run.ref_length:.6f}",
                            "" if run.gap is None else f"{run.gap:.4f}",
                            f"{run.wall_time:.3f}", r.job.time_limit])  # fmt: skip
        print(f"appended {len(results)} rows to {args.csv}")


if __name__ == "__main__":
    main()
