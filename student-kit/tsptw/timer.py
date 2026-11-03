from __future__ import annotations

import time


class Deadline:
    """Wall-clock budget helper.

    The server kills a run at ``time_limit + 1s``; a killed run counts as a
    failure. ``Deadline`` stops a little earlier (``safety`` fraction of the
    budget) so you always have time to return your best tour.

        deadline = Deadline(time_limit)
        while not deadline.expired():
            ...
    """

    def __init__(self, time_limit: float, safety: float = 0.05) -> None:
        if time_limit <= 0:
            raise ValueError("time_limit must be positive")
        self.time_limit = float(time_limit)
        self.start = time.perf_counter()
        self.end = self.start + self.time_limit * (1.0 - safety)

    def elapsed(self) -> float:
        return time.perf_counter() - self.start

    def remaining(self) -> float:
        return max(0.0, self.end - time.perf_counter())

    def expired(self) -> bool:
        return time.perf_counter() >= self.end
