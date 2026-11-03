"""Pre-flight check: run this before uploading.

    python check_submission.py                 # checks algorithm.py
    python check_submission.py path/to/file.py

1. the same static checks the website applies on upload (imports, solve signature, size)
2. a smoke run on one public instance per track with the official time limits
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from run_local import build_jobs, run_jobs  # noqa: E402
from tsptw import TRACKS, check_source  # noqa: E402


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "algorithm.py")
    print(f"checking {path}")
    problems = check_source(path.read_bytes())
    if problems:
        print("✗ static check failed — the website would reject this file:")
        for msg in problems:
            print(f"   - {msg}")
        return 1
    print("✓ static check passed")

    jobs = [build_jobs([t], seeds=1, time_scale=1.0, limit=1)[0] for t in TRACKS]
    print(f"smoke run: {len(jobs)} instances, official time limits ...")
    ok = True
    for r in run_jobs(path, jobs, workers=len(jobs)):
        mark = {"ok": "✓", "infeasible": "~"}.get(r.status, "✗")
        print(f"   {mark} {r.job.track:<11} {r.status:<10} {r.wall_time:6.2f}s / {r.job.time_limit:.0f}s")
        if r.status in ("crash", "invalid", "timeout"):
            ok = False
            if r.detail:
                print("     " + r.detail.strip().replace("\n", "\n     "))
    if not ok:
        print("✗ fix the errors above: crashes, invalid tours and timeouts count as failures")
        return 1
    print("✓ ready to upload (✓ feasible, ~ valid but infeasible = counts as a failure)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
