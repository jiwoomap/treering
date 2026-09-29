from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

GENESIS = "0" * 64


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _digest(prev_hash: str, payload: dict[str, Any]) -> str:
    return hashlib.sha256((prev_hash + _canonical(payload)).encode()).hexdigest()


@dataclass(frozen=True)
class Ring:
    seq: int
    prev_hash: str
    hash: str
    payload: dict[str, Any]


class RingLog:
    def __init__(self, path: str | Path | None = None):
        self._rings: list[Ring] = []
        self._path = Path(path) if path else None
        if self._path and self._path.exists():
            self._load()

    def append(self, **payload: Any) -> Ring:
        prev = self._rings[-1].hash if self._rings else GENESIS
        ring = Ring(
            seq=len(self._rings), prev_hash=prev, hash=_digest(prev, payload), payload=payload
        )
        self._rings.append(ring)
        if self._path:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(_canonical(asdict(ring)) + "\n")
        return ring

    def verify(self) -> tuple[bool, int | None]:
        prev = GENESIS
        for ring in self._rings:
            if ring.prev_hash != prev or ring.hash != _digest(prev, ring.payload):
                return False, ring.seq
            prev = ring.hash
        return True, None

    def rings(self) -> list[Ring]:
        return list(self._rings)

    def __len__(self) -> int:
        return len(self._rings)

    def _load(self) -> None:
        assert self._path is not None
        with open(self._path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    self._rings.append(Ring(**json.loads(line)))
