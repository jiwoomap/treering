from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from treering.ringlog import RUN_ID, RingLog

DEFAULT_LOG = Path(os.environ.get("TREERING_LOG", Path.home() / ".treering" / "rings.jsonl"))
SUMMARY_KEYS = ("command", "file_path", "path", "pattern", "url", "query", "prompt")
SUMMARY_LIMIT = 200


@dataclass(frozen=True)
class HookResult:
    stdout: str | None
    exit_code: int


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def _sha(obj: Any) -> str:
    return hashlib.sha256(_canonical(obj).encode()).hexdigest()


def summarize(tool_input: Any) -> str:
    if isinstance(tool_input, dict):
        for k in SUMMARY_KEYS:
            if k in tool_input and tool_input[k]:
                return str(tool_input[k])[:SUMMARY_LIMIT]
    return _canonical(tool_input)[:SUMMARY_LIMIT]


@contextmanager
def _locked(log_path: Path):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    lock = open(str(log_path) + ".lock", "w")
    try:
        import fcntl

        fcntl.flock(lock, fcntl.LOCK_EX)
    except ImportError:
        pass
    try:
        yield
    finally:
        lock.close()


def _decide(summary: str, deny: list[str], ask: list[str]) -> tuple[str, str | None]:
    for pat in deny:
        if re.search(pat, summary):
            return "deny", f"treering: matched deny rule /{pat}/"
    for pat in ask:
        if re.search(pat, summary):
            return "ask", f"treering: matched ask rule /{pat}/"
    return "allow", None


def run_hook(
    event: dict[str, Any],
    log_path: Path = DEFAULT_LOG,
    deny: list[str] | None = None,
    ask: list[str] | None = None,
    module: str = "claude-code",
) -> HookResult:
    name = str(event.get("hook_event_name", ""))
    tool = str(event.get("tool_name", "?"))
    tool_input = event.get("tool_input", {})
    summary = summarize(tool_input)
    payload: dict[str, Any] = {
        RUN_ID: event.get("session_id"),
        "module": str(event.get("agent", module)),
        "tool_use_id": event.get("tool_use_id"),
        "cwd": event.get("cwd"),
        "summary": summary,
        "input_hash": _sha(tool_input),
    }

    stdout = None
    if name == "PreToolUse":
        decision, reason = _decide(summary, deny or [], ask or [])
        payload |= {"action": f"tool:{tool}", "decision": decision}
        if reason:
            payload["reason"] = reason
            stdout = json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": decision,
                        "permissionDecisionReason": reason,
                    }
                }
            )
    elif name == "PostToolUse":
        payload |= {"action": f"result:{tool}", "output_hash": _sha(event.get("tool_response"))}
    else:
        payload |= {"action": f"event:{name or 'unknown'}"}

    with _locked(log_path):
        RingLog(log_path).append(**payload)
    return HookResult(stdout, 0)


def main_from_stdin(log_path: Path, deny: list[str], ask: list[str], module: str) -> int:
    try:
        event = json.load(sys.stdin)
        result = run_hook(event, log_path, deny, ask, module)
    except Exception as e:
        print(f"treering hook: {e}", file=sys.stderr)
        return 1
    if result.stdout:
        print(result.stdout)
    return result.exit_code
