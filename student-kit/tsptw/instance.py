"""TSPTW instance model and JSON (de)serialisation.

Units follow the PIP benchmark (NeurIPS 2024) after its normalisation step:
coordinates live in [0, 1]^2, travel time equals Euclidean distance (speed 1),
service time is zero, and node 0 is the depot.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

SET_FORMAT = "tsptw-set/1"


def _readonly(a: np.ndarray) -> np.ndarray:
    a.setflags(write=False)
    return a


def distance_matrix(coords: np.ndarray) -> np.ndarray:
    diff = coords[:, None, :] - coords[None, :, :]
    return np.sqrt((diff**2).sum(axis=-1))


@dataclass(frozen=True, eq=False)
class Instance:
    """One TSPTW instance.

    Attributes:
        name:      unique instance name, e.g. ``"50_hard_007"``.
        coords:    (n, 2) float array, node 0 is the depot.
        tw_start:  (n,) earliest service start per node (l_i).
        tw_end:    (n,) latest service start per node (u_i).
        dist:      (n, n) Euclidean distance (= travel time) matrix.
        track:     benchmark track, e.g. ``"50_hard"`` (may be empty).

    Numpy arrays are read-only. For tight pure-Python loops use the plain-list
    mirrors ``dist_list``, ``tw_start_list`` and ``tw_end_list``; indexing a
    Python list is much faster than indexing a numpy array element by element.
    """

    name: str
    coords: np.ndarray
    tw_start: np.ndarray
    tw_end: np.ndarray
    track: str = ""
    dist: np.ndarray = field(init=False, repr=False)
    dist_list: list[list[float]] = field(init=False, repr=False)
    tw_start_list: list[float] = field(init=False, repr=False)
    tw_end_list: list[float] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        coords = np.array(self.coords, dtype=np.float64)
        tw_start = np.array(self.tw_start, dtype=np.float64)
        tw_end = np.array(self.tw_end, dtype=np.float64)
        if coords.ndim != 2 or coords.shape[1] != 2:
            raise ValueError("coords must have shape (n, 2)")
        n = coords.shape[0]
        if n < 2 or tw_start.shape != (n,) or tw_end.shape != (n,):
            raise ValueError("tw_start / tw_end must have shape (n,) with n >= 2")
        dist = distance_matrix(coords)
        set_ = object.__setattr__
        set_(self, "coords", _readonly(coords))
        set_(self, "tw_start", _readonly(tw_start))
        set_(self, "tw_end", _readonly(tw_end))
        set_(self, "dist", _readonly(dist))
        set_(self, "dist_list", dist.tolist())
        set_(self, "tw_start_list", tw_start.tolist())
        set_(self, "tw_end_list", tw_end.tolist())

    @property
    def n(self) -> int:
        """Number of nodes including the depot."""
        return self.coords.shape[0]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "track": self.track,
            "coords": self.coords.tolist(),
            "tw_start": self.tw_start.tolist(),
            "tw_end": self.tw_end.tolist(),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Instance:
        return cls(
            name=str(d.get("name", "")),
            coords=d["coords"],
            tw_start=d["tw_start"],
            tw_end=d["tw_end"],
            track=str(d.get("track", "")),
        )


@dataclass(frozen=True)
class Benchmark:
    """A set of instances of one track plus their reference tour lengths.

    ``refs[name]`` is the best known feasible tour length (from long LKH-3 runs)
    used to compute the gap. It is never passed to ``solve``.
    """

    track: str
    instances: list[Instance]
    refs: dict[str, float | None]

    def __iter__(self):
        return iter(self.instances)

    def __len__(self) -> int:
        return len(self.instances)


def load_instance(path: str | Path) -> Instance:
    with open(path, encoding="utf-8") as f:
        return Instance.from_dict(json.load(f))


def load_set(path: str | Path) -> Benchmark:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    if raw.get("format") != SET_FORMAT:
        raise ValueError(f"{path}: not a {SET_FORMAT} file")
    track = raw.get("track", "")
    instances, refs = [], {}
    for d in raw["instances"]:
        d = {"track": track, **d}
        inst = Instance.from_dict(d)
        instances.append(inst)
        refs[inst.name] = d.get("ref_length")
    return Benchmark(track=track, instances=instances, refs=refs)


def dump_set(path: str | Path, track: str, items: list[dict[str, Any]]) -> None:
    """Write a set file. ``items`` are ``Instance.to_dict()`` dicts, optionally
    extended with ``ref_length`` / ``ref_source``."""
    payload = {"format": SET_FORMAT, "track": track, "instances": items}
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))
