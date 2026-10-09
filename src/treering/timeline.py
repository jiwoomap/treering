from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from treering.ringlog import RUN_ID, TS, Ring, RunSummary

_HEADER_KEYS = frozenset({"module", "action", TS, RUN_ID, "status", "reason"})


def _fmt_value(v: Any) -> str:
    if isinstance(v, list):
        return ",".join(str(x) for x in v) or "-"
    return str(v)


def _clock(ts: str) -> str:
    return ts[11:23] if len(ts) >= 23 else ts


def format_ring(ring: Ring) -> str:
    p = ring.payload
    detail = " ".join(f"{k}={_fmt_value(v)}" for k, v in p.items() if k not in _HEADER_KEYS)
    if p.get("status") == "blocked":
        detail = f"BLOCKED  {p.get('reason', '')}".rstrip()
    return f"  #{ring.seq:<4} {_clock(ring.ts):<12} {ring.module:<9} {ring.action:<24} {detail}"


def _run_header(rid: str | None, started: str, query: str) -> str:
    label = rid or "(no run)"
    q = f'  "{query}"' if query else ""
    return f"run {label}  {started}{q}"


def render_timeline(rings: list[Ring]) -> str:
    lines: list[str] = []
    current: str | None | object = object()
    for r in rings:
        if r.run_id != current:
            current = r.run_id
            query = str(r.payload.get("query", ""))
            if lines:
                lines.append("")
            lines.append(_run_header(r.run_id, r.ts, query))
        lines.append(format_ring(r))
    return "\n".join(lines) if lines else "(empty)"


def render_runs(runs: list[RunSummary]) -> str:
    if not runs:
        return "(empty)"
    lines = [f"{'run':<14} {'started':<32} {'rings':>5}  {'outcome':<8} query"]
    for s in runs:
        outcome = "blocked" if s.blocked else "ok"
        lines.append(
            f"{s.run_id or '(no run)':<14} {s.started:<32} {s.rings:>5}  {outcome:<8} {s.query}"
        )
    return "\n".join(lines)


def render_jsonl(rings: list[Ring]) -> str:
    return "\n".join(json.dumps(asdict(r), sort_keys=True, default=str) for r in rings)
