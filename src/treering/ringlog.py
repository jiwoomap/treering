from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

GENESIS = "0" * 64
TS = "ts"
RUN_ID = "run_id"
KEY_SUFFIX = ".key"


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _digest(prev_hash: str, payload: dict[str, Any]) -> str:
    return hashlib.sha256((prev_hash + _canonical(payload)).encode()).hexdigest()


def _seal(key: bytes, ring_hash: str) -> str:
    return hmac.new(key, ring_hash.encode(), "sha256").hexdigest()


def _ratchet(key: bytes) -> bytes:
    return hashlib.sha256(key).digest()


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


def generate_root_key() -> bytes:
    return secrets.token_bytes(32)


def key_file_for(log_path: str | Path) -> Path:
    return Path(str(log_path) + KEY_SUFFIX)


def _write_key_file(path: Path, seq: int, key: bytes) -> None:
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"seq": seq, "key": key.hex()}, f)
    os.replace(tmp, path)


def _read_key_file(path: Path) -> tuple[int, bytes]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return int(data["seq"]), bytes.fromhex(data["key"])


def init_key_file(log_path: str | Path, root_key: bytes) -> Path:
    key_path = key_file_for(log_path)
    if key_path.exists():
        raise ValueError(f"{key_path} already exists")
    log = Path(log_path)
    if log.exists() and log.stat().st_size > 0:
        raise ValueError(f"{log_path} already has rings; sealing must start at ring 0")
    _write_key_file(key_path, 0, root_key)
    return key_path


@dataclass(frozen=True)
class Ring:
    seq: int
    prev_hash: str
    hash: str
    payload: dict[str, Any]
    seal: str | None = None

    @property
    def ts(self) -> str:
        return str(self.payload.get(TS, ""))

    @property
    def run_id(self) -> str | None:
        v = self.payload.get(RUN_ID)
        return None if v is None else str(v)

    @property
    def module(self) -> str:
        return str(self.payload.get("module", ""))

    @property
    def action(self) -> str:
        return str(self.payload.get("action", ""))


@dataclass(frozen=True)
class RunSummary:
    run_id: str | None
    started: str
    query: str
    rings: int
    blocked: bool


@dataclass(frozen=True)
class Anchor:
    seq: int
    hash: str
    ts: str


def load_anchors(path: str | Path) -> list[Anchor]:
    p = Path(path)
    if not p.exists():
        return []
    lines = p.read_text(encoding="utf-8").splitlines()
    return [Anchor(**json.loads(line)) for line in lines if line.strip()]


def append_anchor(path: str | Path, anchor: Anchor) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(anchor), sort_keys=True) + "\n")


class RingLog:
    def __init__(self, path: str | Path | None = None, *, key: bytes | None = None):
        self._path = Path(path) if path else None
        self._rings: list[Ring] = []
        self._key = key
        self._key_path: Path | None = None
        if self._path:
            self._load()
            key_path = key_file_for(self._path)
            if key_path.exists():
                seq, stored = _read_key_file(key_path)
                if seq != len(self._rings):
                    raise ValueError(
                        f"{self._path} has {len(self._rings)} rings but {key_path} expects "
                        f"ring {seq}: log and key file are out of step"
                    )
                self._key, self._key_path = stored, key_path

    def append(self, **payload: Any) -> Ring:
        payload.setdefault(TS, now_iso())
        prev = self._rings[-1].hash if self._rings else GENESIS
        ring_hash = _digest(prev, payload)
        seal = _seal(self._key, ring_hash) if self._key is not None else None
        ring = Ring(len(self._rings), prev, ring_hash, payload, seal)
        self._rings.append(ring)
        if self._path:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(_canonical(asdict(ring)) + "\n")
        if self._key is not None:
            self._key = _ratchet(self._key)
            if self._key_path:
                _write_key_file(self._key_path, len(self._rings), self._key)
        return ring

    def verify(self) -> tuple[bool, int | None]:
        prev = GENESIS
        for ring in self._rings:
            if ring.prev_hash != prev or ring.hash != _digest(prev, ring.payload):
                return False, ring.seq
            prev = ring.hash
        return True, None

    def verify_seals(self, root_key: bytes) -> tuple[bool, int | None]:
        key = root_key
        for ring in self._rings:
            if ring.seal is None or not hmac.compare_digest(ring.seal, _seal(key, ring.hash)):
                return False, ring.seq
            key = _ratchet(key)
        return True, None

    def anchor(self) -> Anchor:
        if not self._rings:
            raise ValueError("cannot anchor an empty log")
        last = self._rings[-1]
        return Anchor(last.seq, last.hash, now_iso())

    def check_anchors(self, anchors: list[Anchor]) -> list[tuple[Anchor, str]]:
        out: list[tuple[Anchor, str]] = []
        for a in anchors:
            if a.seq >= len(self._rings):
                out.append((a, "MISSING"))
            elif self._rings[a.seq].hash != a.hash:
                out.append((a, "MISMATCH"))
            else:
                out.append((a, "ok"))
        return out

    def rings(self) -> list[Ring]:
        return list(self._rings)

    def tail(self, n: int | None = None, run_id: str | None = None) -> list[Ring]:
        rings = self._rings
        if run_id is not None:
            rings = [r for r in rings if r.run_id is not None and r.run_id.startswith(run_id)]
        return list(rings[-n:]) if n else list(rings)

    def runs(self) -> list[RunSummary]:
        order: list[str | None] = []
        groups: dict[str | None, list[Ring]] = {}
        for r in self._rings:
            if r.run_id not in groups:
                order.append(r.run_id)
                groups[r.run_id] = []
            groups[r.run_id].append(r)
        out: list[RunSummary] = []
        for rid in order:
            rs = groups[rid]
            query = next((str(r.payload["query"]) for r in rs if "query" in r.payload), "")
            blocked = any(r.payload.get("status") == "blocked" for r in rs)
            out.append(RunSummary(rid, rs[0].ts, query, len(rs), blocked))
        return out

    def __len__(self) -> int:
        return len(self._rings)

    def _load(self) -> None:
        assert self._path is not None
        if not self._path.exists():
            return
        with open(self._path, encoding="utf-8") as f:
            for n, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    self._rings.append(Ring(**json.loads(line)))
                except (ValueError, TypeError) as e:
                    raise ValueError(f"{self._path}: line {n} is not a valid ring") from e
